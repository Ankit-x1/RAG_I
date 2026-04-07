# === Production RAG Backend Dockerfile ===
FROM python:3.11-slim

# === Metadata ===
LABEL maintainer="Tuning Neural" \
    version="2.0.0" \
    description="Enterprise-grade Retrieval-Augmented Generation system"

# === Build-time Variables ===
ARG DEBIAN_FRONTEND=noninteractive
ARG PIP_NO_CACHE_DIR=1

# === environment Variables ===
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    LOG_LEVEL=INFO \
    ENVIRONMENT=production

# === System Dependencies ===
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# === Working Directory ===
WORKDIR /app

# === Copy Project Files ===
COPY requirements.txt .
COPY . .

# === Install Python Dependencies ===
RUN pip install --upgrade pip setuptools wheel && \
    pip install -r requirements.txt && \
    pip install uvicorn[standard] gunicorn

# === Create Non-Root User for Security ===
RUN useradd -m -u 1000 raguser && \
    chown -R raguser:raguser /app

USER raguser

# === Health Check ===
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# === Port Exposure ===
EXPOSE 8000

# === Startup Command ===
CMD ["uvicorn", "backend.api.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
