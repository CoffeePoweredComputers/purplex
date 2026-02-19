#!/bin/bash
# Pre-deployment health validation
# Verifies system is ready for deployment

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo "=========================================="
echo "Pre-Deployment Health Check"
echo "=========================================="

# Check if services are running
echo -n "Checking Docker services... "
if docker compose ps | grep -q "Up"; then
    echo -e "${GREEN}OK${NC}"
else
    echo -e "${RED}FAILED${NC}"
    echo "Services are not running. Start services first."
    exit 1
fi

# Check database connectivity
echo -n "Checking database... "
if docker compose exec -T postgres pg_isready -U ${POSTGRES_USER:-purplex_user} >/dev/null 2>&1; then
    echo -e "${GREEN}OK${NC}"
else
    echo -e "${RED}FAILED${NC}"
    exit 1
fi

# Check Redis connectivity
echo -n "Checking Redis... "
if docker compose exec -T redis redis-cli ping >/dev/null 2>&1; then
    echo -e "${GREEN}OK${NC}"
else
    echo -e "${RED}FAILED${NC}"
    exit 1
fi

# Check web service health
echo -n "Checking web service... "
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/api/health/ 2>/dev/null || echo "000")
if [ "$HTTP_CODE" = "200" ]; then
    echo -e "${GREEN}OK${NC}"
else
    echo -e "${RED}FAILED (HTTP $HTTP_CODE)${NC}"
    exit 1
fi

# Check Celery workers
echo -n "Checking Celery workers... "
if docker compose exec -T celery celery -A purplex.celery_simple inspect ping >/dev/null 2>&1; then
    echo -e "${GREEN}OK${NC}"
else
    echo -e "${RED}FAILED${NC}"
    exit 1
fi

# Check disk space
echo -n "Checking disk space... "
DISK_USAGE=$(df -h / | awk 'NR==2 {print $5}' | sed 's/%//')
if [ "$DISK_USAGE" -lt 80 ]; then
    echo -e "${GREEN}OK (${DISK_USAGE}% used)${NC}"
else
    echo -e "${YELLOW}WARNING (${DISK_USAGE}% used)${NC}"
fi

# Check memory
echo -n "Checking memory... "
MEM_USAGE=$(free | grep Mem | awk '{printf("%.0f", $3/$2 * 100)}')
if [ "$MEM_USAGE" -lt 90 ]; then
    echo -e "${GREEN}OK (${MEM_USAGE}% used)${NC}"
else
    echo -e "${YELLOW}WARNING (${MEM_USAGE}% used)${NC}"
fi

echo ""
echo -e "${GREEN}All pre-deployment checks passed!${NC}"
echo "System is ready for deployment."
exit 0