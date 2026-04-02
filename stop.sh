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

# Stop all purplex-related Docker containers (covers both start.sh and docker-compose names)
echo -e "${YELLOW}Stopping Docker containers...${NC}"
docker ps -a --filter "name=purplex" --format "{{.Names}}" 2>/dev/null | while read -r name; do
    docker stop "$name" 2>/dev/null && docker rm "$name" 2>/dev/null && echo -e "${GREEN}✓ $name stopped and removed${NC}"
done
echo -e "${GREEN}✓ Docker cleanup complete${NC}"

# Kill any remaining Python processes from the project
echo -e "${YELLOW}Cleaning up any remaining processes...${NC}"
pkill -f "python.*manage.py" 2>/dev/null || true
pkill -f "yarn.*vite" 2>/dev/null || true
pkill -f "npm.*vite" 2>/dev/null || true

echo ""
echo -e "${GREEN}═══════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}     All Purplex services have been stopped            ${NC}"
echo -e "${GREEN}═══════════════════════════════════════════════════════${NC}"
