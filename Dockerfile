# Simple Dockerfile for Purplex with Frontend Build
FROM python:3.11-slim as backend

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy project
COPY . .

  # Build frontend
FROM node:20-alpine as frontend
WORKDIR /app
COPY purplex/client/package.json purplex/client/yarn.lock ./
RUN yarn install --frozen-lockfile
COPY purplex/client/ ./
# Production build uses relative URLs via nginx proxy
ENV VITE_PURPLEX_ENV=production
RUN yarn build

# Final image
FROM backend
COPY --from=frontend /app/dist /app/purplex/client/dist

# Create necessary directories
RUN mkdir -p staticfiles media logs

# Collect static files
# Note: This may fail during build if Django needs database connection
# In production, run collectstatic after deployment with: python manage.py collectstatic --noinput
RUN python manage.py collectstatic --noinput --clear 2>/dev/null || echo "⚠️  Static files collection skipped (run manually after deployment)"

# Expose port
EXPOSE 8000

# Run the application (command can be overridden in docker-compose)
CMD ["gunicorn", "purplex.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "4"]