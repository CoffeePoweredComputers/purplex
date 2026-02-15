#!/bin/bash

# Setup AWS Secrets Manager for Purplex production credentials
# Run this once to create the secret in AWS

set -e

# Configuration
SECRET_NAME="${1:-purplex/production/credentials}"
REGION="${2:-us-east-2}"

echo "========================================"
echo "AWS Secrets Manager Setup for Purplex"
echo "========================================"
echo ""
echo "This script will create a new secret in AWS Secrets Manager"
echo "Secret Name: $SECRET_NAME"
echo "Region: $REGION"
echo ""

# Check AWS CLI
if ! command -v aws &> /dev/null; then
    echo "ERROR: AWS CLI is not installed"
    exit 1
fi

# Generate strong passwords
echo "Generating strong random passwords..."
POSTGRES_PASSWORD=$(openssl rand -base64 32 | tr -d "=+/" | cut -c1-32)
REDIS_PASSWORD=$(openssl rand -base64 32 | tr -d "=+/" | cut -c1-32)
DJANGO_SECRET_KEY=$(python3 -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())' 2>/dev/null || openssl rand -base64 64 | tr -d "=+/")

# Prompt for OpenAI API Key
echo ""
read -p "Enter your OpenAI API Key: " OPENAI_API_KEY
if [ -z "$OPENAI_API_KEY" ]; then
    echo "ERROR: OpenAI API Key is required"
    exit 1
fi

# Create JSON secret
SECRET_JSON=$(cat <<EOF
{
  "POSTGRES_DB": "purplex_prod",
  "POSTGRES_USER": "purplex_user",
  "POSTGRES_PASSWORD": "$POSTGRES_PASSWORD",
  "REDIS_PASSWORD": "$REDIS_PASSWORD",
  "DJANGO_SECRET_KEY": "$DJANGO_SECRET_KEY",
  "OPENAI_API_KEY": "$OPENAI_API_KEY"
}
EOF
)

echo ""
echo "Creating secret in AWS Secrets Manager..."

# Try to create the secret
aws secretsmanager create-secret \
    --name "$SECRET_NAME" \
    --description "Purplex production credentials" \
    --secret-string "$SECRET_JSON" \
    --region "$REGION" 2>&1

if [ $? -eq 0 ]; then
    echo "✓ Secret created successfully!"
else
    echo "Secret already exists. Updating instead..."
    aws secretsmanager put-secret-value \
        --secret-id "$SECRET_NAME" \
        --secret-string "$SECRET_JSON" \
        --region "$REGION"

    if [ $? -eq 0 ]; then
        echo "✓ Secret updated successfully!"
    else
        echo "ERROR: Failed to create or update secret"
        exit 1
    fi
fi

echo ""
echo "========================================"
echo "✓ Setup Complete!"
echo "========================================"
echo ""
echo "Secret Name: $SECRET_NAME"
echo "Region: $REGION"
echo ""
echo "Generated credentials:"
echo "  - PostgreSQL Password: [32 characters]"
echo "  - Redis Password: [32 characters]"
echo "  - Django Secret Key: [generated]"
echo "  - OpenAI API Key: [provided]"
echo ""
echo "Next steps:"
echo "1. Grant EC2 instance IAM role access to this secret"
echo "2. Run scripts/load-aws-secrets.sh on your EC2 instance"
echo "3. Start your application with docker-compose up -d"
echo ""