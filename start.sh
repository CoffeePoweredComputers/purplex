#!/bin/bash

# ============================================================================
# Purplex Local Development Environment Startup Script
# ============================================================================
# Starts all services using local processes with Docker only for databases
# Uses .env.development for configuration
# ============================================================================

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# PIDs for cleanup
DJANGO_PID=""
CELERY_PID=""
CELERY_BEAT_PID=""
VUE_PID=""
FLOWER_PID=""

# Cleanup flag
CLEANING_UP=0

# ============================================================================
# Display Banner
# ============================================================================
echo -e "${CYAN}╔═══════════════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║                                                       ║${NC}"
echo -e "${CYAN}║         ${GREEN}Purplex Development Environment${CYAN}               ║${NC}"
echo -e "${CYAN}║              ${YELLOW}Local Process Mode${CYAN}                       ║${NC}"
echo -e "${CYAN}║                                                       ║${NC}"
echo -e "${CYAN}╚═══════════════════════════════════════════════════════╝${NC}"
echo ""

# ============================================================================
# Cleanup Function
# ============================================================================
cleanup() {
    if [ $CLEANING_UP -eq 1 ]; then
        return
    fi

    CLEANING_UP=1
    echo ""
    echo -e "${YELLOW}╔═══════════════════════════════════════════════════════╗${NC}"
    echo -e "${YELLOW}║           Shutting down services...                  ║${NC}"
    echo -e "${YELLOW}╚═══════════════════════════════════════════════════════╝${NC}"
    echo ""

    # Kill processes gracefully
    echo -e "${BLUE}→ Stopping Django...${NC}"
    [ ! -z "$DJANGO_PID" ] && kill -TERM $DJANGO_PID 2>/dev/null || true
    lsof -ti:8000 2>/dev/null | xargs -r kill -9 2>/dev/null || true

    echo -e "${BLUE}→ Stopping Vue...${NC}"
    [ ! -z "$VUE_PID" ] && kill -TERM $VUE_PID 2>/dev/null || true
    lsof -ti:5173 2>/dev/null | xargs -r kill -9 2>/dev/null || true

    echo -e "${BLUE}→ Stopping Celery worker...${NC}"
    [ ! -z "$CELERY_PID" ] && kill -TERM $CELERY_PID 2>/dev/null || true

    echo -e "${BLUE}→ Stopping Celery beat...${NC}"
    [ ! -z "$CELERY_BEAT_PID" ] && kill -TERM $CELERY_BEAT_PID 2>/dev/null || true

    echo -e "${BLUE}→ Stopping Flower...${NC}"
    [ ! -z "$FLOWER_PID" ] && kill -TERM $FLOWER_PID 2>/dev/null || true
    lsof -ti:5555 2>/dev/null | xargs -r kill -9 2>/dev/null || true

    # Kill any remaining Celery processes
    pkill -f "celery.*purplex" 2>/dev/null || true
    pkill -f "python.*manage.py" 2>/dev/null || true

    sleep 2

    echo ""
    echo -e "${GREEN}✓ All services stopped successfully${NC}"
    echo ""
    exit 0
}

# ============================================================================
# Force Cleanup (Double Ctrl+C)
# ============================================================================
handle_interrupt() {
    if [ $CLEANING_UP -eq 1 ]; then
        echo ""
        echo -e "${RED}╔═══════════════════════════════════════════════════════╗${NC}"
        echo -e "${RED}║              Force Quitting...                        ║${NC}"
        echo -e "${RED}╚═══════════════════════════════════════════════════════╝${NC}"

        pkill -9 -f "celery.*purplex" 2>/dev/null || true
        pkill -9 -f "python.*manage.py" 2>/dev/null || true
        pkill -9 -f "yarn.*vite" 2>/dev/null || true
        lsof -ti:8000 2>/dev/null | xargs -r kill -9 2>/dev/null || true
        lsof -ti:5173 2>/dev/null | xargs -r kill -9 2>/dev/null || true
        lsof -ti:5555 2>/dev/null | xargs -r kill -9 2>/dev/null || true

        exit 1
    fi

    echo ""
    echo -e "${YELLOW}Gracefully shutting down... (Press Ctrl+C again to force quit)${NC}"
    cleanup
}

# Set traps
trap handle_interrupt INT TERM
trap cleanup EXIT

# ============================================================================
# Prerequisites Check
# ============================================================================
echo -e "${BLUE}→ Checking prerequisites...${NC}"

if ! command -v docker &> /dev/null; then
    echo -e "${RED}✗ Docker is not installed${NC}"
    exit 1
fi

if ! command -v python &> /dev/null; then
    echo -e "${RED}✗ Python is not installed${NC}"
    exit 1
fi

if ! command -v node &> /dev/null; then
    echo -e "${RED}✗ Node.js is not installed${NC}"
    exit 1
fi

if [ ! -d "env" ]; then
    echo -e "${RED}✗ Virtual environment not found${NC}"
    echo -e "${YELLOW}  Please create it:${NC}"
    echo "    python -m venv env"
    echo "    source env/bin/activate"
    echo "    pip install -r requirements.txt"
    exit 1
fi

if [ ! -f .env.development ]; then
    echo -e "${RED}✗ .env.development file not found${NC}"
    exit 1
fi

echo -e "${GREEN}✓ All prerequisites met${NC}"
echo ""

# ============================================================================
# Docker Sanity Check
# ============================================================================
echo -e "${BLUE}→ Verifying Docker can start containers...${NC}"
if ! docker_check=$(docker run --rm alpine:latest true 2>&1); then
    echo -e "${RED}✗ Docker cannot start containers:${NC}"
    echo -e "${RED}  $docker_check${NC}"
    echo -e "${YELLOW}  Common causes:${NC}"
    echo -e "${YELLOW}    - Kernel updated but not rebooted (missing veth module)${NC}"
    echo -e "${YELLOW}    - Docker daemon not running${NC}"
    echo -e "${YELLOW}    - Insufficient permissions${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Docker is healthy${NC}"
echo ""

# ============================================================================
# Load Environment Variables
# ============================================================================
echo -e "${BLUE}→ Loading environment variables...${NC}"
set -a
source .env.development
set +a
export DJANGO_SETTINGS_MODULE=purplex.settings
export REDIS_HOST=localhost
echo -e "${GREEN}✓ Environment loaded${NC}"
echo ""

# ============================================================================
# Create Required Directories
# ============================================================================
echo -e "${BLUE}→ Creating required directories...${NC}"
mkdir -p logs staticfiles media
echo -e "${GREEN}✓ Directories created${NC}"
echo ""

# ============================================================================
# Start PostgreSQL
# ============================================================================
echo -e "${BLUE}→ Starting PostgreSQL...${NC}"

if docker ps | grep -q purplex-postgres-dev; then
    echo -e "${GREEN}✓ PostgreSQL already running${NC}"
else
    docker rm -f purplex-postgres-dev > /dev/null 2>&1 || true

    if ! pg_output=$(docker run -d \
        --name purplex-postgres-dev \
        -e POSTGRES_DB=purplex_dev \
        -e POSTGRES_USER=purplex_user \
        -e POSTGRES_PASSWORD=devpass \
        -p 5432:5432 \
        -v purplex_postgres_dev_data:/var/lib/postgresql/data \
        postgres:15-alpine 2>&1); then
        echo -e "${RED}✗ Failed to start PostgreSQL container:${NC}"
        echo -e "${RED}  $pg_output${NC}"
        exit 1
    fi

    # Wait for PostgreSQL to be ready
    echo -e "${BLUE}  Waiting for PostgreSQL to accept connections...${NC}"
    for i in $(seq 1 15); do
        if docker exec purplex-postgres-dev pg_isready -U purplex_user > /dev/null 2>&1; then
            break
        fi
        if [ "$i" -eq 15 ]; then
            echo -e "${RED}✗ PostgreSQL failed to become ready after 15s${NC}"
            echo -e "${YELLOW}  Check: docker logs purplex-postgres-dev${NC}"
            exit 1
        fi
        sleep 1
    done
    echo -e "${GREEN}✓ PostgreSQL started and ready${NC}"
fi
echo ""

# ============================================================================
# Start Redis
# ============================================================================
echo -e "${BLUE}→ Starting Redis...${NC}"

if docker ps | grep -q purplex-redis-dev; then
    echo -e "${GREEN}✓ Redis already running${NC}"
else
    docker rm -f purplex-redis-dev > /dev/null 2>&1 || true

    if ! redis_output=$(docker run -d \
        --name purplex-redis-dev \
        -p 6379:6379 \
        redis:7-alpine 2>&1); then
        echo -e "${RED}✗ Failed to start Redis container:${NC}"
        echo -e "${RED}  $redis_output${NC}"
        exit 1
    fi
fi

# Wait for Redis to be ready
echo -e "${BLUE}  Waiting for Redis to accept connections...${NC}"
for i in $(seq 1 10); do
    if docker exec purplex-redis-dev redis-cli ping > /dev/null 2>&1; then
        break
    fi
    if [ "$i" -eq 10 ]; then
        echo -e "${RED}✗ Redis failed to become ready after 10s${NC}"
        echo -e "${YELLOW}  Check: docker logs purplex-redis-dev${NC}"
        exit 1
    fi
    sleep 1
done
echo -e "${GREEN}✓ Redis started and ready${NC}"
echo ""

# ============================================================================
# Activate Virtual Environment & Run Migrations
# ============================================================================
echo -e "${BLUE}→ Activating Python virtual environment...${NC}"
source env/bin/activate
echo -e "${GREEN}✓ Virtual environment activated${NC}"
echo ""

echo -e "${BLUE}→ Running database migrations...${NC}"
python manage.py migrate --noinput > logs/migrate.log 2>&1 || true
echo -e "${GREEN}✓ Migrations complete${NC}"
echo ""

# ============================================================================
# Kill Existing Processes
# ============================================================================
echo -e "${BLUE}→ Cleaning up old processes...${NC}"
pkill -f "celery.*purplex" 2>/dev/null || true
lsof -ti:8000 2>/dev/null | xargs -r kill -9 2>/dev/null || true
lsof -ti:5173 2>/dev/null | xargs -r kill -9 2>/dev/null || true
lsof -ti:5555 2>/dev/null | xargs -r kill -9 2>/dev/null || true
sleep 2
echo -e "${GREEN}✓ Cleanup complete${NC}"
echo ""

# ============================================================================
# Start Celery Worker
# ============================================================================
echo -e "${BLUE}→ Starting Celery worker...${NC}"
CELERY_WORKER=1 nohup celery -A purplex.celery_simple worker \
    -l info \
    --concurrency=4 \
    --pool=gevent \
    > logs/celery_worker.log 2>&1 &
CELERY_PID=$!
sleep 3

if ps -p $CELERY_PID > /dev/null; then
    echo -e "${GREEN}✓ Celery worker started (PID: $CELERY_PID)${NC}"
else
    echo -e "${RED}✗ Celery worker failed to start${NC}"
    echo -e "${YELLOW}  Check logs/celery_worker.log for details${NC}"
    exit 1
fi
echo ""

# ============================================================================
# Start Celery Beat
# ============================================================================
echo -e "${BLUE}→ Starting Celery beat scheduler...${NC}"
nohup celery -A purplex.celery_simple beat \
    -l info \
    --scheduler django_celery_beat.schedulers:DatabaseScheduler \
    > logs/celery_beat.log 2>&1 &
CELERY_BEAT_PID=$!
sleep 2

if ps -p $CELERY_BEAT_PID > /dev/null; then
    echo -e "${GREEN}✓ Celery beat started (PID: $CELERY_BEAT_PID)${NC}"
else
    echo -e "${YELLOW}⚠ Celery beat failed to start (non-critical)${NC}"
fi
echo ""

# ============================================================================
# Start Flower (Optional)
# ============================================================================
echo -e "${BLUE}→ Starting Flower monitoring...${NC}"
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
echo ""

# ============================================================================
# Start Django Development Server
# ============================================================================
echo -e "${BLUE}→ Starting Django development server...${NC}"
nohup python manage.py runserver > logs/django.log 2>&1 &
DJANGO_PID=$!
sleep 3

if ps -p $DJANGO_PID > /dev/null; then
    echo -e "${GREEN}✓ Django server started (PID: $DJANGO_PID)${NC}"
else
    echo -e "${RED}✗ Django server failed to start${NC}"
    echo -e "${YELLOW}  Check logs/django.log for details${NC}"
    exit 1
fi
echo ""

# ============================================================================
# Start Vue.js Frontend
# ============================================================================
echo -e "${BLUE}→ Starting Vue.js frontend...${NC}"
cd purplex/client

# Install dependencies if needed
if [ ! -d "node_modules" ]; then
    echo -e "${YELLOW}  Installing npm dependencies...${NC}"
    yarn install > ../../logs/yarn_install.log 2>&1
fi

# Start Vite dev server
nohup yarn vite --mode development > ../../logs/vue.log 2>&1 &
VUE_PID=$!
cd ../..
sleep 5

if ps -p $VUE_PID > /dev/null; then
    echo -e "${GREEN}✓ Vue dev server started (PID: $VUE_PID)${NC}"
else
    echo -e "${RED}✗ Vue dev server failed to start${NC}"
    echo -e "${YELLOW}  Check logs/vue.log for details${NC}"
    exit 1
fi
echo ""

# ============================================================================
# Display Status
# ============================================================================
echo ""
echo -e "${CYAN}╔═══════════════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║                                                       ║${NC}"
echo -e "${CYAN}║        ${GREEN}All Services Started Successfully! 🚀${CYAN}        ║${NC}"
echo -e "${CYAN}║                                                       ║${NC}"
echo -e "${CYAN}╚═══════════════════════════════════════════════════════╝${NC}"
echo ""

echo -e "${GREEN}📍 Access Points:${NC}"
echo -e "   ${CYAN}Frontend (Vue.js):${NC}     http://localhost:5173"
echo -e "   ${CYAN}Backend API:${NC}           http://localhost:8000/api"
echo -e "   ${CYAN}Django Admin:${NC}          http://localhost:8000/admin"
echo -e "   ${CYAN}Flower Monitor:${NC}        http://localhost:5555"
echo ""

echo -e "${GREEN}🔧 Service PIDs:${NC}"
echo -e "   ${CYAN}Django:${NC}                $DJANGO_PID"
echo -e "   ${CYAN}Celery Worker:${NC}         $CELERY_PID"
echo -e "   ${CYAN}Celery Beat:${NC}           $CELERY_BEAT_PID"
echo -e "   ${CYAN}Flower:${NC}                $FLOWER_PID"
echo -e "   ${CYAN}Vue.js:${NC}                $VUE_PID"
echo ""

echo -e "${GREEN}📊 Docker Containers:${NC}"
docker ps --filter "name=purplex" --format "   ${CYAN}{{.Names}}:${NC} {{.Status}}"
echo ""

echo -e "${GREEN}📝 View Logs:${NC}"
echo -e "   ${CYAN}Django:${NC}                tail -f logs/django.log"
echo -e "   ${CYAN}Celery Worker:${NC}         tail -f logs/celery_worker.log"
echo -e "   ${CYAN}Celery Beat:${NC}           tail -f logs/celery_beat.log"
echo -e "   ${CYAN}Vue.js:${NC}                tail -f logs/vue.log"
echo -e "   ${CYAN}Flower:${NC}                tail -f logs/flower.log"
echo ""

echo -e "${YELLOW}Press Ctrl+C to stop all services (Press twice to force quit)${NC}"
echo ""
echo -e "${CYAN}╔═══════════════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║            Showing combined logs...                   ║${NC}"
echo -e "${CYAN}╚═══════════════════════════════════════════════════════╝${NC}"
echo ""

# ============================================================================
# Stream Logs
# ============================================================================
show_logs() {
    pkill -f "tail -f logs/" 2>/dev/null || true

    tail -f logs/django.log 2>/dev/null | sed 's/^/[Django] /' &
    TAIL_DJANGO=$!
    tail -f logs/celery_worker.log 2>/dev/null | sed 's/^/[Celery] /' &
    TAIL_CELERY=$!
    tail -f logs/vue.log 2>/dev/null | sed 's/^/[Vue] /' &
    TAIL_VUE=$!

    wait $TAIL_DJANGO $TAIL_CELERY $TAIL_VUE
}

show_logs
