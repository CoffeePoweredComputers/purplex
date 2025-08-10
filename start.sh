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

# Load environment variables from .env file if it exists
if [ -f .env ]; then
    echo -e "${YELLOW}Loading environment variables from .env file...${NC}"
    export $(cat .env | grep -v '^#' | xargs)
    echo -e "${GREEN}✓ Environment variables loaded${NC}"
else
    echo -e "${YELLOW}No .env file found. Using system environment variables.${NC}"
    echo -e "${YELLOW}Copy .env.example to .env and add your API keys.${NC}"
fi
echo ""

# Function to cleanup on exit
cleanup() {
    echo ""
    echo -e "${YELLOW}Shutting down services...${NC}"
    
    # Kill Django if running
    if [ ! -z "$DJANGO_PID" ]; then
        kill $DJANGO_PID 2>/dev/null || true
    fi
    # Also kill any Django on port 8000
    lsof -i :8000 | grep LISTEN | awk '{print $2}' | xargs kill -9 2>/dev/null || true
    
    # Kill Vue dev server
    if [ ! -z "$VUE_PID" ]; then
        kill $VUE_PID 2>/dev/null || true
    fi
    # Also kill any process on port 5173
    lsof -i :5173 | grep LISTEN | awk '{print $2}' | xargs kill -9 2>/dev/null || true
    
    # Kill Celery processes
    pkill -f "celery.*purplex" 2>/dev/null || true
    
    # Stop Redis
    docker stop purplex-redis 2>/dev/null || true
    
    echo -e "${GREEN}All services stopped.${NC}"
    exit 0
}

# Set trap for cleanup on script exit
trap cleanup EXIT INT TERM

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

# 2. Start Redis
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

# 3. Setup Python environment and migrations
echo -e "${YELLOW}Setting up Django...${NC}"
source env/bin/activate

# Run migrations
python manage.py migrate --noinput > /dev/null 2>&1
python manage.py migrate django_celery_beat --noinput > /dev/null 2>&1
python manage.py migrate django_celery_results --noinput > /dev/null 2>&1
echo -e "${GREEN}✓ Database migrations complete${NC}"

# Create logs directory if it doesn't exist
mkdir -p logs

# 4. Kill any existing Celery processes
pkill -f "celery.*purplex" 2>/dev/null || true
sleep 1

# 5. Start Celery Worker with increased concurrency
echo -e "${YELLOW}Starting Celery Worker...${NC}"
# Ensure environment variables are passed to Celery
export OPENAI_API_KEY="${OPENAI_API_KEY}"
# Increase concurrency to prevent deadlock (was 4, now 10)
nohup env OPENAI_API_KEY="${OPENAI_API_KEY}" celery -A purplex worker \
    -l info \
    -Q high_priority,ai_operations,analytics,maintenance \
    --concurrency=10 \
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

# 6. Start Celery Beat
echo -e "${YELLOW}Starting Celery Beat...${NC}"
nohup celery -A purplex beat \
    -l info \
    --scheduler django_celery_beat.schedulers:DatabaseScheduler \
    > logs/celery_beat.log 2>&1 &
BEAT_PID=$!
sleep 2
if ps -p $BEAT_PID > /dev/null; then
    echo -e "${GREEN}✓ Celery Beat started (PID: $BEAT_PID)${NC}"
else
    echo -e "${RED}✗ Celery Beat failed to start${NC}"
    exit 1
fi

# 7. Start Flower (optional monitoring)
echo -e "${YELLOW}Starting Flower (monitoring)...${NC}"
nohup celery -A purplex flower \
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

# 9. Install npm dependencies if needed and start Vue
echo -e "${YELLOW}Starting Vue.js frontend...${NC}"
cd purplex/client

# Install dependencies if node_modules doesn't exist
if [ ! -d "node_modules" ]; then
    echo -e "${YELLOW}Installing npm dependencies...${NC}"
    npm install > /dev/null 2>&1
fi

# Start Vue dev server
nohup npm run dev > ../../logs/vue.log 2>&1 &
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

# 10. Show status
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
echo -e "  • Celery Beat:     $BEAT_PID"
echo -e "  • Flower:          $FLOWER_PID"
echo -e "  • Django:          $DJANGO_PID"
echo -e "  • Vue:             $VUE_PID"
echo ""
echo -e "${GREEN}Logs:${NC}"
echo -e "  • tail -f logs/celery_worker.log"
echo -e "  • tail -f logs/django.log"
echo -e "  • tail -f logs/vue.log"
echo ""
echo -e "${YELLOW}Press Ctrl+C to stop all services${NC}"
echo ""

# Keep script running and show combined logs
echo -e "${GREEN}Showing combined logs (Ctrl+C to stop all services):${NC}"
echo -e "${GREEN}═══════════════════════════════════════════════════════${NC}"

# Function to display logs with prefixes
show_logs() {
    tail -f logs/django.log 2>/dev/null | sed 's/^/[Django] /' &
    tail -f logs/celery_worker.log 2>/dev/null | sed 's/^/[Celery] /' &
    tail -f logs/vue.log 2>/dev/null | sed 's/^/[Vue] /' &
    wait
}

# Show logs until interrupted
show_logs