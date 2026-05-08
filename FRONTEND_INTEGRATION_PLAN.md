# Plan: Fix Frontend 404 — Align with Backend Presentation Generation API

## Context

The frontend form (topic, slide number, language inputs) is returning a 404 error when submitting a presentation generation request. The root cause is a mismatch between what the frontend is calling and what the backend actually exposes. This plan documents the exact backend contract so the frontend can be updated to match it.

---

## Backend API Contract (Source of Truth)

### Base URL
```
https://intellislide-ai-api.onrender.com
```

### Endpoint 1 — Trigger Generation
```
POST /api/v1/presentations
Content-Type: application/json
```

**Request body (all fields):**
| Field | Type | Required | Default | Constraints |
|---|---|---|---|---|
| `topic` | string | Yes | — | 3–300 chars, not whitespace-only |
| `num_slides` | integer | No | `5` | 1–20 |
| `language` | enum string | No | `"English"` | See values below |
| `theme` | enum string | No | `"professional"` | See values below |

**Valid `language` values:**
`"English"`, `"Arabic"`, `"French"`, `"Spanish"`, `"German"`, `"Portuguese"`, `"Chinese"`, `"Japanese"`, `"Hindi"`

**Valid `theme` values:**
`"professional"`, `"minimal"`, `"vibrant"`

**Response — HTTP 202 Accepted:**
```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "pending",
  "message": "Presentation generation queued.",
  "filename": "the-future-of-ai_550e8400.pptx",
  "download_url": null
}
```

---

### Endpoint 2 — Poll Status
```
GET /api/v1/presentations/{job_id}/status
```

**Response** (same `PPTResponse` model):
```json
{
  "job_id": "...",
  "status": "pending | processing | ready | failed",
  "message": "...",
  "filename": "...",
  "download_url": null
}
```

Poll this endpoint repeatedly until `status === "ready"` or `status === "failed"`.

---

### Endpoint 3 — Download File
```
GET /api/v1/presentations/{job_id}/download
```

Returns the `.pptx` file as a binary `FileResponse`.
Only works when status is `"ready"`. Returns 404 if not ready yet.

---

## Common Causes of the 404

These are the most likely mismatches causing the 404 error on the frontend:

| Likely Frontend Mistake | Correct Backend Value |
|---|---|
| Calling `/api/presentations` | Must be `/api/v1/presentations` (includes `/v1/`) |
| Calling `/api/v1/presentations/generate` | No `/generate` suffix — just `POST /api/v1/presentations` |
| Field named `slide_count` or `slides` | Must be `num_slides` |
| Field named `title` or `subject` | Must be `topic` |
| HTTP method `GET` for generation | Must be `POST` |
| Missing `Content-Type: application/json` header | Required for POST body parsing |

---

## Frontend Implementation Steps

### Step 1 — Fix the Fetch Call

Update the form submit handler to call the correct URL with the correct field names:

```js
const response = await fetch('https://intellislide-ai-api.onrender.com/api/v1/presentations', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    topic: formData.topic,           // NOT "title" or "subject"
    num_slides: formData.num_slides, // NOT "slide_count" or "slides"
    language: formData.language,     // e.g. "English"
    theme: formData.theme,           // e.g. "professional" (optional)
  }),
});

if (!response.ok) throw new Error(`HTTP ${response.status}`);
const { job_id } = await response.json(); // response is 202, not 200
```

### Step 2 — Add Status Polling

After getting `job_id`, poll until `status === "ready"`:

```js
async function pollStatus(job_id) {
  while (true) {
    const res = await fetch(`https://intellislide-ai-api.onrender.com/api/v1/presentations/${job_id}/status`);
    const data = await res.json();
    if (data.status === 'ready') return data;
    if (data.status === 'failed') throw new Error(data.message);
    await new Promise(r => setTimeout(r, 2000)); // wait 2s between polls
  }
}
```

### Step 3 — Trigger Download

When status is `"ready"`, download the file:

```js
const downloadUrl = `https://intellislide-ai-api.onrender.com/api/v1/presentations/${job_id}/download`;
window.open(downloadUrl, '_blank');
// OR use an anchor tag:
const a = document.createElement('a');
a.href = downloadUrl;
a.download = filename; // from the status response
a.click();
```

### Step 4 — Form Field Names

Ensure HTML form inputs or React/Lynx state use these exact names:

```html
<!-- Topic -->
<input name="topic" ... />

<!-- Slide count — must map to num_slides in the payload -->
<input name="num_slides" type="number" min="1" max="20" />

<!-- Language — dropdown with enum values -->
<select name="language">
  <option value="English">English</option>
  <option value="Arabic">Arabic</option>
  <option value="French">French</option>
  <option value="Spanish">Spanish</option>
  <option value="German">German</option>
  <option value="Portuguese">Portuguese</option>
  <option value="Chinese">Chinese</option>
  <option value="Japanese">Japanese</option>
  <option value="Hindi">Hindi</option>
</select>

<!-- Theme (optional) -->
<select name="theme">
  <option value="professional">Professional</option>
  <option value="minimal">Minimal</option>
  <option value="vibrant">Vibrant</option>
</select>
```

---

## Critical Files on the Backend (for reference)

| Purpose | File |
|---|---|
| Route definitions | `src/api/v1/presentation.py` |
| Router registration | `src/api/router.py` |
| App entry point | `src/main.py` |
| Request/response schemas | `src/schemas/presentation.py` |
| AI generation service | `src/services/ai_service.py` |
| PPTX builder | `src/services/presentation_service.py` |

---

## Verification Checklist

1. Open `https://intellislide-ai-api.onrender.com/docs` in a browser — verify the three presentation endpoints appear
2. Use the Swagger UI to POST a test request and confirm you get a 202 with a `job_id`
3. Poll the status endpoint manually until `"ready"`
4. Download the file via the download endpoint
5. Fix the frontend fetch URL/field names, resubmit the form, and confirm no 404
6. Check browser DevTools Network tab — the POST request URL should be exactly `https://intellislide-ai-api.onrender.com/api/v1/presentations`
