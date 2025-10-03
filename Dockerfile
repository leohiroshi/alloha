# Alloha.app - AI Chat System for Real Estate
# Dockerfile for Azure Container Apps deployment

FROM python:3.10-slim

# Build args
ARG INSTALL_BROWSER=false
ARG INSTALL_TORCH=true

WORKDIR /app

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    ENABLE_SCRAPER=${ENABLE_SCRAPER:-true}

# System deps (curl needed for healthcheck and optional browser installs)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc g++ curl wget gnupg ca-certificates libnss3 \
    && rm -rf /var/lib/apt/lists/*

# If you need browser for Selenium, enable at build: --build-arg INSTALL_BROWSER=true
# This installs Chromium and chromedriver on Debian-based slim images (may be adjusted per base image)
RUN if [ "$INSTALL_BROWSER" = "true" ] ; then \
            echo "--> Instalando Chromium e dependências" && \
            apt-get update && apt-get install -y \
                chromium chromium-driver \
                fonts-liberation libasound2 libatk-bridge2.0-0 libatk1.0-0 libatspi2.0-0 \
                libdrm2 libgbm1 libgtk-3-0 libnspr4 libnss3 libx11-6 libx11-xcb1 libxcb1 \
                libxcomposite1 libxcursor1 libxdamage1 libxext6 libxfixes3 libxi6 libxrandr2 \
                libxrender1 libxshmfence1 libxss1 libxtst6 libxkbcommon0 libpango-1.0-0 libpangocairo-1.0-0 \
                libglib2.0-0 \
            && rm -rf /var/lib/apt/lists/* \
            && echo "Chromium instalado" ; \
        else \
            echo "--> BUILD sem navegador (INSTALL_BROWSER=false)" ; \
        fi

ENV CHROME_BINARY=/usr/bin/chromium \
        CHROMEDRIVER_PATH=/usr/bin/chromedriver

# Copy requirements for caching
COPY requirements.txt /app/requirements.txt

# Force compatible numpy (<2.0) first to avoid incompatible wheels being pulled
RUN pip install --no-cache-dir "numpy<2.0.0"

# Install torch CPU wheel (recommended to pin CPU wheel appropriate to your target):
# Example (adjust version/platform as needed) — comment out if you're not using sentence-transformers with torch
RUN if [ "$INSTALL_TORCH" = "true" ] ; then \
      pip install --no-cache-dir --index-url https://download.pytorch.org/whl/cpu "torch==2.2.2+cpu" ; \
    fi

# Install remaining Python deps
RUN pip install --no-cache-dir -r /app/requirements.txt

# Copy only runtime code (keep out secrets)
# - app/: Python application package
COPY app/ /app/app

# Ensure app path is on PYTHONPATH
ENV PYTHONPATH=/app

# Create non-root user and set ownership
RUN useradd --create-home --shell /bin/bash appuser \
    && chown -R appuser:appuser /app
USER appuser

# Expose port and healthcheck
EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=30s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run the application
CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
