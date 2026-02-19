#!/bin/bash
################################################################################
# PostgreSQL Restore Script (Local Backup)
#
# Purpose: Restore PostgreSQL database from local backup file
# Usage: ./restore-from-local.sh [backup-file]
# WARNING: This will OVERWRITE the existing database!
################################################################################

set -e  # Exit on error

# =============================================================================
# CONFIGURATION
# =============================================================================

# Default backup directory
BACKUP_DIR="${BACKUP_DIR:-/home/ubuntu/backups/postgres}"

# Database Configuration
DB_CONTAINER="${DB_CONTAINER:-purplex_postgres}"
DB_NAME="${DB_NAME:-purplex_prod}"
DB_USER="${DB_USER:-purplex_user}"

# Backup file (can be passed as argument)
BACKUP_FILE="${1:-}"

# =============================================================================
# FUNCTIONS
# =============================================================================

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*"
}

error_exit() {
    log "ERROR: $1"
    exit 1
}

check_dependencies() {
    local deps=("docker" "gunzip")
    for cmd in "${deps[@]}"; do
        if ! command -v "$cmd" &> /dev/null; then
            error_exit "Required command not found: $cmd"
        fi
    done
}

select_backup_file() {
    if [[ -n "$BACKUP_FILE" && -f "$BACKUP_FILE" ]]; then
        log "Using specified backup file: $BACKUP_FILE"
        return 0
    fi

    log "Searching for available backups..."
    local backups=($(find "$BACKUP_DIR" -name "*.sql.gz" -type f -exec ls -t {} + 2>/dev/null))

    if [[ ${#backups[@]} -eq 0 ]]; then
        error_exit "No backup files found in $BACKUP_DIR"
    fi

    log "Available backups:"
    for i in "${!backups[@]}"; do
        local size=$(du -h "${backups[$i]}" | cut -f1)
        local date=$(stat -c %y "${backups[$i]}" 2>/dev/null | cut -d' ' -f1 || stat -f %Sm -t "%Y-%m-%d" "${backups[$i]}")
        printf "%2d) %s (Size: %s, Date: %s)\n" $((i+1)) "$(basename "${backups[$i]}")" "$size" "$date"
    done

    echo ""
    read -p "Select backup number (1-${#backups[@]}) or press Enter for most recent: " selection

    if [[ -z "$selection" ]]; then
        BACKUP_FILE="${backups[0]}"
    elif [[ "$selection" =~ ^[0-9]+$ ]] && [[ "$selection" -ge 1 ]] && [[ "$selection" -le "${#backups[@]}" ]]; then
        BACKUP_FILE="${backups[$((selection-1))]}"
    else
        error_exit "Invalid selection"
    fi

    log "Selected backup: $BACKUP_FILE"
}

confirm_restore() {
    local size=$(du -h "$BACKUP_FILE" | cut -f1)

    log "=========================================="
    log "PostgreSQL Database Restore"
    log "=========================================="
    log "Backup file: $BACKUP_FILE"
    log "Backup size: $size"
    log "Target database: $DB_NAME"
    log "Container: $DB_CONTAINER"
    log ""
    log "WARNING: This will COMPLETELY OVERWRITE the current database!"
    log "All existing data will be permanently deleted."
    log ""
    read -p "Type 'yes' to continue or anything else to cancel: " confirm

    if [[ "$confirm" != "yes" ]]; then
        log "Restore cancelled by user."
        exit 0
    fi
}

check_container() {
    if ! docker ps --format '{{.Names}}' | grep -q "^${DB_CONTAINER}$"; then
        error_exit "PostgreSQL container '${DB_CONTAINER}' is not running"
    fi
}

stop_services() {
    log "Stopping application services..."
    if command -v docker-compose &> /dev/null; then
        docker-compose stop web celery 2>/dev/null || log "Note: Could not stop services (may not exist)"
    fi
}

terminate_connections() {
    log "Terminating database connections..."
    docker exec ${DB_CONTAINER} psql -U ${DB_USER} -d postgres -c \
        "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname='${DB_NAME}' AND pid <> pg_backend_pid();" \
        2>/dev/null || log "Note: No connections to terminate"
}

drop_and_recreate_database() {
    log "Recreating database..."
    docker exec ${DB_CONTAINER} psql -U ${DB_USER} -d postgres -c "DROP DATABASE IF EXISTS ${DB_NAME};" || error_exit "Failed to drop database"
    docker exec ${DB_CONTAINER} psql -U ${DB_USER} -d postgres -c "CREATE DATABASE ${DB_NAME};" || error_exit "Failed to create database"
}

restore_backup() {
    log "Restoring backup (this may take several minutes)..."
    if gunzip -c "${BACKUP_FILE}" | docker exec -i ${DB_CONTAINER} \
        pg_restore -U ${DB_USER} -d ${DB_NAME} \
        --no-owner \
        --no-acl \
        --verbose 2>&1 | grep -E "(restoring|creating|processing)" | tail -10; then
        log "Backup restored successfully"
    else
        error_exit "Backup restore failed"
    fi
}

verify_restore() {
    log "Verifying restore..."
    local table_count=$(docker exec ${DB_CONTAINER} psql -U ${DB_USER} -d ${DB_NAME} -t -c \
        "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='public';")

    log "Tables restored: $table_count"

    if [[ $table_count -lt 5 ]]; then
        log "WARNING: Very few tables restored. Database may be incomplete."
    fi
}

run_migrations() {
    log "Running Django migrations..."
    if command -v docker-compose &> /dev/null; then
        docker-compose run --rm web python manage.py migrate 2>/dev/null || log "Note: Migrations may have issues (check manually)"
    else
        log "Note: docker-compose not found, skipping migrations"
    fi
}

restart_services() {
    log "Restarting services..."
    if command -v docker-compose &> /dev/null; then
        docker-compose start web celery 2>/dev/null || log "Note: Could not start services"
    fi
}

# =============================================================================
# MAIN EXECUTION
# =============================================================================

main() {
    log "Starting PostgreSQL restore process"

    # Pre-flight checks
    check_dependencies
    check_container

    # Select backup file if not specified
    select_backup_file

    # Confirm restore operation
    confirm_restore

    # Perform restore
    stop_services
    terminate_connections
    drop_and_recreate_database
    restore_backup
    verify_restore
    run_migrations
    restart_services

    log "=========================================="
    log "Restore Complete!"
    log "=========================================="
    log "Database: $DB_NAME"
    log "Backup: $BACKUP_FILE"
    log ""
    log "IMPORTANT: Please verify application functionality before resuming normal operations."
}

# Run main function
main "$@"