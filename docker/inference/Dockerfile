FROM nvidia/cuda:12.4.1-runtime-ubuntu22.04

ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1
ENV PIP_NO_CACHE_DIR=1

ENV NVIDIA_VISIBLE_DEVICES=all
ENV NVIDIA_DRIVER_CAPABILITIES=compute,utility
ENV LD_LIBRARY_PATH=/usr/local/nvidia/lib64:/usr/local/nvidia/lib:/usr/lib64:/usr/lib/x86_64-linux-gnu:${LD_LIBRARY_PATH}
ENV CC=/usr/bin/gcc
ENV CXX=/usr/bin/g++

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 \
    python3-dev \
    python3-pip \
    python3-venv \
    git \
    curl \
    ca-certificates \
    build-essential \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

RUN python3 -m pip install --upgrade pip setuptools wheel

COPY requirements.txt /app/requirements.txt

RUN python3 -m pip install -r /app/requirements.txt

COPY src /app/src

RUN cat > /app/start.sh <<'EOF'
#!/usr/bin/env bash
set -e

mkdir -p /usr/lib64

if [ -f /usr/local/nvidia/lib64/libcuda.so.1 ]; then
  ln -sf /usr/local/nvidia/lib64/libcuda.so.1 /usr/lib64/libcuda.so.1
elif [ -f /usr/lib/x86_64-linux-gnu/libcuda.so.1 ]; then
  ln -sf /usr/lib/x86_64-linux-gnu/libcuda.so.1 /usr/lib64/libcuda.so.1
fi

exec python3 -m uvicorn src.api.main:app --host 0.0.0.0 --port 8000
EOF

RUN chmod +x /app/start.sh

ENV PYTHONPATH=/app
ENV HF_HOME=/tmp/hf-cache
ENV TRANSFORMERS_CACHE=/tmp/hf-cache
ENV HUGGINGFACE_HUB_CACHE=/tmp/hf-cache
ENV TRITON_CACHE_DIR=/tmp/triton-cache

EXPOSE 8000

CMD ["/app/start.sh"]
