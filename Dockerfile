# Stage 1: Build Vite Frontend
FROM node:20-slim AS frontend-builder
WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm install
COPY frontend/ ./
RUN npm run build

# Stage 2: Python Backend with Playwright Headless Chromium
FROM python:3.12-slim
ENV PYTHONUNBUFFERED=1 \
    DEBIAN_FRONTEND=noninteractive \
    PATHLENS_PROVIDER=gemini \
    PATHLENS_HEADLESS=true

WORKDIR /app

# Install system dependencies required by Playwright and curl for healthchecks
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN playwright install --with-deps chromium

# Copy application code
COPY . .

# Copy built frontend assets into frontend/dist for FastAPI static file serving
COPY --from=frontend-builder /app/frontend/dist /app/frontend/dist

# Expose default port (overridden by $PORT in cloud environments)
EXPOSE 8000

# Start server respecting $PORT dynamically assigned by Railway/Render/Cloud Run/Fly
CMD ["sh", "-c", "uvicorn backend.api.app:app --host 0.0.0.0 --port ${PORT:-8000}"]
