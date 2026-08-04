# ═══════════════════════════════════════════════════════
# Multi-stage Docker build: Frontend (Node) → Backend (Python)
# ═══════════════════════════════════════════════════════

# Stage 1: Build Frontend
FROM node:18-slim AS frontend-build
WORKDIR /app/frontend
COPY frontend/package.json frontend/package-lock.json* ./
RUN npm ci --production=false && npm cache clean --force
COPY frontend/ ./
RUN npm run build

# Stage 2: Backend
FROM python:3.11-slim
WORKDIR /app

# System dependencies (minimal to avoid OOM on Railway free tier)
RUN apt-get update -qq && apt-get install -y --no-install-recommends \
    libpq-dev gcc \
    && rm -rf /var/lib/apt/lists/* /var/cache/apt/*

# Python dependencies (layer caching)
COPY backend/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend code
COPY backend/ ./

# Copy built frontend
COPY --from=frontend-build /app/frontend/dist ./static

# Create non-root user
RUN useradd -m -s /bin/bash appuser && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

# Start: init DB then run with gunicorn + uvicorn
CMD ["sh", "-c", "\
    python init_db.py && \
    gunicorn app.main:app \
        -w 2 \
        -k uvicorn.workers.UvicornWorker \
        --bind 0.0.0.0:${PORT:-8000} \
        --access-logfile - \
        --error-logfile - \
        --timeout 120 \
        --keep-alive 5 \
        --max-requests 1000 \
        --max-requests-jitter 50 \
"]
