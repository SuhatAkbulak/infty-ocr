from pathlib import Path
from urllib.parse import urlparse
import requests


def validate_http_url(value: str) -> None:
    parsed = urlparse(value)
    if parsed.scheme not in {"http", "https"}:
        raise RuntimeError("sourceUrl sadece http/https olabilir.")
    if not parsed.netloc:
        raise RuntimeError("sourceUrl gecersiz.")


def _detect_type_from_magic(file_path: Path) -> str:
    with file_path.open("rb") as f:
        magic = f.read(12)

    if magic.startswith(b"%PDF-"):
        return "pdf"
    if magic.startswith(b"\x89PNG\r\n\x1a\n"):
        return "png"
    if magic.startswith(b"\xff\xd8\xff"):
        return "jpg"
    if magic.startswith(b"RIFF") and magic[8:12] == b"WEBP":
        return "webp"
    return "unknown"


def download_source_url(url: str, dest_path: Path, timeout_ms: int, max_source_mb: int) -> str:
    validate_http_url(url)
    dest_path.parent.mkdir(parents=True, exist_ok=True)

    total_limit = max_source_mb * 1024 * 1024
    downloaded = 0
    with requests.get(url, stream=True, timeout=timeout_ms / 1000) as resp:
        resp.raise_for_status()

        with dest_path.open("wb") as f:
            for chunk in resp.iter_content(chunk_size=1024 * 256):
                if not chunk:
                    continue
                downloaded += len(chunk)
                if downloaded > total_limit:
                    raise RuntimeError(f"Dosya boyutu limit asimi: {max_source_mb}MB")
                f.write(chunk)

    detected = _detect_type_from_magic(dest_path)
    if detected not in {"pdf", "png", "jpg", "webp"}:
        raise RuntimeError("Desteklenmeyen dosya tipi. Sadece PDF/PNG/JPG/WEBP kabul edilir.")
    return detected
