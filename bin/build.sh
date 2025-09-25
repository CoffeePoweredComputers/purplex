#!/bin/bash
# =====================================================================================
# PURPLEX BUILD SCRIPT
# =====================================================================================
# Builds the application for production deployment
# =====================================================================================

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}           Purplex Production Build Script              ${NC}"
echo -e "${GREEN}════════════════════════════════════════════════════════${NC}"

# Check if we're in the project root
if [ ! -f "manage.py" ]; then
    echo -e "${RED}Error: Not in project root directory${NC}"
    exit 1
fi

# Load version
VERSION=$(cat VERSION)
echo -e "${YELLOW}Building version: $VERSION${NC}"

# Step 1: Build frontend
echo -e "\n${YELLOW}Step 1: Building frontend...${NC}"
cd purplex/client
yarn install --frozen-lockfile
yarn build
cd ../..
echo -e "${GREEN}✓ Frontend built successfully${NC}"

# Step 2: Collect static files
echo -e "\n${YELLOW}Step 2: Collecting static files...${NC}"
python manage.py collectstatic --noinput
echo -e "${GREEN}✓ Static files collected${NC}"

# Step 3: Run tests
echo -e "\n${YELLOW}Step 3: Running tests...${NC}"
pytest -q
echo -e "${GREEN}✓ All tests passed${NC}"

# Step 4: Build Docker images
echo -e "\n${YELLOW}Step 4: Building Docker images...${NC}"
docker build -t purplex-app:$VERSION -t purplex-app:latest .
docker build -f Dockerfile.celery -t purplex-celery:$VERSION -t purplex-celery:latest .
echo -e "${GREEN}✓ Docker images built${NC}"

# Step 5: Generate build info
echo -e "\n${YELLOW}Step 5: Generating build info...${NC}"
cat > build-info.json <<EOF
{
  "version": "$VERSION",
  "build_date": "$(date -u +"%Y-%m-%dT%H:%M:%SZ")",
  "git_commit": "$(git rev-parse HEAD)",
  "git_branch": "$(git rev-parse --abbrev-ref HEAD)",
  "builder": "$(whoami)@$(hostname)"
}
EOF
echo -e "${GREEN}✓ Build info generated${NC}"

echo -e "\n${GREEN}════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}              Build completed successfully!             ${NC}"
echo -e "${GREEN}════════════════════════════════════════════════════════${NC}"
echo -e "\nImages built:"
echo -e "  • purplex-app:$VERSION"
echo -e "  • purplex-celery:$VERSION"
echo -e "\nNext steps:"
echo -e "  1. Push images to registry: ${YELLOW}make docker-push${NC}"
echo -e "  2. Deploy to production: ${YELLOW}make prod-deploy${NC}"