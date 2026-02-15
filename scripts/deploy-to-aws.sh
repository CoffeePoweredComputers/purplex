#!/bin/bash
set -e

# AWS Deployment Script for Purplex
# This script deploys the Purplex application to an AWS EC2 instance

echo "================================================"
echo "Purplex AWS Deployment Script"
echo "================================================"

# Configuration
REMOTE_USER=${REMOTE_USER:-ubuntu}
REMOTE_HOST=${1:-}
DEPLOY_DIR=/home/$REMOTE_USER/purplex
AWS_REGION=${AWS_REGION:-us-east-1}
ECR_REGISTRY=${ECR_REGISTRY:-}
APP_NAME=purplex

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}[+]${NC} $1"
}

print_error() {
    echo -e "${RED}[!]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[*]${NC} $1"
}

# Check if remote host is provided
if [ -z "$REMOTE_HOST" ]; then
    print_error "Usage: $0 <ec2-public-ip-or-domain>"
    print_error "Example: $0 54.123.45.67"
    print_error "Example: $0 ec2-user@my-server.com"
    exit 1
}

# Check for required files
print_status "Checking required files..."
REQUIRED_FILES=(".env.production" "firebase-credentials.json" "docker-compose.production.yml")
for file in "${REQUIRED_FILES[@]}"; do
    if [ ! -f "$file" ]; then
        print_error "Required file not found: $file"
        exit 1
    fi
done

# Step 1: Build Docker images locally
print_status "Building Docker images..."
docker-compose -f docker-compose.production.yml build

# Step 2: Tag images for ECR (if using ECR)
if [ ! -z "$ECR_REGISTRY" ]; then
    print_status "Tagging images for ECR..."
    docker tag ${APP_NAME}_web:latest $ECR_REGISTRY/${APP_NAME}-web:latest
    docker tag ${APP_NAME}_celery:latest $ECR_REGISTRY/${APP_NAME}-celery:latest

    # Push to ECR
    print_status "Pushing images to ECR..."
    aws ecr get-login-password --region $AWS_REGION | docker login --username AWS --password-stdin $ECR_REGISTRY
    docker push $ECR_REGISTRY/${APP_NAME}-web:latest
    docker push $ECR_REGISTRY/${APP_NAME}-celery:latest
fi

# Step 3: Create deployment package
print_status "Creating deployment package..."
DEPLOY_PACKAGE="purplex-deploy-$(date +%Y%m%d-%H%M%S).tar.gz"
tar -czf $DEPLOY_PACKAGE \
    docker-compose.production.yml \
    .env.production \
    firebase-credentials.json \
    nginx/ \
    scripts/setup-ec2.sh \
    postgres-custom.conf 2>/dev/null || true

# Step 4: Copy deployment package to EC2
print_status "Copying deployment package to EC2..."
scp $DEPLOY_PACKAGE ${REMOTE_USER}@${REMOTE_HOST}:~/

# Step 5: Deploy on EC2
print_status "Deploying on EC2..."
ssh ${REMOTE_USER}@${REMOTE_HOST} << 'ENDSSH'
set -e

# Extract deployment package
echo "Extracting deployment package..."
tar -xzf purplex-deploy-*.tar.gz

# Create deployment directory
mkdir -p /home/ubuntu/purplex
cd /home/ubuntu/purplex

# Move files to deployment directory
mv ~/docker-compose.production.yml ./docker-compose.yml
mv ~/.env.production ./.env.production
mv ~/firebase-credentials.json ./
mv ~/nginx ./nginx || true
mv ~/postgres-custom.conf ./postgres-custom.conf || true

# Stop existing containers
echo "Stopping existing containers..."
docker-compose down || true

# Pull latest images (if using ECR)
if [ ! -z "$ECR_REGISTRY" ]; then
    echo "Pulling latest images from ECR..."
    aws ecr get-login-password --region $AWS_REGION | docker login --username AWS --password-stdin $ECR_REGISTRY
    docker-compose pull
fi

# Start services
echo "Starting services..."
docker-compose up -d

# Wait for services to be healthy
echo "Waiting for services to be healthy..."
sleep 30

# Run database migrations
echo "Running database migrations..."
docker-compose exec -T web python manage.py migrate --noinput

# Collect static files
echo "Collecting static files..."
docker-compose exec -T web python manage.py collectstatic --noinput

# Create superuser if needed
echo "Creating superuser (if not exists)..."
docker-compose exec -T web python manage.py shell << 'EOF'
from django.contrib.auth import get_user_model
User = get_user_model()
if not User.objects.filter(username='admin').exists():
    User.objects.create_superuser('admin', 'admin@example.com', 'changeme')
    print("Superuser created. Username: admin, Password: changeme")
    print("IMPORTANT: Change this password immediately!")
else:
    print("Superuser already exists")
EOF

# Show service status
echo "Service status:"
docker-compose ps

# Clean up
rm -f ~/purplex-deploy-*.tar.gz

echo "Deployment complete!"
ENDSSH

# Step 6: Clean up local files
print_status "Cleaning up local files..."
rm -f $DEPLOY_PACKAGE

# Step 7: Show deployment information
print_status "Deployment complete!"
echo ""
echo "================================================"
echo "Deployment Information:"
echo "================================================"
echo "Server: $REMOTE_HOST"
echo "Application URL: http://$REMOTE_HOST"
echo "Admin URL: http://$REMOTE_HOST/admin/"
echo ""
print_warning "Next Steps:"
echo "1. Update your DNS records to point to $REMOTE_HOST"
echo "2. Configure SSL certificates (run setup-ssl.sh)"
echo "3. Update ALLOWED_HOSTS in .env.production"
echo "4. Change the default admin password"
echo "5. Configure monitoring and backups"
echo ""
echo "To view logs:"
echo "  ssh ${REMOTE_USER}@${REMOTE_HOST} 'cd $DEPLOY_DIR && docker-compose logs -f'"
echo ""
echo "To restart services:"
echo "  ssh ${REMOTE_USER}@${REMOTE_HOST} 'cd $DEPLOY_DIR && docker-compose restart'"
echo "================================================"