#!/bin/bash
# Zero-downtime rolling deployment for Purplex
# Uses health checks and staged migrations

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
DEPLOYMENT_LOG="$PROJECT_ROOT/logs/deployment-$(date +%Y%m%d-%H%M%S).log"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Logging functions
log() {
    echo -e "$1" | tee -a "$DEPLOYMENT_LOG"
}

log_step() {
    log "${BLUE}[STEP]${NC} $1"
}

log_success() {
    log "${GREEN}[SUCCESS]${NC} $1"
}

log_error() {
    log "${RED}[ERROR]${NC} $1"
}

log_warning() {
    log "${YELLOW}[WARNING]${NC} $1"
}

# Error handler
trap 'log_error "Deployment failed at line $LINENO"; exit 1' ERR

# Create logs directory
mkdir -p "$PROJECT_ROOT/logs"
mkdir -p "$PROJECT_ROOT/backups"

log "=========================================="
log "Purplex Rolling Deployment"
log "Started: $(date)"
log "=========================================="

# Step 1: Pre-deployment checks
log_step "Running pre-deployment checks..."
bash "$SCRIPT_DIR/pre-deployment-check.sh"
log_success "Pre-deployment checks passed"

# Step 2: Backup current state
log_step "Creating backup..."
BACKUP_TAG="backup-$(date +%Y%m%d-%H%M%S)"

# Backup database
log "Creating database backup..."
docker compose exec -T postgres pg_dump -U ${POSTGRES_USER:-purplex_user} ${POSTGRES_DB:-purplex_dev} > "$PROJECT_ROOT/backups/db-${BACKUP_TAG}.sql"
log_success "Database backup created: backups/db-${BACKUP_TAG}.sql"

# Step 3: Build new images
log_step "Building new Docker images..."
docker compose build --pull web celery
log_success "New images built"

# Step 4: Check for pending migrations
log_step "Checking for database migrations..."
PENDING_MIGRATIONS=$(docker compose run --rm web python manage.py showmigrations --plan 2>/dev/null | grep "\[ \]" | wc -l || echo "0")

if [ "$PENDING_MIGRATIONS" -gt 0 ]; then
    log_warning "$PENDING_MIGRATIONS pending migrations detected"

    # Step 5: Run migrations (separate from service startup)
    log_step "Running database migrations..."

    # Stop Celery workers to prevent concurrent access during migration
    log "Stopping Celery workers..."
    docker compose stop celery

    # Run migrations
    docker compose run --rm web python manage.py migrate --noinput

    # Verify migrations succeeded
    REMAINING=$(docker compose run --rm web python manage.py showmigrations --plan 2>/dev/null | grep "\[ \]" | wc -l || echo "0")
    if [ "$REMAINING" -gt 0 ]; then
        log_error "Migrations failed! $REMAINING migrations still pending"
        log "Rolling back..."
        bash "$SCRIPT_DIR/rollback.sh" "$BACKUP_TAG"
        exit 1
    fi

    log_success "Database migrations completed"
else
    log "No pending migrations"
fi

# Step 6: Rolling update - Web service
log_step "Updating web service with zero downtime..."

# Scale up web service (run new alongside old)
log "Scaling web service to 2 instances..."
docker compose up -d --scale web=2 --no-recreate web

# Wait for new instance to be healthy
log "Waiting for new web instance to be healthy..."
sleep 10

MAX_WAIT=60
WAITED=0
while [ $WAITED -lt $MAX_WAIT ]; do
    HEALTHY=$(docker compose ps web 2>/dev/null | grep -c "healthy" || echo "0")
    if [ "$HEALTHY" -ge 2 ]; then
        log_success "New web instance is healthy"
        break
    fi
    sleep 5
    WAITED=$((WAITED + 5))
    log "Waiting... ($WAITED/${MAX_WAIT}s)"
done

if [ $WAITED -ge $MAX_WAIT ]; then
    log_error "New web instance failed to become healthy"
    log "Rolling back..."
    bash "$SCRIPT_DIR/rollback.sh" "$BACKUP_TAG"
    exit 1
fi

# Verify new instance handles traffic
log "Verifying new instance handles requests..."
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/api/health/ 2>/dev/null || echo "000")
if [ "$HTTP_CODE" != "200" ]; then
    log_error "New instance failing health checks (HTTP $HTTP_CODE)"
    log "Rolling back..."
    bash "$SCRIPT_DIR/rollback.sh" "$BACKUP_TAG"
    exit 1
fi

# Scale down to 1 instance (removes old container)
log "Removing old web instance..."
docker compose up -d --scale web=1 --no-recreate web
sleep 5

log_success "Web service updated"

# Step 7: Rolling update - Celery service
log_step "Updating Celery service..."

# Scale up Celery
log "Scaling Celery service to 2 instances..."
docker compose up -d --scale celery=2 --no-recreate celery
sleep 15

# Verify new worker
log "Verifying new Celery worker..."
CELERY_HEALTHY=$(docker compose exec -T celery celery -A purplex.celery_simple inspect ping 2>&1 | grep -c "pong" || echo "0")
if [ "$CELERY_HEALTHY" -lt 1 ]; then
    log_warning "Celery health check inconclusive, continuing..."
else
    log_success "New Celery worker is healthy"
fi

# Scale down to 1 instance
log "Removing old Celery worker..."
docker compose up -d --scale celery=1 --no-recreate celery
sleep 5

log_success "Celery service updated"

# Step 8: Update nginx (if needed)
log_step "Updating nginx if needed..."
docker compose up -d nginx
log_success "Nginx updated"

# Step 9: Collect static files
log_step "Collecting static files..."
docker compose exec -T web python manage.py collectstatic --noinput
log_success "Static files collected"

# Step 10: Post-deployment validation
log_step "Running post-deployment validation..."

# Check web service
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/api/health/ 2>/dev/null || echo "000")
if [ "$HTTP_CODE" != "200" ]; then
    log_error "Post-deployment health check failed (HTTP $HTTP_CODE)"
    log "Rolling back..."
    bash "$SCRIPT_DIR/rollback.sh" "$BACKUP_TAG"
    exit 1
fi

# Check Celery
if docker compose exec -T celery celery -A purplex.celery_simple inspect ping >/dev/null 2>&1; then
    log_success "Celery workers operational"
else
    log_warning "Celery health check failed, but continuing (non-critical)"
fi

# Step 11: Cleanup old images
log_step "Cleaning up old Docker images..."
docker image prune -f
log_success "Cleanup completed"

# Step 12: Deployment summary
log ""
log "=========================================="
log_success "DEPLOYMENT SUCCESSFUL"
log "Completed: $(date)"
log "=========================================="
log "Backup tag: $BACKUP_TAG"
log "Deployment log: $DEPLOYMENT_LOG"
log ""
log "Services status:"
docker compose ps
log ""
log "To rollback this deployment:"
log "  bash scripts/rollback.sh $BACKUP_TAG"
log ""
log "To view logs:"
log "  docker compose logs -f web celery"
log "=========================================="

exit 0