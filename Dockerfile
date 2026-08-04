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

# Stage 2: Backend (Alpine ~50MB, 3x lighter than slim ~150MB)
FROM python:3.11-alpine
WORKDIR /app

# Alpine needs build deps for packages with C extensions
RUN apk add --no-cache gcc musl-dev libffi-dev

# Single pip install — Alpine base image leaves enough memory on Railway
COPY backend/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Remove build deps to slim final image
RUN apk del gcc musl-dev libffi-dev

# Copy backend code
COPY backend/ ./

# Copy built frontend
COPY --from=frontend-build /app/frontend/dist ./static

# Create non-root user (Alpine: use adduser, no bash)
RUN adduser -D appuser && chown -R appuser:appuser /app
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
