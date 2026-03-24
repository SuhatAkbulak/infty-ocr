FROM alleninstituteforai/olmocr:latest

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN python3 -m pip install --no-cache-dir -r requirements.txt

COPY . .

# Base image may ship a broken /usr/bin/python on some platforms; Runpod is linux/amd64.
# Clear inherited ENTRYPOINT so Serverless runs our process directly.
ENTRYPOINT []
CMD ["python3", "-u", "handler.py"]
