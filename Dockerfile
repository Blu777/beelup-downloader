# ── Beelup Downloader — Dockerfile ──────────────────────────────────────────
FROM python:3.14-alpine

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Create a non-root user to mitigate root-container vulnerabilities
RUN adduser -D -u 1000 appuser

# Install updates and ffmpeg to patch OS-level CVEs
RUN apk --no-cache upgrade && \
    apk --no-cache add ffmpeg

WORKDIR /app

# Install Python dependencies first (better layer caching)
COPY requirements.txt .
RUN apk --no-cache add --virtual .build-deps build-base linux-headers && \
    pip install --upgrade pip setuptools wheel && \
    pip install --no-cache-dir -r requirements.txt && \
    apk del .build-deps

# Copy application source (omitting unused legacy scripts)
COPY app.py downloader_core.py ./
COPY static/ ./static/
COPY templates/ ./templates/

# Persistent storage directories mapped via volume
RUN mkdir -p downloads temp && \
    chown -R appuser:appuser /app

# Switch to non-root user
USER appuser

EXPOSE 5000

CMD ["python", "app.py"]
