#!/bin/bash
# =====================================================================================
# PURPLEX DEPLOYMENT SCRIPT
# =====================================================================================
# Orchestrates deployment to production environment
# =====================================================================================

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}           Purplex Production Deployment                ${NC}"
echo -e "${BLUE}════════════════════════════════════════════════════════${NC}"

# Configuration
ENVIRONMENT=${1:-production}
VERSION=$(cat VERSION)

# Validate environment
if [[ ! "$ENVIRONMENT" =~ ^(staging|production)$ ]]; then
    echo -e "${RED}Error: Invalid environment. Use 'staging' or 'production'${NC}"
    exit 1
fi

echo -e "${YELLOW}Deploying version $VERSION to $ENVIRONMENT${NC}"

# Step 1: Pre-deployment checks
echo -e "\n${YELLOW}Step 1: Running pre-deployment checks...${NC}"

# Check if images exist
if ! docker image inspect purplex-app:$VERSION >/dev/null 2>&1; then
    echo -e "${RED}Error: Docker image purplex-app:$VERSION not found${NC}"
    echo -e "${YELLOW}Run 'make build' first${NC}"
    exit 1
fi

# Check environment file
if [ ! -f ".env.$ENVIRONMENT" ]; then
    echo -e "${RED}Error: .env.$ENVIRONMENT file not found${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Pre-deployment checks passed${NC}"

# Step 2: Database backup
echo -e "\n${YELLOW}Step 2: Creating database backup...${NC}"
BACKUP_FILE="backup_$(date +%Y%m%d_%H%M%S)_pre_$VERSION.sql"
pg_dump -h $DB_HOST -U $DB_USER -d $DB_NAME > backups/$BACKUP_FILE
echo -e "${GREEN}✓ Database backed up to $BACKUP_FILE${NC}"

# Step 3: Run migrations
echo -e "\n${YELLOW}Step 3: Running database migrations...${NC}"
docker run --rm \
    --env-file .env.$ENVIRONMENT \
    purplex-app:$VERSION \
    python manage.py migrate --noinput
echo -e "${GREEN}✓ Migrations completed${NC}"

# Step 4: Deploy new version
echo -e "\n${YELLOW}Step 4: Deploying new version...${NC}"

if [ "$ENVIRONMENT" == "production" ]; then
    # Production deployment (using docker-compose)
    docker-compose -f config/docker/production.yml down
    docker-compose -f config/docker/production.yml up -d

    # Wait for services to be healthy
    echo -e "${YELLOW}Waiting for services to be healthy...${NC}"
    sleep 10

    # Health check
    if curl -f http://localhost:8000/health/ >/dev/null 2>&1; then
        echo -e "${GREEN}✓ Application is healthy${NC}"
    else
        echo -e "${RED}Error: Health check failed${NC}"
        echo -e "${YELLOW}Rolling back...${NC}"
        docker-compose -f config/docker/production.yml down
        docker-compose -f config/docker/production.yml up -d
        exit 1
    fi
else
    # Staging deployment
    docker-compose -f config/docker/staging.yml down
    docker-compose -f config/docker/staging.yml up -d
fi

echo -e "${GREEN}✓ New version deployed${NC}"

# Step 5: Clear caches
echo -e "\n${YELLOW}Step 5: Clearing caches...${NC}"
docker exec purplex-app python manage.py clear_cache
echo -e "${GREEN}✓ Caches cleared${NC}"

# Step 6: Smoke tests
echo -e "\n${YELLOW}Step 6: Running smoke tests...${NC}"
python monitoring/performance_test.py --smoke
echo -e "${GREEN}✓ Smoke tests passed${NC}"

# Step 7: Update version in monitoring
echo -e "\n${YELLOW}Step 7: Updating monitoring...${NC}"
curl -X POST http://monitoring.purplex.com/api/deployment \
    -H "Content-Type: application/json" \
    -d "{\"version\":\"$VERSION\",\"environment\":\"$ENVIRONMENT\",\"timestamp\":\"$(date -u +"%Y-%m-%dT%H:%M:%SZ")\"}"
echo -e "${GREEN}✓ Monitoring updated${NC}"

echo -e "\n${GREEN}════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}         Deployment completed successfully!            ${NC}"
echo -e "${GREEN}════════════════════════════════════════════════════════${NC}"
echo -e "\nDeployment summary:"
echo -e "  • Version: $VERSION"
echo -e "  • Environment: $ENVIRONMENT"
echo -e "  • Backup: $BACKUP_FILE"
echo -e "\nPost-deployment tasks:"
echo -e "  1. Monitor logs: ${YELLOW}docker-compose logs -f${NC}"
echo -e "  2. Check metrics: ${YELLOW}http://grafana.purplex.com${NC}"
echo -e "  3. Run full test suite: ${YELLOW}make test${NC}"