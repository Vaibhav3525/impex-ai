# ==============================================================================
# ImpEx AI — Single Unified All-in-One Production Dockerfile
# Serves Next.js Frontend + FastAPI Backend + Real Buyers DB on a Single Port
# Compatible with 100% Free Tiers: Render, Koyeb, Railway, Fly.io, Hugging Face
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
ENV DATABASE_URL=sqlite:///./impex_leads.db
ENV ALLOWED_ORIGINS=*

# Seed authentic verified buyer data on build
RUN python scripts/seed_verified_real_buyers.py

EXPOSE 8000

# Start unified Uvicorn server (automatically binds to Render's dynamic $PORT or 8000)
CMD ["sh", "-c", "python -m uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]


