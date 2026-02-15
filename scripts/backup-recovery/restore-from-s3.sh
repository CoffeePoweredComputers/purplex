#!/bin/bash
################################################################################
# PostgreSQL Restore Script (S3 Backup)
#
# Purpose: Restore PostgreSQL database from S3 backup
# Usage: ./restore-from-s3.sh [s3-key]
# Example: ./restore-from-s3.sh daily/2025-09-29/purplex_purplex_prod_2025-09-29_02-00-00.sql.gz
# WARNING: This will OVERWRITE the existing database!
################################################################################

set -e  # Exit on error

# =============================================================================
# CONFIGURATION
# =============================================================================

# S3 Configuration
S3_BUCKET="${S3_BUCKET:-purplex-db-backups}"
S3_KEY="${1:-}"

# Temporary directory for downloads
TEMP_DIR="${TEMP_DIR:-/tmp/restore-$(date +%s)}"

# Database Configuration
DB_CONTAINER="${DB_CONTAINER:-purplex_postgres}"
DB_NAME="${DB_NAME:-purplex_prod}"
DB_USER="${DB_USER:-purplex_user}"

# =============================================================================
# FUNCTIONS
# =============================================================================

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*"
}

error_exit() {
    log "ERROR: $1"
    cleanup
    exit 1
}

cleanup() {
    if [[ -d "$TEMP_DIR" ]]; then
        log "Cleaning up temporary files..."
        rm -rf "$TEMP_DIR"
    fi
}

check_dependencies() {
    local deps=("docker" "gunzip" "aws")
    for cmd in "${deps[@]}"; do
        if ! command -v "$cmd" &> /dev/null; then
            error_exit "Required command not found: $cmd"
        fi
    done
}

list_s3_backups() {
    log "Listing available S3 backups..."
    aws s3 ls "s3://${S3_BUCKET}/daily/" --recursive | grep ".sql.gz" | awk '{print $4}' | sort -r
}

select_backup() {
    if [[ -n "$S3_KEY" ]]; then
        log "Using specified S3 key: $S3_KEY"
        return 0
    fi

    log "Searching for available S3 backups..."
    local backups=($(list_s3_backups))

    if [[ ${#backups[@]} -eq 0 ]]; then
        error_exit "No backup files found in S3 bucket: s3://${S3_BUCKET}"
    fi

    log "Available S3 backups (most recent first):"
    for i in "${!backups[@]}"; do
        if [[ $i -lt 10 ]]; then  # Show only last 10
            printf "%2d) %s\n" $((i+1)) "${backups[$i]}"
        fi
    done

    echo ""
    read -p "Select backup number (1-${#backups[@]}) or press Enter for most recent: " selection

    if [[ -z "$selection" ]]; then
        S3_KEY="${backups[0]}"
    elif [[ "$selection" =~ ^[0-9]+$ ]] && [[ "$selection" -ge 1 ]] && [[ "$selection" -le "${#backups[@]}" ]]; then
        S3_KEY="${backups[$((selection-1))]}"
    else
        error_exit "Invalid selection"
    fi

    log "Selected backup: $S3_KEY"
}

download_backup() {
    log "Downloading backup from S3..."
    mkdir -p "$TEMP_DIR"

    local s3_path="s3://${S3_BUCKET}/${S3_KEY}"
    local local_path="${TEMP_DIR}/backup.sql.gz"

    if aws s3 cp "$s3_path" "$local_path"; then
        log "Download complete"
        BACKUP_FILE="$local_path"
    else
        error_exit "Failed to download backup from S3"
    fi

    # Get file size
    local size=$(du -h "$BACKUP_FILE" | cut -f1)
    log "Downloaded backup size: $size"
}

verify_backup() {
    log "Verifying backup integrity..."
    if ! gzip -t "$BACKUP_FILE" 2>/dev/null; then
        error_exit "Downloaded backup is corrupted!"
    fi
    log "Backup verification successful"
}

confirm_restore() {
    log "=========================================="
    log "PostgreSQL Database Restore from S3"
    log "=========================================="
    log "S3 location: s3://${S3_BUCKET}/${S3_KEY}"
    log "Target database: $DB_NAME"
    log "Container: $DB_CONTAINER"
    log ""
    log "WARNING: This will COMPLETELY OVERWRITE the current database!"
    log "All existing data will be permanently deleted."
    log ""
    read -p "Type 'yes' to continue or anything else to cancel: " confirm

    if [[ "$confirm" != "yes" ]]; then
        log "Restore cancelled by user."
        cleanup
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
        --verbose \
        --jobs=4 2>&1 | grep -E "(restoring|creating|processing)" | tail -10; then
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
    log "Starting PostgreSQL restore from S3"

    # Trap cleanup on exit
    trap cleanup EXIT

    # Pre-flight checks
    check_dependencies
    check_container

    # Select backup from S3
    select_backup

    # Download backup
    download_backup

    # Verify download
    verify_backup

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
    log "S3 backup: $S3_KEY"
    log ""
    log "IMPORTANT: Please verify application functionality before resuming normal operations."
}

# Run main function
main "$@"