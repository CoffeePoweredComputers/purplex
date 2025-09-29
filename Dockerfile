# =====================================================================================
# PURPLEX DJANGO APPLICATION DOCKERFILE
# =====================================================================================
# Multi-stage build for optimized production image
# =====================================================================================

# Stage 1: Python dependencies builder
FROM python:3.11-slim as builder

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install system dependencies for building Python packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    libpq-dev \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

# Create virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy and install Python dependencies
COPY requirements/base.txt /tmp/base.txt
COPY requirements/production.txt /tmp/requirements.txt
RUN pip install --upgrade pip && \
    pip install -r /tmp/requirements.txt

# =====================================================================================
# Stage 2: Frontend builder
FROM node:20-alpine as frontend-builder

WORKDIR /app

# Copy package files
COPY purplex/client/package.json ./
COPY purplex/client/yarn.lock ./

# Install dependencies
RUN yarn install --frozen-lockfile

# Copy frontend source
COPY purplex/client/ ./

# Build frontend
RUN yarn build

# =====================================================================================
# Stage 3: Final production image
FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DJANGO_SETTINGS_MODULE=purplex.settings \
    PATH="/opt/venv/bin:$PATH"

# Install runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN groupadd -r purplex && useradd -r -g purplex purplex

# Create necessary directories with proper permissions
RUN mkdir -p /app /app/staticfiles /app/media /app/logs \
    && touch /app/logs/django.log /app/logs/errors.log /app/logs/access.log \
    && chown -R purplex:purplex /app \
    && chmod -R 755 /app/logs

WORKDIR /app

# Copy virtual environment from builder
COPY --from=builder /opt/venv /opt/venv

# Copy application code
COPY --chown=purplex:purplex . .

# Copy frontend build
COPY --from=frontend-builder --chown=purplex:purplex /app/dist /app/purplex/client/dist

# Switch to non-root user BEFORE collecting static files
USER purplex

# Collect static files as the purplex user (will use dev settings during build, that's ok)
RUN python manage.py collectstatic --noinput || true

# Health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:8000/health/ || exit 1

# Expose port
EXPOSE 8000

# Default command using gunicorn
CMD ["gunicorn", \
     "--config", "config/gunicorn/gunicorn.py", \
     "--bind", "0.0.0.0:8000", \
     "--workers", "4", \
     "--threads", "4", \
     "--worker-class", "sync", \
     "--worker-tmp-dir", "/dev/shm", \
     "--access-logfile", "-", \
     "--error-logfile", "-", \
     "purplex.wsgi:application"]