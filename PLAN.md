# infty-ocr Yol Haritasi

## Faz 1 - Worker Iskeleti (tamamlandi)

- Runpod handler giris noktasi
- Input/Output schema tanimi
- Dockerfile + requirements
- Mock OCR pipeline

## Faz 2 - S3 Manifest + Batch

- `manifest.json` formati:
  - `documentId`
  - `pages[]` (`pageNo`, `s3Key`, `checksum`)
  - `createdAt`
- Worker sadece gelen batch index/size araligini isler
- Sonuc `pages[]` olarak dondurulur

## Faz 3 - olmOCR Entegrasyonu

- Provider adapter katmani:
  - `extract_text_from_image(s3_uri, lang)`
- Timeout/retry ve error mapping
- OCR confidence ve raw json saklama (opsiyonel)

## Faz 4 - Callback/Webhook

- Worker sonucu `callback.url` adresine POST eder
- `X-OCR-Signature` (HMAC) ile dogrulama
- Idempotency key: `documentId:batchIndex`

## Faz 5 - Uretim Sertlestirme

- CloudWatch/Runpod log standardi
- Dead-letter queue stratejisi
- Metrics: p95 latency, fail ratio, page/sec
