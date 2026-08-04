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

# Install Python deps with serial single-thread, wheel-only to avoid OOM on Railway free tier
COPY backend/requirements.txt ./
RUN pip install --no-cache-dir --only-binary :all: -j 1 -r requirements.txt

# Copy backend code
COPY backend/ ./

# Copy built frontend
COPY --from=frontend-build /app/frontend/dist ./static

# Create non-root user
RUN useradd -m -s /bin/bash appuser && chown -R appuser:appuser /app
USER appuser

EXPOSE 8080

# Start: init DB then run with gunicorn + uvicorn
CMD ["sh", "-c", "\
    python init_db.py && \
    gunicorn app.main:app \
        -w 2 \
        -k uvicorn.workers.UvicornWorker \
        --bind 0.0.0.0:${PORT:-8080} \
        --access-logfile - \
        --error-logfile - \
        --timeout 120 \
        --keep-alive 5 \
        --max-requests 1000 \
        --max-requests-jitter 50 \
"]
