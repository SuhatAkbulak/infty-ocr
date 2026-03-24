# Runpod: linux/amd64, host NVIDIA driver GPU ile nvidia-container-runtime.
#
# Uyum notu:
# - Runpod resmi imajlari CUDA 12.8.x kullaniyor (github.com/runpod/containers versions.hcl).
# - pytorch ... cuda12.8 runtime, bu host ler ile hizali; cuda12.4 eski ama genelde yine calisir
#   (CUDA 12.x minor compatibility; driver tipik olarak 525+).
# - Tag secimi: resmi pytorch/pytorch, cudnn9-runtime (devel degil = daha kucuk).
#
# Baska surum: build-arg ile degistir
#   docker build --build-arg BASE_IMAGE=pytorch/pytorch:2.10.0-cuda12.8-cudnn9-runtime ...
ARG BASE_IMAGE=pytorch/pytorch:2.7.1-cuda12.8-cudnn9-runtime
FROM ${BASE_IMAGE}

# olmocr>=0.4 (HF karti) sadece Python 3.11+ wheel yukluyor.
RUN python -c "import sys; v=sys.version_info; assert (v.major,v.minor)>=(3,11), f'Python 3.11+ gerekli, bu imaj {v.major}.{v.minor}. BASE_IMAGE degistir.'"

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DEBIAN_FRONTEND=noninteractive

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    poppler-utils \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENTRYPOINT []
CMD ["python", "-u", "handler.py"]
