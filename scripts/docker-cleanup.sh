#!/bin/bash
# Docker Container Cleanup Script for Purplex
# Removes orphaned sandbox containers to prevent disk space accumulation
#
# Usage:
#   ./scripts/docker-cleanup.sh           # Interactive mode (default)
#   ./scripts/docker-cleanup.sh --force   # Non-interactive mode
#
# Can be run as a cron job:
#   0 * * * * /path/to/purplex/scripts/docker-cleanup.sh --force >> /var/log/purplex-cleanup.log 2>&1

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Parse arguments
FORCE=false
if [[ "${1:-}" == "--force" ]]; then
    FORCE=true
fi

echo "🧹 Purplex Docker Cleanup Script"
echo "=================================="

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo -e "${RED}❌ Error: Docker is not running${NC}"
    exit 1
fi

# Count containers to remove
EXITED_COUNT=$(docker ps -a --filter "status=exited" --filter "label=purplex-pool=true" -q | wc -l)
CREATED_COUNT=$(docker ps -a --filter "status=created" --filter "ancestor=purplex/python-sandbox:latest" -q | wc -l)
TOTAL_COUNT=$((EXITED_COUNT + CREATED_COUNT))

echo ""
echo "📊 Containers found:"
echo "  - Exited pool containers: ${EXITED_COUNT}"
echo "  - Created (never started): ${CREATED_COUNT}"
echo "  - Total to remove: ${TOTAL_COUNT}"
echo ""

if [ "$TOTAL_COUNT" -eq 0 ]; then
    echo -e "${GREEN}✅ No containers to clean up${NC}"
    exit 0
fi

# Confirm removal unless --force
if [ "$FORCE" = false ]; then
    read -p "Remove ${TOTAL_COUNT} containers? [y/N] " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Cleanup cancelled"
        exit 0
    fi
fi

# Remove exited pool containers
if [ "$EXITED_COUNT" -gt 0 ]; then
    echo -e "${YELLOW}🗑️  Removing ${EXITED_COUNT} exited pool containers...${NC}"
    docker ps -a --filter "status=exited" --filter "label=purplex-pool=true" -q | xargs -r docker rm
fi

# Remove created but never started containers
if [ "$CREATED_COUNT" -gt 0 ]; then
    echo -e "${YELLOW}🗑️  Removing ${CREATED_COUNT} created containers...${NC}"
    docker ps -a --filter "status=created" --filter "ancestor=purplex/python-sandbox:latest" -q | xargs -r docker rm
fi

# Final count
REMAINING=$(docker ps -a --filter "ancestor=purplex/python-sandbox:latest" --filter "status=exited" -q | wc -l)

echo ""
echo -e "${GREEN}✅ Cleanup complete!${NC}"
echo "  - Removed: ${TOTAL_COUNT} containers"
echo "  - Remaining exited: ${REMAINING}"
echo ""

# Disk space saved (approximate)
if command -v docker system df &> /dev/null; then
    echo "💾 Current Docker disk usage:"
    docker system df
fi
