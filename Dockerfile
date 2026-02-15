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

# Runtime deps for MediaPipe (libGL + libglib) + curl for model download
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        libgl1 \
        libglib2.0-0 \
        curl && \
    rm -rf /var/lib/apt/lists/*

# Download MediaPipe PoseLandmarker model (full, matches old model_complexity=1)
RUN mkdir -p /app/models && \
    curl -fsSL -o /app/models/pose_landmarker_full.task \
    https://storage.googleapis.com/mediapipe-models/pose_landmarker/pose_landmarker_full/float16/latest/pose_landmarker_full.task

COPY --from=builder /install /usr/local

COPY . .

EXPOSE 8000

ENTRYPOINT ["python", "main.py"]
