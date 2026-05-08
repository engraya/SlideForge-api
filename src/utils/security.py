import re
import unicodedata
import uuid
from pathlib import Path

_SAFE_FILENAME_RE = re.compile(r"[^\w\s-]", re.UNICODE)
_WHITESPACE_RE = re.compile(r"[\s]+")


def sanitize_topic_for_filename(topic: str) -> str:
    normalized = unicodedata.normalize("NFKD", topic)
    ascii_topic = normalized.encode("ascii", "ignore").decode("ascii")
    safe = _SAFE_FILENAME_RE.sub("", ascii_topic)
    safe = _WHITESPACE_RE.sub("_", safe.strip())
    return safe[:50].strip("_") or "presentation"


def generate_safe_filename(topic: str) -> str:
    slug = sanitize_topic_for_filename(topic)
    unique_id = uuid.uuid4().hex[:12]
    return f"{slug}_{unique_id}.pptx"


def get_safe_file_path(filename: str, output_dir: Path) -> Path:
    """
    Resolves filename relative to output_dir and raises ValueError if the
    resolved path escapes the directory. Uses Path.name as first-layer defense
    (strips all directory components), then resolve()+prefix check as second layer.
    """
    base = output_dir.resolve()
    clean_filename = Path(filename).name
    candidate = (base / clean_filename).resolve()

    base_str = str(base)
    candidate_str = str(candidate)
    if not (candidate_str.startswith(base_str + "\\") or
            candidate_str.startswith(base_str + "/") or
            candidate_str == base_str):
        raise ValueError(
            f"Path traversal detected: '{filename}' resolves outside output directory."
        )

    return candidate
