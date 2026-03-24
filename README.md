# infty-ocr (Runpod Worker)

`infty-ocr`, Runpod Serverless GPU endpoint'inde calisacak local olmOCR worker'idir.

## Amac

- S3'teki PDF/sayfa image dosyalarini al
- olmOCR'u container icinde local GPU ile calistir
- Sonucu sync response veya callback URL ile geri gonder

## Ilk Surum Kapsami

- Queue-based Runpod worker (handler tabanli)
- `submit_ocr_job` operasyonu
- S3 manifest odakli calisma
- S3'ten dosya indirip `olmocr` komutuyla local pipeline calistirma
- `OLMOCR_MOCK=true` ile local mock test

## Input Contract (ornek)

```json
{
  "operation": "submit_ocr_job",
  "documentId": "sha256:abc123",
  "sourceUrl": "https://example.com/sample.pdf",
  "lang": "tur+eng",
  "batch": {
    "size": 10,
    "index": 0
  },
  "callback": {
    "url": "https://api.example.com/ocr/callback",
    "token": "optional-shared-secret"
  }
}
```

## Output Contract (ornek)

```json
{
  "ok": true,
  "documentId": "sha256:abc123",
  "pages": [
    { "pageNo": 1, "text": "..." }
  ],
  "meta": {
    "provider": "olmocr",
    "elapsedMs": 1234
  }
}
```

## Dosya Yapisi

- `handler.py`: Runpod handler giris noktasi
- `services/ocr_pipeline.py`: OCR orchestration
- `services/s3_io.py`: S3 okuma/yazma yardimcilari
- `schemas.py`: request/response schema yardimcilari
- `Dockerfile`: worker image

## Local Run

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python handler.py
```

## Environment Variables

- `AWS_REGION`
- `AWS_ACCESS_KEY_ID`
- `AWS_SECRET_ACCESS_KEY`
- `OCR_DOWNLOAD_TIMEOUT_MS` (varsayilan `30000`)
- `OCR_MAX_SOURCE_MB` (varsayilan `50`)
- `OLMOCR_TIMEOUT_MS` (varsayilan `120000`)
- `OLMOCR_MOCK` (varsayilan `true`)
- `OLMOCR_CMD_TEMPLATE` (varsayilan: `olmocr "{workspace}" --markdown --pdfs "{input}" --workers 1 --pages_per_group 1`)

`sourceUrl` icin desteklenen tipler: `pdf`, `png`, `jpg/jpeg`, `webp`.

## GPU Notu

- Bu worker local olmOCR GPU akisi icin planlandi.
- Runpod Endpoint olustururken GPU tipi secilmelidir.
- Trafik artinca `workers/pages_per_group` degerleri artirilabilir.

## Next Steps

1. Manifest bazli page batching
2. Callback imza dogrulama (HMAC)
3. Idempotency + retry politikalari
4. OCR confidence/raw metadata gecisi
