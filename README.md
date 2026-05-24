<div align="center">

# ⚡ SlideForge API

**AI-powered presentation generation. Topic in → polished PPTX out.**

[![Python](https://img.shields.io/badge/Python-3.12+-3776AB?style=flat-square&logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?style=flat-square&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![Google Gemini](https://img.shields.io/badge/Gemini-AI-4285F4?style=flat-square&logo=google&logoColor=white)](https://ai.google.dev/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow?style=flat-square)](LICENSE)
[![CI](https://img.shields.io/github/actions/workflow/status/Engraya/SlideForge-api/ci.yml?branch=main&style=flat-square&label=CI)](https://github.com/Engraya/SlideForge-api/actions)
[![Docker](https://img.shields.io/badge/Docker-ready-2496ED?style=flat-square&logo=docker&logoColor=white)](Dockerfile)
[![Coverage](https://img.shields.io/badge/coverage-tested-brightgreen?style=flat-square)](tests/)

[Live Demo](https://slide-forge123.vercel.app/) · [API Docs](http://localhost:8000/docs) · [Report Bug](https://github.com/Engraya/SlideForge-api/issues)

</div>

---

## What is SlideForge?

SlideForge is a production-grade REST API that turns a plain text topic into a fully formatted `.pptx` presentation in seconds — powered by Google Gemini.

You send a topic, the number of slides, a language, and a visual theme. SlideForge queues the job, calls Gemini to generate structured slide content, assembles the PowerPoint file, and gives you a download link. No templates to fill. No design skills required.

**Who is it for?**

- Educators who need lecture slides fast
- Developers building AI productivity tools or SaaS wrappers
- Teams automating internal documentation and training materials
- Anyone who has ever spent an hour making a deck that should have taken five minutes

---

## Features

### Core

- **Async job processing** — POST returns immediately with a `job_id`; poll for status; download when ready
- **9 language support** — English, Arabic, French, Spanish, German, Portuguese, Chinese, Japanese, Hindi
- **3 visual themes** — Professional (dark blue), Minimal (clean white), Vibrant (cyan accent)
- **1–20 slides per request** (configurable up to 50 via env)
- **Automatic file cleanup** — generated `.pptx` files are deleted after 1 hour
- **Structured JSON logging** — every event captured with ISO 8601 timestamps and contextual fields

### AI

- **Google Gemini** (`gemini-2.0-flash-preview`) with JSON-mode output
- **Prompt-engineered schema enforcement** — Gemini always returns valid, structured slide content
- **Exponential backoff retry** — up to 3 attempts with 1s/2s/4s delays on transient failures
- **Strict response validation** — Pydantic ensures every slide has a title, bullets, and optional image placeholder before the PPTX is assembled

### Security

- **Rate limiting** — 10 requests/minute per IP via slowapi (configurable)
- **Path traversal prevention** — two-layer filename validation (stripping + resolve-bound check)
- **CORS** — explicit origin allowlist for frontend domains
- **Non-root Docker execution** — container runs as `appuser` (UID 1001)
- **No information leakage** — typed exceptions surface clean error codes; sensitive detail stays in server logs

### Developer Experience

- **Full type coverage** — validated with MyPy
- **Ruff** for linting and formatting
- **pytest + pytest-asyncio** test suite with coverage
- **GitHub Actions CI** — lint → type-check → test → Docker build on every push
- **Multi-stage Dockerfile** — minimal runtime image, healthcheck included
- **Dependency injection** — services are LRU-cached singletons injected via FastAPI `Depends`

---

## Tech Stack

| Layer | Technology |
|---|---|
| **Language** | Python 3.12+ |
| **Framework** | FastAPI 0.115 |
| **Server** | Uvicorn (ASGI) |
| **AI Provider** | Google Gemini (`google-generativeai 0.8.4`) |
| **PPTX Generation** | python-pptx 1.0.2 |
| **Validation** | Pydantic v2 + pydantic-settings |
| **Rate Limiting** | slowapi 0.1.9 |
| **Testing** | pytest, pytest-asyncio, pytest-cov, httpx |
| **Type Checking** | MyPy 1.13 |
| **Linting / Formatting** | Ruff 0.8 |
| **Containerization** | Docker (multi-stage, non-root) |
| **CI/CD** | GitHub Actions |
| **Frontend** | Next.js on Vercel (`slide-forge123.vercel.app`) |

---

## Architecture

SlideForge uses a clean layered architecture: HTTP routes delegate to service classes, which are dependency-injected and fully unit-testable.

```
┌─────────────────────────────────────────────────────────┐
│                    FastAPI Application                   │
│  ┌─────────────┐  ┌──────────────┐  ┌────────────────┐  │
│  │  Health API │  │Presentation  │  │  Rate Limiter  │  │
│  │  /v1/health │  │    API /v1   │  │  (slowapi)     │  │
│  └─────────────┘  └──────┬───────┘  └────────────────┘  │
└─────────────────────────┬┼────────────────────────────────┘
                          ││  Depends()
             ┌────────────┘└─────────────┐
             ▼                           ▼
  ┌─────────────────┐         ┌────────────────────┐
  │   GeminiProvider│         │  PresentationService│
  │  (ai_service)   │         │ (presentation_svc)  │
  └────────┬────────┘         └────────────┬────────┘
           │ JSON-mode                      │ python-pptx
           ▼                               ▼
  ┌─────────────────┐         ┌────────────────────┐
  │  Google Gemini  │         │  FileService        │
  │  API (external) │         │  (file_service)     │
  └─────────────────┘         └────────────────────┘
```

### Job Lifecycle

```
POST /presentations
       │
       ▼
   [202 Accepted]
   job_id returned
       │
       ▼  (background task)
  status: PENDING
       │
       ▼
  GeminiProvider.generate_slides()
       │  (with retry + validation)
       ▼
  status: PROCESSING
       │
       ▼
  PresentationService.build()
       │
       ▼
  status: READY ──▶ download_url populated
       │
       ▼  (1 hour later)
  FileService.cleanup()
  .pptx deleted
```

---

## Project Structure

```
SlideForge-api/
├── src/
│   ├── main.py                   # App factory — CORS, lifespan, error handlers
│   ├── config.py                 # Pydantic BaseSettings — all env config
│   ├── dependencies.py           # LRU-cached service singletons
│   ├── exceptions.py             # Typed exception hierarchy (6 types)
│   ├── api/
│   │   ├── router.py             # Aggregates all versioned routers
│   │   └── v1/
│   │       ├── health.py         # GET /health, GET /ready
│   │       └── presentation.py   # POST + GET presentation endpoints
│   ├── schemas/
│   │   ├── common.py             # HealthResponse, ErrorDetail
│   │   └── presentation.py       # PPTRequest, PPTResponse, SlideContent, enums
│   ├── services/
│   │   ├── ai_service.py         # Gemini integration — prompt, retry, parse
│   │   ├── presentation_service.py # PPTX assembly — themes, layout, fonts
│   │   └── file_service.py       # UUID filenames, path safety, TTL cleanup
│   └── utils/
│       ├── logging.py            # Structured JSON logging (UTC ISO 8601)
│       └── security.py           # Path traversal prevention
├── tests/
│   ├── conftest.py               # Shared TestClient fixture
│   ├── test_api.py               # Endpoint integration tests
│   ├── test_ai_service.py        # Gemini provider unit tests
│   ├── test_schemas.py           # Pydantic validation tests
│   └── test_file_service.py      # File ops and cleanup tests
├── .github/
│   └── workflows/
│       └── ci.yml                # Lint → Type → Test → Docker CI pipeline
├── Dockerfile                    # Multi-stage, non-root production image
├── docker-compose.yml            # Local dev stack with volume mount
├── requirements.txt              # Production dependencies
├── requirements-dev.txt          # Dev/test dependencies
└── pyproject.toml                # Project metadata, tool config (ruff, mypy, pytest)
```

---

## Getting Started

### Prerequisites

- Python 3.12+
- A [Google AI Studio](https://aistudio.google.com/) API key (free tier works)
- Docker (optional, for containerized runs)

### 1. Clone and install

```bash
git clone https://github.com/Engraya/SlideForge-api.git
cd SlideForge-api

python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS / Linux
source .venv/bin/activate

pip install -r requirements.txt
pip install -r requirements-dev.txt   # only needed for testing/dev
```

### 2. Configure environment

```bash
cp .env.example .env
# then edit .env and add your GOOGLE_API_KEY
```

### 3. Run locally

```bash
uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
```

API is now live at `http://localhost:8000`.
Interactive docs at `http://localhost:8000/docs` (disabled in production).

### 4. Run with Docker

```bash
# Build and start
docker-compose up --build

# Or pull and run the image directly
docker build -t slideforge-api .
docker run -p 8000:8000 -e GOOGLE_API_KEY=your_key slideforge-api
```

---

## Environment Variables

Create a `.env` file in the project root. All variables except `GOOGLE_API_KEY` are optional.

```env
# ── Required ──────────────────────────────────────────────
GOOGLE_API_KEY=your_google_generative_ai_key_here

# ── Application ───────────────────────────────────────────
ENVIRONMENT=development          # "development" | "production" (disables /docs in prod)
LOG_LEVEL=INFO                   # DEBUG | INFO | WARNING | ERROR | CRITICAL

# ── File Storage ──────────────────────────────────────────
OUTPUT_DIR=generated             # Directory for generated .pptx files
FILE_TTL_SECONDS=3600            # How long to keep files before cleanup (1 hour)

# ── Limits ────────────────────────────────────────────────
MAX_SLIDES=20                    # Maximum slides per request (1–50)
RATE_LIMIT_PER_MINUTE=10         # Requests per minute per IP

# ── CORS ──────────────────────────────────────────────────
CORS_ORIGINS=["http://localhost:3000","https://your-frontend.vercel.app"]
```

---

## API Reference

Base URL: `http://localhost:8000/api/v1`

### Health

```
GET /health
GET /ready
```

**Response `200`**
```json
{
  "status": "ok",
  "environment": "development",
  "version": "1.0.0"
}
```

---

### Create Presentation

```
POST /presentations
Content-Type: application/json
```

**Request Body**

| Field | Type | Required | Default | Notes |
|---|---|---|---|---|
| `topic` | string | ✅ | — | 3–300 characters |
| `num_slides` | integer | ❌ | `5` | 1–20 |
| `language` | string | ❌ | `"English"` | See supported languages below |
| `theme` | string | ❌ | `"professional"` | `professional` · `minimal` · `vibrant` |

**Supported Languages:** `English` · `Arabic` · `French` · `Spanish` · `German` · `Portuguese` · `Chinese` · `Japanese` · `Hindi`

```bash
curl -X POST http://localhost:8000/api/v1/presentations \
  -H "Content-Type: application/json" \
  -d '{
    "topic": "Introduction to Machine Learning",
    "num_slides": 6,
    "language": "English",
    "theme": "professional"
  }'
```

**Response `202 Accepted`**
```json
{
  "job_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "status": "pending",
  "message": "Presentation generation queued.",
  "filename": "introduction_to_machine_learning_a1b2c3d4e5f6.pptx",
  "download_url": null
}
```

---

### Poll Job Status

```
GET /presentations/{job_id}/status
```

```bash
curl http://localhost:8000/api/v1/presentations/3fa85f64-.../status
```

**Response `200`**
```json
{
  "job_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "status": "ready",
  "message": "Presentation is ready for download.",
  "filename": "introduction_to_machine_learning_a1b2c3d4e5f6.pptx",
  "download_url": "/api/v1/presentations/3fa85f64-.../download"
}
```

**Status values:** `pending` → `processing` → `ready` · `failed`

---

### Download Presentation

```
GET /presentations/{job_id}/download
```

Returns the `.pptx` binary file directly.

```bash
curl -OJ http://localhost:8000/api/v1/presentations/3fa85f64-.../download
```

---

### Error Responses

All errors follow a consistent shape:

```json
{
  "error_code": "AI_SERVICE_ERROR",
  "detail": "The AI service is temporarily unavailable. Please try again."
}
```

| HTTP Status | Error Code | Cause |
|---|---|---|
| `422` | `INPUT_VALIDATION_ERROR` | Invalid request body |
| `429` | `RATE_LIMIT_EXCEEDED` | Too many requests from this IP |
| `404` | `PRESENTATION_NOT_FOUND` | Job ID does not exist |
| `500` | `PRESENTATION_GENERATION_ERROR` | PPTX assembly failed |
| `502` | `AI_SERVICE_ERROR` | Gemini API unavailable |
| `502` | `AI_PARSING_ERROR` | Gemini returned unparseable content |

---

## Frontend Integration

The typical client flow:

```typescript
// 1. Submit the job
const { job_id } = await fetch('/api/v1/presentations', {
  method: 'POST',
  body: JSON.stringify({ topic, num_slides, language, theme }),
}).then(r => r.json());

// 2. Poll until ready
let status = 'pending';
while (status !== 'ready' && status !== 'failed') {
  await sleep(2000);
  const res = await fetch(`/api/v1/presentations/${job_id}/status`).then(r => r.json());
  status = res.status;
}

// 3. Download
window.location.href = `/api/v1/presentations/${job_id}/download`;
```

---

## AI Layer

SlideForge uses Google Gemini in **JSON mode** (`response_mime_type="application/json"`) to guarantee structured output. The prompt instructs Gemini to return a specific schema with no markdown fencing — then Pydantic validates every field before the PPTX is built.

**Generation config:**
- Model: `gemini-2.0-flash-preview`
- Temperature: `0.7` (balanced creativity)
- Max output tokens: `8192`

**Retry strategy:**

```
Attempt 1 ──(fail: network)──▶ wait 1s ──▶ Attempt 2
Attempt 2 ──(fail: network)──▶ wait 2s ──▶ Attempt 3
Attempt 3 ──(fail: network)──▶ raise AIServiceError (502)

Parsing failure ──▶ raise AIParsingError (502) immediately (no retry)
```

**Slide schema enforced by the prompt:**
```json
{
  "slides": [
    {
      "title": "string (max 80 chars)",
      "bullets": ["string (max 120 chars)", "..."],
      "image_placeholder": "string | null"
    }
  ]
}
```

---

## Running Tests

```bash
# Run all tests
pytest

# With coverage report
pytest --cov=src --cov-report=term-missing

# Specific module
pytest tests/test_ai_service.py -v
```

Tests are fully isolated — each test gets a fresh in-memory job store via the `TestClient` fixture in `conftest.py`.

---

## Performance Considerations

| Concern | Approach |
|---|---|
| **Job queue** | In-memory dict — zero latency, single-worker safe |
| **File I/O** | Async-compatible via `FastAPI.BackgroundTasks` |
| **Gemini latency** | Mitigated by async execution; UI polls asynchronously |
| **File bloat** | TTL cleanup deletes `.pptx` files after 1 hour |
| **Service instantiation** | LRU-cached singletons via `@lru_cache` + `Depends` |
| **Horizontal scaling** | Replace in-memory job store with Redis for multi-worker |

---

## Deployment

### Docker (recommended)

```bash
docker-compose up --build -d
```

The container:
- Exposes port `8000`
- Runs as non-root (`appuser`, UID 1001)
- Healthchecks `GET /api/v1/health` every 30 seconds
- Mounts a named volume for generated files

### Bare Metal / PaaS

```bash
# Production start
uvicorn src.main:app --host 0.0.0.0 --port 8000 --workers 1

# Set ENVIRONMENT=production to disable /docs endpoint
```

> **Note:** Multiple workers share no state. For multi-worker or multi-instance deployments, replace the in-memory job store with Redis and serve files from object storage (S3, GCS).

### Recommended Platforms

| Platform | Notes |
|---|---|
| **Railway** | One-click Docker deploy, managed env vars |
| **Render** | Free tier available, `Dockerfile` auto-detected |
| **Fly.io** | Excellent for stateful, latency-sensitive APIs |
| **AWS ECS / Cloud Run** | Production-grade, add Redis + S3 for scale |

---

## CI/CD

Every push to `main` or `develop` runs the full pipeline:

```
┌─────────┐    ┌──────────────┐    ┌─────────┐    ┌──────────────┐
│  Ruff   │───▶│  MyPy type   │───▶│ pytest  │───▶│ Docker build │
│  lint   │    │    check     │    │  suite  │    │  (no push)   │
└─────────┘    └──────────────┘    └─────────┘    └──────────────┘
```

See [`.github/workflows/ci.yml`](.github/workflows/ci.yml) for the full config.

---

## Screenshots

> Screenshots from the companion frontend at [slide-forge123.vercel.app](https://slide-forge123.vercel.app/)

| | |
|---|---|
| ![Dashboard](docs/screenshots/dashboard.png) | ![Generation Flow](docs/screenshots/generation.png) |
| **Dashboard** — topic input, slide count, theme picker | **Generation** — real-time polling status |
| ![Download](docs/screenshots/download.png) | ![Mobile](docs/screenshots/mobile.png) |
| **Download** — one-click `.pptx` download | **Mobile** — fully responsive UI |

---

## Future Improvements

- **Redis job store** — enable horizontal scaling and worker restarts without losing job state
- **S3 / GCS file backend** — durable file storage decoupled from compute
- **Webhook support** — push notification when job completes (instead of client polling)
- **Custom slide templates** — user-uploadable `.pptx` templates for brand consistency
- **Image generation** — integrate DALL·E or Imagen to fill `image_placeholder` slots
- **User accounts & history** — authenticated users see past generations
- **Streaming status** — Server-Sent Events or WebSocket to replace polling
- **Token usage tracking** — log and expose Gemini token consumption per request
- **Multi-model support** — swap Gemini for OpenAI, Claude, or local LLMs via provider abstraction

---

## Contributing

Contributions are welcome. Please follow the workflow below.

```bash
# 1. Fork and clone
git clone https://github.com/your-username/SlideForge-api.git
cd SlideForge-api

# 2. Create a feature branch
git checkout -b feature/your-feature-name

# 3. Install dev dependencies
pip install -r requirements.txt -r requirements-dev.txt

# 4. Make your changes, then verify
ruff check src/ tests/
mypy src/
pytest --cov=src

# 5. Open a pull request against main
```

**Guidelines:**
- All new code must be type-annotated and pass MyPy
- All new endpoints or services need corresponding tests
- Keep functions small and focused — services handle one concern
- Match the existing JSON logging style for new log statements
- Run `ruff format` before committing

---

## License

This project is licensed under the **MIT License**. See [LICENSE](LICENSE) for details.

---

<div align="center">

Built with FastAPI and Google Gemini · Maintained by [@Engraya](https://github.com/Engraya)

</div>
