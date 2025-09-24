#!/bin/bash

# Purplex Stop Script - Kills all running services

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${YELLOW}═══════════════════════════════════════════════════════${NC}"
echo -e "${YELLOW}     Stopping Purplex Development Environment          ${NC}"
echo -e "${YELLOW}═══════════════════════════════════════════════════════${NC}"
echo ""

# Function to kill processes on a port
kill_port() {
    local port=$1
    local name=$2
    
    pids=$(lsof -t -i:$port 2>/dev/null)
    if [ ! -z "$pids" ]; then
        echo -e "${YELLOW}Stopping $name (port $port)...${NC}"
        for pid in $pids; do
            kill -9 $pid 2>/dev/null || true
        done
        echo -e "${GREEN}✓ $name stopped${NC}"
    else
        echo -e "${GREEN}✓ $name not running${NC}"
    fi
}

# Kill Django server
kill_port 8000 "Django server"

# Kill Vue dev server
kill_port 5173 "Vue dev server"

# Kill Flower monitoring
kill_port 5555 "Flower monitoring"

# Kill all Celery processes
echo -e "${YELLOW}Stopping Celery workers...${NC}"
pkill -f "celery.*purplex" 2>/dev/null && echo -e "${GREEN}✓ Celery workers stopped${NC}" || echo -e "${GREEN}✓ Celery workers not running${NC}"

# Stop Redis container
echo -e "${YELLOW}Stopping Redis...${NC}"
docker stop purplex-redis 2>/dev/null && echo -e "${GREEN}✓ Redis stopped${NC}" || echo -e "${GREEN}✓ Redis not running${NC}"

# Stop PostgreSQL container (if running)
echo -e "${YELLOW}Stopping PostgreSQL...${NC}"
docker stop purplex-postgres 2>/dev/null && echo -e "${GREEN}✓ PostgreSQL stopped${NC}" || echo -e "${GREEN}✓ PostgreSQL not running${NC}"

# Kill any remaining Python processes from the project
echo -e "${YELLOW}Cleaning up any remaining processes...${NC}"
pkill -f "python.*manage.py" 2>/dev/null || true
pkill -f "yarn.*vite" 2>/dev/null || true
pkill -f "npm.*vite" 2>/dev/null || true

echo ""
echo -e "${GREEN}═══════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}     All Purplex services have been stopped            ${NC}"
echo -e "${GREEN}═══════════════════════════════════════════════════════${NC}"