## ---- Builder stage ----
FROM python:3.12-slim AS builder

WORKDIR /build

# System deps for Pillow and MediaPipe
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        build-essential \
        libgl1 \
        libglib2.0-0 && \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

## ---- Runtime stage ----
FROM python:3.12-slim

WORKDIR /app

# Runtime deps for MediaPipe (libGL + libglib)
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        libgl1 \
        libglib2.0-0 && \
    rm -rf /var/lib/apt/lists/*

COPY --from=builder /install /usr/local

COPY . .

EXPOSE 8000

ENTRYPOINT ["python", "main.py"]
