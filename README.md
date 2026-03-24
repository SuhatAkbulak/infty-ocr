# infty-ocr (Runpod Serverless Worker)

`infty-ocr` is a [Runpod](https://www.runpod.io/) Serverless worker that runs **[olmOCR](https://github.com/allenai/olmocr)** on top of the official Docker image [`alleninstituteforai/olmocr`](https://hub.docker.com/r/alleninstituteforai/olmocr). It accepts a public **`sourceUrl`** (PDF or image) or **S3** keys, runs the `olmocr` CLI inside the container, and returns extracted text.

## What it does

- **V1 – HTTP source:** Download a file from `sourceUrl`, detect type (PDF / PNG / JPEG / WebP), run `olmocr`, read Markdown output from the workspace.
- **S3 batch (optional):** List image keys under a prefix, process a slice using `batch.index` and `batch.size`.
- **Mock mode:** Skip real OCR for cheap local smoke tests (`OLMOCR_MOCK=true`).

> **Callback** fields exist in the request schema for future use; the worker does not POST to a webhook yet.

## Project layout

| Path | Role |
|------|------|
| `handler.py` | Runpod serverless entry (`runpod.serverless.start`) |
| `schemas.py` | Pydantic request/response models |
| `services/ocr_pipeline.py` | Download → `olmocr` subprocess → collect output |
| `services/url_io.py` | HTTP download, size limit, magic-byte type check |
| `services/s3_io.py` | S3 list + download helpers |
| `Dockerfile` | `FROM alleninstituteforai/olmocr:latest` + app code |
| `test_input.json` | Local Runpod SDK test payload |

## Request payload (Runpod `input`)

```json
{
  "input": {
    "operation": "submit_ocr_job",
    "documentId": "sha256:abc123",
    "sourceUrl": "https://example.com/document.pdf",
    "lang": "tur+eng",
    "batch": { "size": 1, "index": 0 }
  }
}
```

Either **`sourceUrl`** or **`s3`** must be provided (`s3` is optional when `sourceUrl` is set).

**S3 variant:**

```json
{
  "input": {
    "operation": "submit_ocr_job",
    "documentId": "sha256:abc123",
    "s3": {
      "bucket": "my-bucket",
      "prefix": "temps-jobs/abc123/pages/",
      "region": "eu-central-1"
    },
    "lang": "tur+eng",
    "batch": { "size": 10, "index": 0 }
  }
}
```

## Response shape

Successful handler output (shape from `OcrJobOutput`):

```json
{
  "ok": true,
  "documentId": "sha256:abc123",
  "pages": [
    { "pageNo": 1, "text": "..." }
  ],
  "provider": "olmocr",
  "elapsedMs": 1234
}
```

On failure, the handler may return:

```json
{
  "ok": false,
  "error": "error message"
}
```

## Environment variables

| Variable | Default | Description |
|----------|---------|-------------|
| `OLMOCR_MOCK` | `true` | If `true`, no download/OCR; returns placeholder text. Set `false` in production. |
| `OLMOCR_TIMEOUT_MS` | `120000` | Subprocess timeout for `olmocr` (ms). |
| `OLMOCR_CMD_TEMPLATE` | see below | Shell command template; placeholders: `{workspace}`, `{input}`, `{lang}`. |
| `OCR_DOWNLOAD_TIMEOUT_MS` | `30000` | HTTP download timeout for `sourceUrl` (ms). |
| `OCR_MAX_SOURCE_MB` | `50` | Max download size for `sourceUrl`. |
| `AWS_REGION` | — | Required for S3 path. |
| `AWS_ACCESS_KEY_ID` | — | Required for S3 path. |
| `AWS_SECRET_ACCESS_KEY` | — | Required for S3 path. |

Default command template:

```text
olmocr "{workspace}" --markdown --pdfs "{input}" --workers 1 --pages_per_group 1
```

Copy `.env.example` to `.env` for local reference (do not commit secrets).

## Local development

```bash
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python handler.py
```

With `test_input.json` present, the Runpod SDK runs one local job and exits.

## Docker image

- Base: **`alleninstituteforai/olmocr:latest`** (large; includes the olmOCR stack).
- Build context: this directory (`runpod-workers/infty-ocr`).
- Start command: `python handler.py` (set in `Dockerfile` `CMD`).

Build locally (amd64 for Runpod):

```bash
docker build --platform linux/amd64 -t your-registry/infty-ocr:0.1.0 .
```

## Deploying on Runpod

1. Push this repo to GitHub (or build and push the image to Docker Hub).
2. Create a **Serverless** endpoint:
   - **Queue** workers
   - **GPU** suitable for olmOCR (see [olmocr docs](https://github.com/allenai/olmocr))
3. Point Runpod at:
   - your **Docker image**, or  
   - **GitHub** build with `Dockerfile` path = `Dockerfile` and build context = this folder.
4. Set environment variables (at minimum `OLMOCR_MOCK=false` and AWS creds if using S3).

See also `RUNPOD_SERVERLESS_TEMPLATE_STEPS.md` in this repo for a step-by-step checklist.

## Roadmap

- Manifest-based page batching and stronger idempotency  
- Signed webhook / HMAC callback delivery  
- Optional remote inference (`--server`) for a smaller worker image  
- Richer metadata (confidence, raw model output) in responses

## License

Application code in this worker follows your repo’s license. **olmOCR** is [Apache-2.0](https://github.com/allenai/olmocr/blob/main/LICENSE).
