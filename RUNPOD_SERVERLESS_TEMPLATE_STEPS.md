# Runpod Serverless Template Adimlari (infty-ocr)

Bu dokuman, `infty-ocr` worker'ini Runpod Serverless'e deploy etmek icin dogrudan uygulanabilir adimlari verir.

Kaynak: Runpod Quickstart

## 0) Gereksinimler

- Runpod hesabi
- Docker kurulu
- Python 3.x kurulu
- Bir container registry hesabi (GHCR veya Docker Hub)

## 1) Lokal handler testi

`runpod-workers/infty-ocr` klasorunde:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python handler.py
```

Not: `runpod` SDK lokal testte `test_input.json` kullanabilir. Gerekirse asagidaki dosyayi ekleyin:

```json
{
  "input": {
    "operation": "submit_ocr_job",
    "documentId": "sha256:test123",
    "pdfUrl": "https://example.com/sample.pdf",
    "lang": "tur+eng",
    "batch": {
      "size": 1,
      "index": 0
    }
  }
}
```

## 2) Docker image build

Runpod uyumlulugu icin `linux/amd64` platformuyla build alin:

```bash
docker build --platform linux/amd64 -t ghcr.io/<GITHUB_USER>/<REPO>-infty-ocr:0.1.0 .
```

## 3) Registry'e push

### GHCR ornegi

```bash
echo <GITHUB_TOKEN> | docker login ghcr.io -u <GITHUB_USER> --password-stdin
docker push ghcr.io/<GITHUB_USER>/<REPO>-infty-ocr:0.1.0
```

### Docker Hub ornegi

```bash
docker login
docker tag ghcr.io/<GITHUB_USER>/<REPO>-infty-ocr:0.1.0 <DOCKER_USER>/infty-ocr:0.1.0
docker push <DOCKER_USER>/infty-ocr:0.1.0
```

## 4) Runpod Serverless Template olusturma

Runpod Console:

1. `Serverless` bolumune girin.
2. `New Endpoint` (veya image import) akisini baslatin.
3. `Import from Docker Registry` secin.
4. Container image alanina image URL girin:
   - GHCR: `ghcr.io/<GITHUB_USER>/<REPO>-infty-ocr:0.1.0`
   - Docker Hub: `docker.io/<DOCKER_USER>/infty-ocr:0.1.0`
5. Endpoint Type: `Queue` secin.
6. Worker calisirken gerekli environment variable'lari ekleyin:
   - `AWS_REGION`
   - `AWS_ACCESS_KEY_ID`
   - `AWS_SECRET_ACCESS_KEY`
   - `OCR_CALLBACK_SECRET` (opsiyonel)
7. Deploy edin.

## 5) Endpoint test

Endpoint detail sayfasinda `Requests` tabindan su payload ile test edin:

```json
{
  "input": {
    "operation": "submit_ocr_job",
    "documentId": "sha256:test123",
    "pdfUrl": "https://example.com/sample.pdf",
    "lang": "tur+eng",
    "batch": {
      "size": 1,
      "index": 0
    }
  }
}
```

Basarili durumda `output.ok = true` ve `output.pages[]` doner.

## 6) Onerilen production ayarlari

- Min workers: `0` (tam serverless maliyet optimizasyonu)
- Max workers: trafik beklentisine gore `3-10`
- Retry: idempotency key (`documentId:batchIndex`) ile guvenli tekrar
- Versiyonlama: image tag'lerini sabit tutun (`0.1.0`, `0.1.1`, ...)

## 7) Hata durumlari hizli kontrol listesi

- `Image pull error`: registry izinleri/public-private ayari
- `Handler crash`: `handler.py` ve `requirements.txt` uyumsuzlugu
- `S3 access denied`: AWS IAM policy eksigi
- `Timeout`: batch size dusur (ornek `size=2..5`)
