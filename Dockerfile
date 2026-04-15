# ── Beelup Downloader — Dockerfile ──────────────────────────────────────────
FROM python:3.14-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Create a non-root user to mitigate root-container vulnerabilities
RUN useradd -m -u 1000 appuser

# Install updates and ffmpeg to patch OS-level CVEs
RUN set -eux; \
    . /etc/os-release; \
    test "$VERSION_CODENAME" = "bookworm"; \
    rm -f /etc/apt/sources.list; \
    rm -f /etc/apt/sources.list.d/*; \
    printf '%s\n' \
        'Types: deb' \
        'URIs: http://deb.debian.org/debian' \
        'Suites: bookworm bookworm-updates' \
        'Components: main' \
        'Signed-By: /usr/share/keyrings/debian-archive-keyring.gpg' \
        '' \
        'Types: deb' \
        'URIs: http://security.debian.org/debian-security' \
        'Suites: bookworm-security' \
        'Components: main' \
        'Signed-By: /usr/share/keyrings/debian-archive-keyring.gpg' \
        > /etc/apt/sources.list.d/debian.sources; \
    if grep -RqsE '(trixie|deb13)' /etc/apt/sources.list.d /etc/apt/sources.list 2>/dev/null; then exit 1; fi; \
    apt-get update; \
    apt-get dist-upgrade -y; \
    apt-get install -y --no-install-recommends ffmpeg; \
    apt-get autoremove -y; \
    apt-get clean; \
    rm -rf /var/lib/apt/lists/* /var/cache/apt/archives/*

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
