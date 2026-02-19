#!/bin/bash

# Load secrets from AWS Secrets Manager into environment variables
# This script is run on EC2 instances before starting Docker Compose

set -e

# Configuration
SECRET_NAME="${AWS_SECRET_NAME:-purplex/production/credentials}"
REGION="${AWS_REGION:-us-east-2}"

echo "Loading secrets from AWS Secrets Manager..."
echo "Secret Name: $SECRET_NAME"
echo "Region: $REGION"

# Check if AWS CLI is installed
if ! command -v aws &> /dev/null; then
    echo "ERROR: AWS CLI is not installed"
    echo "Install with: sudo apt-get install awscli"
    exit 1
fi

# Check if jq is installed (for JSON parsing)
if ! command -v jq &> /dev/null; then
    echo "ERROR: jq is not installed"
    echo "Install with: sudo apt-get install jq"
    exit 1
fi

# Retrieve secret from AWS Secrets Manager
echo "Retrieving secret from AWS Secrets Manager..."
SECRET_JSON=$(aws secretsmanager get-secret-value \
    --secret-id "$SECRET_NAME" \
    --region "$REGION" \
    --query SecretString \
    --output text 2>&1)

if [ $? -ne 0 ]; then
    echo "ERROR: Failed to retrieve secret from AWS Secrets Manager"
    echo "$SECRET_JSON"
    exit 1
fi

# Parse JSON and export as environment variables
echo "Parsing secrets and exporting to environment..."

# Export each key-value pair from the JSON secret
export POSTGRES_DB=$(echo "$SECRET_JSON" | jq -r '.POSTGRES_DB // empty')
export POSTGRES_USER=$(echo "$SECRET_JSON" | jq -r '.POSTGRES_USER // empty')
export POSTGRES_PASSWORD=$(echo "$SECRET_JSON" | jq -r '.POSTGRES_PASSWORD // empty')
export REDIS_PASSWORD=$(echo "$SECRET_JSON" | jq -r '.REDIS_PASSWORD // empty')
export DJANGO_SECRET_KEY=$(echo "$SECRET_JSON" | jq -r '.DJANGO_SECRET_KEY // empty')
export OPENAI_API_KEY=$(echo "$SECRET_JSON" | jq -r '.OPENAI_API_KEY // empty')

# Validate required secrets
MISSING_SECRETS=()
[ -z "$POSTGRES_DB" ] && MISSING_SECRETS+=("POSTGRES_DB")
[ -z "$POSTGRES_USER" ] && MISSING_SECRETS+=("POSTGRES_USER")
[ -z "$POSTGRES_PASSWORD" ] && MISSING_SECRETS+=("POSTGRES_PASSWORD")
[ -z "$DJANGO_SECRET_KEY" ] && MISSING_SECRETS+=("DJANGO_SECRET_KEY")
[ -z "$OPENAI_API_KEY" ] && MISSING_SECRETS+=("OPENAI_API_KEY")

if [ ${#MISSING_SECRETS[@]} -ne 0 ]; then
    echo "ERROR: Missing required secrets: ${MISSING_SECRETS[*]}"
    exit 1
fi

# Write to .env file for Docker Compose
echo "Writing secrets to .env file..."
cat > .env << EOF
# Auto-generated from AWS Secrets Manager
# DO NOT EDIT MANUALLY - Changes will be overwritten
# Generated at: $(date -u +"%Y-%m-%d %H:%M:%S UTC")

# Environment Type
PURPLEX_ENV=production

# Database Credentials (from AWS Secrets Manager)
POSTGRES_DB=$POSTGRES_DB
POSTGRES_USER=$POSTGRES_USER
POSTGRES_PASSWORD=$POSTGRES_PASSWORD

# Redis Credentials (from AWS Secrets Manager)
REDIS_PASSWORD=$REDIS_PASSWORD

# Django Configuration (from AWS Secrets Manager)
DJANGO_SECRET_KEY=$DJANGO_SECRET_KEY
DJANGO_DEBUG=False
DJANGO_ALLOWED_HOSTS=${DJANGO_ALLOWED_HOSTS:-localhost,127.0.0.1}

# OpenAI Configuration (from AWS Secrets Manager)
OPENAI_API_KEY=$OPENAI_API_KEY
GPT_MODEL=${GPT_MODEL:-gpt-4o-mini}

# Firebase Configuration
FIREBASE_CREDENTIALS_PATH=/app/firebase-credentials.json

# SSL/Security Settings
SECURE_SSL_REDIRECT=${SECURE_SSL_REDIRECT:-False}
SESSION_COOKIE_SECURE=${SESSION_COOKIE_SECURE:-False}
CSRF_COOKIE_SECURE=${CSRF_COOKIE_SECURE:-False}
CSRF_TRUSTED_ORIGINS=${CSRF_TRUSTED_ORIGINS:-}

# Performance Settings
GUNICORN_WORKERS=${GUNICORN_WORKERS:-4}
GUNICORN_THREADS=${GUNICORN_THREADS:-2}
GUNICORN_TIMEOUT=${GUNICORN_TIMEOUT:-120}
CELERY_WORKERS=${CELERY_WORKERS:-4}

# Code Execution Settings
CODE_EXEC_MAX_TIME=${CODE_EXEC_MAX_TIME:-10}
CODE_EXEC_MAX_MEMORY=${CODE_EXEC_MAX_MEMORY:-512m}

# Feature Flags
ENABLE_EIPL=${ENABLE_EIPL:-True}
ENABLE_HINTS=${ENABLE_HINTS:-True}
ENABLE_COURSES=${ENABLE_COURSES:-True}

# URLs (Auto-constructed)
DATABASE_URL=postgresql://$POSTGRES_USER:$POSTGRES_PASSWORD@postgres:5432/$POSTGRES_DB
REDIS_URL=redis://:$REDIS_PASSWORD@redis:6379/0
REDIS_HOST=redis
REDIS_PORT=6379
CELERY_BROKER_URL=redis://:$REDIS_PASSWORD@redis:6379/1
CELERY_RESULT_BACKEND=redis://:$REDIS_PASSWORD@redis:6379/2
EOF

echo "✓ Secrets loaded successfully from AWS Secrets Manager"
echo "✓ .env file created with production credentials"
echo ""
echo "You can now run: docker-compose up -d"