# ==============================================================================
# ImpEx AI production image: static frontend and FastAPI server.
# A separate worker and managed PostgreSQL service are required for automation.
# ==============================================================================

# Stage 1: Build Next.js Static Frontend
FROM node:20-alpine AS frontend-builder
WORKDIR /app/frontend

COPY frontend/package.json frontend/package-lock.json* ./
RUN npm ci

COPY frontend ./
ENV NEXT_TELEMETRY_DISABLED=1
ENV NODE_ENV=production
RUN npm run build

# Stage 2: Python FastAPI Backend & Unified Server
FROM python:3.11-slim AS runner
WORKDIR /app

# Install system utilities
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python requirements
COPY backend/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy Backend Source Code
COPY backend /app/backend
WORKDIR /app/backend

# Copy Pre-Built Frontend Static Assets directly into the container
COPY --from=frontend-builder /app/frontend/out /app/frontend/out

# Environment Configuration
ENV PORT=8000
ENV HOST=0.0.0.0
ENV APP_ENV=production
ENV DEBUG=False
# Production supplies persistent DATABASE_URL, exact ALLOWED_ORIGINS and credentials.
# Seeding is an explicit administrative operation, never a container build step.

EXPOSE 8000

# Start unified Uvicorn server (automatically binds to Render's dynamic $PORT or 8000)
CMD ["sh", "-c", "python -m uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]


