# infty-ocr (Runpod Serverless Worker)

`infty-ocr` is a [Runpod](https://www.runpod.io/) Serverless worker that runs **[olmOCR](https://github.com/allenai/olmocr)**-style **Hugging Face** inference (`Qwen2_5_VLForConditionalGeneration` + `build_no_anchoring_v4_yaml_prompt`). Docker tabanı **[`pytorch/pytorch:2.7.1-cuda12.8-cudnn9-runtime`](https://hub.docker.com/r/pytorch/pytorch)** (Dockerfile’da `BASE_IMAGE` ile değiştirilebilir). **Runpod** tarafında şablonların CUDA hattı **12.8.x** ile uyumlu; **CUDA 12.8** container + güncel host driver bu platformda doğru hizadır. `olmocr` **`pip`** ile kurulur. **`sourceUrl`** veya **S3**. **CLI / vLLM yok.**

## What it does

- **HTTP `sourceUrl`:** Download PDF / PNG / JPEG / WebP, run in-process inference, return text (multi-page PDFs are rendered per page and concatenated).
- **S3 batch:** List keys under a prefix, process a slice with `batch.index` and `batch.size`.
- **Mock:** `OLMOCR_MOCK=true` skips model I/O for cheap smoke tests.

> **Callback** in the schema is reserved; the worker does not POST to webhooks yet.

## Project layout

| Path | Role |
|------|------|
| `handler.py` | Runpod entry (`runpod.serverless.start`) |
| `schemas.py` | Pydantic models |
| `services/ocr_pipeline.py` | Download → `run_olmocr_transformers_on_file` |
| `services/olmocr_transformers_backend.py` | HF model, `render_pdf_to_base64png`, YAML prompt |
| `services/url_io.py` | HTTP download, limits, magic-byte typing |
| `services/s3_io.py` | S3 helpers |
| `Dockerfile` | `pytorch/pytorch` CUDA 12.8 runtime + `poppler-utils` + `pip` |
| `test_input.json` | Local SDK test payload |
| `tests/test_smoke.py` | Mock smoke tests (no GPU) |

## Test (sadece pipeline / handler, GPU yok)

`infty-ocr` klasöründe:

```bash
pip install -r requirements.txt
export OLMOCR_MOCK=true
python -m unittest tests.test_smoke -v
```

Gerçek model + CUDA için container veya Runpod’da `OLMOCR_MOCK=false` kullan.

## Request payload (`input`)

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

Either **`sourceUrl`** or **`s3`** is required.

## Response

```json
{
  "ok": true,
  "documentId": "sha256:abc123",
  "pages": [{ "pageNo": 1, "text": "..." }],
  "provider": "olmocr-transformers",
  "elapsedMs": 1234
}
```

## Environment variables

| Variable | Default | Description |
|----------|---------|-------------|
| `OLMOCR_MOCK` | `true` | `false` in production. |
| `OLMOCR_MODEL_ID` | `allenai/olmOCR-2-7B-1025-FP8` | [Model kartı](https://huggingface.co/allenai/olmOCR-2-7B-1025-FP8) ile aynı id; FP8 / `compressed-tensors` ağırlıklar. |
| `OLMOCR_PROCESSOR_ID` | `Qwen/Qwen2.5-VL-7B-Instruct` | Karttaki “Manual Prompting” ile aynı processor. |
| `OLMOCR_MAX_NEW_TOKENS` | `8192` | `generate` cap per page/image. |
| `OLMOCR_RENDER_LONGEST_DIM` | `1288` | PDF rasterization longest side (px). |
| `OLMOCR_TEMPERATURE` | `0.1` | Sampling temperature. |
| `OLMOCR_TORCH_DTYPE` | — | Optional, e.g. `bfloat16` for `from_pretrained`. |
| `OCR_DOWNLOAD_TIMEOUT_MS` | `30000` | `sourceUrl` download timeout. |
| `OCR_MAX_SOURCE_MB` | `50` | Max download size. |
| `AWS_*` | — | Required for S3 path. |

## Runpod: disk, GPU, CUDA

- **Disk:** HF cache + weights — **≥50 GB** (80–100 GB rahat).
- **GPU:** 7B VLM için **L40 / L40S** sınıfı; mümkünse **GPU başına tek ağır iş**.
- **CUDA / imaj:** Worker özel Docker kullanır; Runpod host’u **NVIDIA driver + container toolkit** ile CUDA kütüphanelerini bağlar. **12.8 runtime** tabanı, [Runpod’un CUDA 12.8 şablon hattı](https://github.com/runpod/containers/blob/main/official-templates/shared/versions.hcl) ile aynı majör hat. Eski **12.4** imajları çoğu node’da çalışır (12.x uyumu) ama **12.8 pin** daha tutarlıdır.
- **Build:** `docker build --platform linux/amd64 ...` (Runpod tipik arch).

## Local run

**Python 3.11+** zorunlu (`olmocr>=0.4` PyPI sınırlaması). GPU ile gerçek OCR için CUDA’lı PyTorch ortamı gerekir (macOS’ta genelde sadece mock / CPU denemesi).

```bash
python3.11 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
OLMOCR_MOCK=true python handler.py   # veya: python -m unittest discover -s tests -v
```

Runpod üretimde **`OLMOCR_MOCK=false`**; ilk çalıştırmada model indirme için `HF_TOKEN` (özel/gated repo yoksa opsiyonel) ve bol disk.

## Docker

```bash
docker build --platform linux/amd64 -t your-registry/infty-ocr:0.1.0 .
```

Deploy: Serverless endpoint, GPU template, `OLMOCR_MOCK=false`, large enough disk, image from this `Dockerfile`.

## License

Worker code: your repo license. **olmOCR** is [Apache-2.0](https://github.com/allenai/olmocr/blob/main/LICENSE).
