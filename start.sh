#!/bin/bash

# Purplex Complete Startup Script
# Starts all services: Redis, Celery, Django, and Vue

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}═══════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}     Starting Purplex Development Environment          ${NC}"
echo -e "${GREEN}═══════════════════════════════════════════════════════${NC}"
echo ""

# Load environment variables - prefer .env.development for local development
if [ -f .env.development ]; then
    echo -e "${YELLOW}Loading environment variables from .env.development file...${NC}"
    export $(cat .env.development | grep -v '^#' | xargs)
    export PURPLEX_ENV=development
    export DJANGO_SETTINGS_MODULE=purplex.settings
    echo -e "${GREEN}✓ Development environment variables loaded${NC}"
elif [ -f .env ]; then
    echo -e "${YELLOW}Loading environment variables from .env file...${NC}"
    export $(cat .env | grep -v '^#' | xargs)
    echo -e "${GREEN}✓ Environment variables loaded${NC}"
else
    echo -e "${YELLOW}No .env file found. Using system environment variables.${NC}"
    echo -e "${YELLOW}Copy .env.development to set up your development environment.${NC}"
fi
echo ""

# Function to cleanup on exit
cleanup() {
    echo ""
    echo -e "${YELLOW}Shutting down services...${NC}"
    
    # Kill Django if running
    if [ ! -z "$DJANGO_PID" ]; then
        kill -TERM $DJANGO_PID 2>/dev/null || true
        sleep 1
        kill -9 $DJANGO_PID 2>/dev/null || true
    fi
    # Also kill any Django on port 8000
    lsof -t -i:8000 2>/dev/null | xargs -r kill -9 2>/dev/null || true
    
    # Kill Vue dev server
    if [ ! -z "$VUE_PID" ]; then
        kill -TERM $VUE_PID 2>/dev/null || true
        sleep 1
        kill -9 $VUE_PID 2>/dev/null || true
    fi
    # Also kill any process on port 5173
    lsof -t -i:5173 2>/dev/null | xargs -r kill -9 2>/dev/null || true
    
    # Kill Celery worker
    if [ ! -z "$WORKER_PID" ]; then
        kill -TERM $WORKER_PID 2>/dev/null || true
        sleep 1
        kill -9 $WORKER_PID 2>/dev/null || true
    fi
    
    # Kill Flower
    if [ ! -z "$FLOWER_PID" ]; then
        kill -TERM $FLOWER_PID 2>/dev/null || true
        sleep 1
        kill -9 $FLOWER_PID 2>/dev/null || true
    fi
    lsof -t -i:5555 2>/dev/null | xargs -r kill -9 2>/dev/null || true
    
    # Kill all Celery processes
    pkill -f "celery.*purplex" 2>/dev/null || true
    
    # Kill any remaining Python manage.py processes
    pkill -f "python.*manage.py" 2>/dev/null || true
    
    # Stop Redis
    docker stop purplex-redis 2>/dev/null || true
    
    echo -e "${GREEN}All services stopped.${NC}"
    exit 0
}

# Variable to track if we're already cleaning up
CLEANING_UP=0

# Enhanced cleanup with force quit on double Ctrl+C
handle_interrupt() {
    if [ $CLEANING_UP -eq 1 ]; then
        echo ""
        echo -e "${RED}Force quitting...${NC}"
        # Force kill everything immediately
        pkill -9 -f "celery.*purplex" 2>/dev/null || true
        pkill -9 -f "python.*manage.py" 2>/dev/null || true
        pkill -9 -f "yarn.*vite" 2>/dev/null || true
        lsof -t -i:8000 2>/dev/null | xargs -r kill -9 2>/dev/null || true
        lsof -t -i:5173 2>/dev/null | xargs -r kill -9 2>/dev/null || true
        lsof -t -i:5555 2>/dev/null | xargs -r kill -9 2>/dev/null || true
        docker stop purplex-redis 2>/dev/null || true
        exit 1
    fi
    
    CLEANING_UP=1
    echo ""
    echo -e "${YELLOW}Gracefully shutting down... (Press Ctrl+C again to force quit)${NC}"
    cleanup
}

# Set trap for cleanup on script exit
trap handle_interrupt INT
trap cleanup EXIT TERM

# 1. Check prerequisites
echo -e "${YELLOW}Checking prerequisites...${NC}"

if ! command -v docker &> /dev/null; then
    echo -e "${RED}✗ Docker is not installed. Please install Docker first.${NC}"
    exit 1
fi

if ! command -v node &> /dev/null; then
    echo -e "${RED}✗ Node.js is not installed. Please install Node.js first.${NC}"
    exit 1
fi

if [ ! -d "env" ]; then
    echo -e "${RED}✗ Virtual environment not found. Please create it first:${NC}"
    echo "  python -m venv env"
    echo "  source env/bin/activate"
    echo "  pip install -r requirements.txt"
    exit 1
fi

echo -e "${GREEN}✓ Prerequisites check passed${NC}"

# 2. Start PostgreSQL for development
echo -e "${YELLOW}Starting PostgreSQL for development...${NC}"
# Check if PostgreSQL is running
if docker ps | grep -q purplex-postgres-dev; then
    echo -e "${GREEN}✓ PostgreSQL is already running${NC}"
else
    # Stop and remove any old container
    docker stop purplex-postgres-dev 2>/dev/null || true
    docker rm purplex-postgres-dev 2>/dev/null || true
    
    echo -e "${YELLOW}Starting fresh PostgreSQL container...${NC}"
    docker run -d \
      --name purplex-postgres-dev \
      -e POSTGRES_DB=purplex_dev \
      -e POSTGRES_USER=purplex_user \
      -e POSTGRES_PASSWORD=devpass \
      -p 5432:5432 \
      -v purplex_postgres_dev_data:/var/lib/postgresql/data \
      postgres:15-alpine > /dev/null 2>&1
    sleep 5
    echo -e "${GREEN}✓ PostgreSQL started for development${NC}"
fi

# 3. Start Redis
echo -e "${YELLOW}Starting Redis...${NC}"
if docker ps | grep -q purplex-redis; then
    echo -e "${GREEN}✓ Redis is already running${NC}"
else
    docker rm -f purplex-redis 2>/dev/null || true
    docker run -d --name purplex-redis -p 6379:6379 --network host redis:7-alpine > /dev/null 2>&1
    sleep 2
fi

# Test Redis
if docker exec purplex-redis redis-cli ping > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Redis is ready${NC}"
else
    echo -e "${RED}✗ Redis failed to start${NC}"
    exit 1
fi

# 4. Setup Python environment and migrations
echo -e "${YELLOW}Setting up Django...${NC}"
source env/bin/activate

# Run migrations
python manage.py migrate --noinput > /dev/null 2>&1
echo -e "${GREEN}✓ Database migrations complete${NC}"

# Create logs directory if it doesn't exist
mkdir -p logs

# 5. Kill any existing Celery processes
pkill -f "celery.*purplex" 2>/dev/null || true
sleep 1

# 6. Start Celery Worker with increased concurrency
echo -e "${YELLOW}Starting Celery Worker...${NC}"
# Ensure environment variables are passed to Celery
export OPENAI_API_KEY="${OPENAI_API_KEY}"
# Using new clean Celery configuration
# Pass DJANGO_SETTINGS_MODULE explicitly to ensure Celery uses the right settings
nohup env OPENAI_API_KEY="${OPENAI_API_KEY}" DJANGO_SETTINGS_MODULE="${DJANGO_SETTINGS_MODULE:-purplex.settings}" celery -A purplex.celery_simple worker \
    -l info \
    --concurrency=4 \
    --pool=prefork \
    > logs/celery_worker.log 2>&1 &
WORKER_PID=$!
sleep 2
if ps -p $WORKER_PID > /dev/null; then
    echo -e "${GREEN}✓ Celery Worker started (PID: $WORKER_PID)${NC}"
else
    echo -e "${RED}✗ Celery Worker failed to start${NC}"
    exit 1
fi

# 7. Start Flower (optional monitoring)
echo -e "${YELLOW}Starting Flower (monitoring)...${NC}"
nohup celery -A purplex.celery_simple flower \
    --port=5555 \
    --broker=redis://localhost:6379/0 \
    > logs/flower.log 2>&1 &
FLOWER_PID=$!
sleep 2
if ps -p $FLOWER_PID > /dev/null; then
    echo -e "${GREEN}✓ Flower started (PID: $FLOWER_PID)${NC}"
else
    echo -e "${YELLOW}⚠ Flower failed to start (non-critical)${NC}"
fi

# 8. Start Django development server
echo -e "${YELLOW}Starting Django server...${NC}"
# Kill any existing Django process on port 8000
lsof -i :8000 | grep LISTEN | awk '{print $2}' | xargs kill -9 2>/dev/null || true
sleep 1
nohup python manage.py runserver > logs/django.log 2>&1 &
DJANGO_PID=$!
sleep 3
if ps -p $DJANGO_PID > /dev/null; then
    echo -e "${GREEN}✓ Django server started (PID: $DJANGO_PID)${NC}"
else
    echo -e "${RED}✗ Django server failed to start${NC}"
    echo "Check logs/django.log for details"
    exit 1
fi

# 10. Install npm dependencies if needed and start Vue
echo -e "${YELLOW}Starting Vue.js frontend...${NC}"
cd purplex/client

# Install dependencies if node_modules doesn't exist
if [ ! -d "node_modules" ]; then
    echo -e "${YELLOW}Installing npm dependencies...${NC}"
    npm install > /dev/null 2>&1
fi

# Start Vue dev server (using vite directly to avoid duplicate Django)
nohup yarn vite --mode development > ../../logs/vue.log 2>&1 &
VUE_PID=$!
cd ../..
sleep 5

# Check if Vue started successfully
if ps -p $VUE_PID > /dev/null; then
    echo -e "${GREEN}✓ Vue dev server started (PID: $VUE_PID)${NC}"
else
    echo -e "${RED}✗ Vue dev server failed to start${NC}"
    echo "Check logs/vue.log for details"
    exit 1
fi

# 11. Show status
echo ""
echo -e "${GREEN}═══════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}     All Services Started Successfully! 🚀             ${NC}"
echo -e "${GREEN}═══════════════════════════════════════════════════════${NC}"
echo ""
echo -e "${GREEN}Access Points:${NC}"
echo -e "  • Frontend:        ${GREEN}http://localhost:5173${NC}"
echo -e "  • Django API:      ${GREEN}http://localhost:8000${NC}"
echo -e "  • Django Admin:    ${GREEN}http://localhost:8000/admin${NC}"
echo -e "  • Flower Monitor:  ${GREEN}http://localhost:5555${NC}"
echo ""
echo -e "${GREEN}Service PIDs:${NC}"
echo -e "  • Celery Worker:   $WORKER_PID"
echo -e "  • Flower:          $FLOWER_PID"
echo -e "  • Django:          $DJANGO_PID"
echo -e "  • Vue:             $VUE_PID"
echo ""
echo -e "${GREEN}Logs:${NC}"
echo -e "  • tail -f logs/celery_worker.log"
echo -e "  • tail -f logs/django.log"
echo -e "  • tail -f logs/vue.log"
echo ""
echo -e "${YELLOW}Press Ctrl+C to stop all services (Press twice to force quit)${NC}"
echo ""

# Keep script running and show combined logs
echo -e "${GREEN}Showing combined logs (Ctrl+C to stop all services):${NC}"
echo -e "${GREEN}═══════════════════════════════════════════════════════${NC}"

# Function to display logs with prefixes
show_logs() {
    # Kill any existing tail processes first
    pkill -f "tail -f logs/" 2>/dev/null || true
    
    # Start fresh tail processes
    tail -f logs/django.log 2>/dev/null | sed 's/^/[Django] /' &
    TAIL_DJANGO=$!
    tail -f logs/celery_worker.log 2>/dev/null | sed 's/^/[Celery] /' &
    TAIL_CELERY=$!
    tail -f logs/vue.log 2>/dev/null | sed 's/^/[Vue] /' &
    TAIL_VUE=$!
    
    # Wait for any of them to exit (which happens on Ctrl+C)
    wait $TAIL_DJANGO $TAIL_CELERY $TAIL_VUE
}

# Show logs until interrupted
show_logs