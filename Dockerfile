#############################
# Stage 1: Builder / Dependencies
#############################
FROM python:3.10-slim AS builder

ARG INSTALL_BROWSER=false
ARG INSTALL_TORCH=true
ARG PRELOAD_MODELS=true

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /build

# System build deps (removed later)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc g++ build-essential \
    curl wget gnupg ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Optional browser (Selenium) layer
RUN if [ "$INSTALL_BROWSER" = "true" ]; then \
      apt-get update && apt-get install -y --no-install-recommends chromium chromium-driver && \
      rm -rf /var/lib/apt/lists/* ; \
    fi

# Copy only requirements first (cache layer)
COPY requirements.txt requirements.txt

# Install base numeric dep early to stabilize wheels
RUN pip install "numpy<2.0.0"

# Torch (CPU) optional
RUN if [ "$INSTALL_TORCH" = "true" ]; then \
      pip install --index-url https://download.pytorch.org/whl/cpu "torch==2.2.2+cpu" ; \
    fi

# Remaining deps
RUN pip install -r requirements.txt

# Preload models to reduce cold start (stored under /root/.cache)
RUN if [ "$PRELOAD_MODELS" = "true" ]; then \
    python -c "from sentence_transformers import SentenceTransformer, CrossEncoder; SentenceTransformer('all-MiniLM-L6-v2'); CrossEncoder('cross-encoder/ms-marco-MiniLM-L-6-v2'); print('Models preloaded')" ; \
    fi

# Create a virtualenv (optional slimming technique)
RUN python -m venv /venv && /venv/bin/pip install --upgrade pip && \
    /venv/bin/pip install -r requirements.txt && \
    if [ "$INSTALL_TORCH" = "true" ]; then /venv/bin/pip install --index-url https://download.pytorch.org/whl/cpu "torch==2.2.2+cpu" ; fi

#############################
# Stage 2: Runtime Image
#############################
FROM python:3.10-slim AS runtime
ARG INSTALL_BROWSER=false

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/venv/bin:$PATH" \
    PYTHONPATH=/app

WORKDIR /app

# Minimal runtime deps (curl for healthcheck)
RUN apt-get update && apt-get install -y --no-install-recommends curl ca-certificates && rm -rf /var/lib/apt/lists/*

# Optional browser runtime (if absolutely required at runtime)
RUN if [ "$INSTALL_BROWSER" = "true" ]; then \
      apt-get update && apt-get install -y --no-install-recommends chromium chromium-driver && \
      rm -rf /var/lib/apt/lists/* ; \
    fi

# Copy virtualenv from builder
COPY --from=builder /venv /venv
# Copy model cache (sentence-transformers) if preloaded
COPY --from=builder /root/.cache /root/.cache

# Copy application code
COPY app/ /app/app

# Non-root user
RUN useradd --create-home --shell /bin/bash appuser && chown -R appuser:appuser /app /root/.cache || true
USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=30s --start-period=60s --retries=3 \
  CMD curl -f http://localhost:8000/health || exit 1

LABEL org.opencontainers.image.title="Alloha Backend" \
      org.opencontainers.image.source="https://example.com/repo" \
      org.opencontainers.image.description="AI Real Estate Chat (Supabase + RAG)" \
      org.opencontainers.image.licenses="Proprietary"

# Default command (single worker) - override with UVICORN_WORKERS env if desired in entrypoint
CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
