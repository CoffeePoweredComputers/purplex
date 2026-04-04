# Simple Dockerfile for Purplex with Frontend Build
FROM python:3.11-slim-bookworm as backend

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
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir --force-reinstall 'wheel>=0.46.2' && \
    pip install --no-cache-dir -r requirements.txt

# Copy project
COPY . .

  # Build frontend
FROM node:20-alpine as frontend
WORKDIR /app
COPY purplex/client/package.json purplex/client/yarn.lock ./
RUN yarn install --frozen-lockfile
COPY purplex/client/ ./

# Firebase client config — passed from CI via --build-arg
ARG VITE_FIREBASE_API_KEY
ARG VITE_FIREBASE_AUTH_DOMAIN
ARG VITE_FIREBASE_PROJECT_ID
ARG VITE_FIREBASE_STORAGE_BUCKET
ARG VITE_FIREBASE_MESSAGING_SENDER_ID
ARG VITE_FIREBASE_APP_ID

# Write .env.production for Vite (the file is gitignored/dockerignored)
RUN printf '%s\n' \
    "VITE_PURPLEX_ENV=production" \
    "VITE_FIREBASE_MOCK=false" \
    "VITE_FIREBASE_API_KEY=${VITE_FIREBASE_API_KEY}" \
    "VITE_FIREBASE_AUTH_DOMAIN=${VITE_FIREBASE_AUTH_DOMAIN}" \
    "VITE_FIREBASE_PROJECT_ID=${VITE_FIREBASE_PROJECT_ID}" \
    "VITE_FIREBASE_STORAGE_BUCKET=${VITE_FIREBASE_STORAGE_BUCKET}" \
    "VITE_FIREBASE_MESSAGING_SENDER_ID=${VITE_FIREBASE_MESSAGING_SENDER_ID}" \
    "VITE_FIREBASE_APP_ID=${VITE_FIREBASE_APP_ID}" \
    "VITE_ENABLE_EIPL=true" \
    "VITE_ENABLE_HINTS=true" \
    "VITE_ENABLE_COURSES=true" \
    "VITE_DEBUG=false" \
    "VITE_LOG_LEVEL=error" \
    "VITE_APP_TITLE=Purplex" \
    > .env.production

# Production build uses relative URLs via nginx proxy
ENV VITE_PURPLEX_ENV=production
RUN yarn build

# Final image
FROM backend
COPY --from=frontend /app/dist /app/purplex/client/dist

# Create necessary directories
RUN mkdir -p staticfiles media logs /var/run/gunicorn

# Collect static files
# Note: Skipped during build - will run after deployment when database is available
# Run manually after deployment: docker-compose exec web python manage.py collectstatic --noinput
# RUN python manage.py collectstatic --noinput --clear 2>/dev/null || echo "⚠️  Static files collection skipped (run manually after deployment)"

# Expose port
EXPOSE 8000

# Run the application (command can be overridden in docker-compose)
CMD ["gunicorn", "purplex.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "4"]
