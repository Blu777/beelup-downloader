# ── Beelup Downloader — Dockerfile ──────────────────────────────────────────
FROM python:3.12-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Create a non-root user to mitigate root-container vulnerabilities
RUN useradd -m -u 1000 appuser

# Install updates and ffmpeg to patch OS-level CVEs
RUN apt-get update && \
    apt-get upgrade -y && \
    apt-get install -y --no-install-recommends ffmpeg && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies first (better layer caching)
COPY requirements.txt .
RUN pip install --upgrade pip setuptools wheel && \
    pip install --no-cache-dir -r requirements.txt

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
