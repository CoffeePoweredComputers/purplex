#!/bin/bash
# Rollback to previous deployment
# Usage: ./rollback.sh [backup-tag]

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
BACKUP_TAG="${1:-}"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log() {
    echo -e "$1"
}

log_error() {
    log "${RED}[ERROR]${NC} $1"
}

log_success() {
    log "${GREEN}[SUCCESS]${NC} $1"
}

if [ -z "$BACKUP_TAG" ]; then
    log_error "Usage: $0 <backup-tag>"
    log "Available backups:"
    log ""
    log "Database backups:"
    ls -lt "$PROJECT_ROOT/backups/" 2>/dev/null | grep "db-backup-" | head -5 || echo "  No backups found"
    exit 1
fi

log "=========================================="
log "Purplex Rollback Procedure"
log "Target: $BACKUP_TAG"
log "=========================================="

# Verify backup exists
DB_BACKUP="$PROJECT_ROOT/backups/db-${BACKUP_TAG}.sql"
if [ ! -f "$DB_BACKUP" ]; then
    log_error "Database backup not found: $DB_BACKUP"
    exit 1
fi

# Step 1: Stop current services
log "Stopping current services..."
docker compose down

# Step 2: Restore database
log "Restoring database from backup..."

# Start only postgres and redis
docker compose up -d postgres redis
sleep 10

# Drop and recreate database
docker compose exec -T postgres psql -U ${POSTGRES_USER:-purplex_user} -c "DROP DATABASE IF EXISTS ${POSTGRES_DB:-purplex_dev};"
docker compose exec -T postgres psql -U ${POSTGRES_USER:-purplex_user} -c "CREATE DATABASE ${POSTGRES_DB:-purplex_dev};"

# Restore backup
cat "$DB_BACKUP" | docker compose exec -T postgres psql -U ${POSTGRES_USER:-purplex_user} ${POSTGRES_DB:-purplex_dev}

log_success "Database restored"

# Step 3: Start services
log "Starting services with restored state..."
docker compose up -d

# Step 4: Wait for health checks
log "Waiting for services to be healthy..."
sleep 30

MAX_WAIT=60
WAITED=0
while [ $WAITED -lt $MAX_WAIT ]; do
    if docker compose ps 2>/dev/null | grep -q "healthy"; then
        log_success "Services are healthy"
        break
    fi
    sleep 5
    WAITED=$((WAITED + 5))
done

if [ $WAITED -ge $MAX_WAIT ]; then
    log_error "Services failed to become healthy after rollback"
    log "Check logs: docker compose logs"
    exit 1
fi

# Step 5: Verify rollback
log "Verifying rollback..."
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/api/health/ 2>/dev/null || echo "000")

if [ "$HTTP_CODE" = "200" ]; then
    log_success "Rollback successful!"
else
    log_error "Health check failed after rollback (HTTP $HTTP_CODE)"
    exit 1
fi

log ""
log "=========================================="
log_success "ROLLBACK COMPLETED"
log "=========================================="
log "Services status:"
docker compose ps
log ""
log "Check logs if issues persist:"
log "  docker compose logs -f"
log "=========================================="

exit 0