# syntax=docker/dockerfile:1

# ---- Build stage: resolve and build all wheels once -------------------------
FROM python:3.12-slim AS builder

WORKDIR /build
COPY pyproject.toml README.md ./
COPY src ./src
RUN pip install --no-cache-dir --upgrade pip \
    && pip wheel --no-cache-dir --wheel-dir /wheels ".[api,pgvector,aws,azure,otel]"

# ---- Runtime stage: slim image, non-root user --------------------------------
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    APP_HOME=/app \
    PORT=8000 \
    LOG_FORMAT=json

RUN useradd --create-home --uid 10001 app
WORKDIR /app

COPY --from=builder /wheels /wheels
RUN pip install --no-cache-dir /wheels/*.whl && rm -rf /wheels

# Small reference data baked into the image; large corpora are mounted or read from the vector store
COPY data/metadata ./data/metadata
COPY data/samples ./data/samples
RUN mkdir -p data/logs && chown -R app:app /app

USER app
EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=3)"

CMD ["legal-rag-api"]
