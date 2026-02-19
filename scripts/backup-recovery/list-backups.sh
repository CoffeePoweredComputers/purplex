#!/bin/bash
################################################################################
# List Available Backups
#
# Purpose: List all available PostgreSQL backups (local and S3)
# Usage: ./list-backups.sh
################################################################################

# Configuration
BACKUP_DIR="${BACKUP_DIR:-/home/ubuntu/backups/postgres}"
S3_BUCKET="${S3_BUCKET:-purplex-db-backups}"

log() {
    echo "$*"
}

list_local_backups() {
    log "=== Local Backups ==="
    log ""

    if [[ ! -d "$BACKUP_DIR" ]]; then
        log "Local backup directory does not exist: $BACKUP_DIR"
        return
    fi

    local backups=($(find "$BACKUP_DIR" -name "*.sql.gz" -type f 2>/dev/null))

    if [[ ${#backups[@]} -eq 0 ]]; then
        log "No local backups found."
    else
        log "Found ${#backups[@]} local backup(s):"
        log ""
        for backup in "${backups[@]}"; do
            local size=$(du -h "$backup" | cut -f1)
            local date=$(stat -c %y "$backup" 2>/dev/null | cut -d' ' -f1 || stat -f %Sm -t "%Y-%m-%d" "$backup")
            log "  File: $(basename "$backup")"
            log "  Path: $backup"
            log "  Size: $size"
            log "  Date: $date"
            log ""
        done
    fi
}

list_s3_backups() {
    log "=== S3 Backups ==="
    log ""

    if ! command -v aws &> /dev/null; then
        log "AWS CLI not found - cannot list S3 backups"
        return
    fi

    log "Bucket: s3://${S3_BUCKET}"
    log ""

    if aws s3 ls "s3://${S3_BUCKET}/" &>/dev/null; then
        local count=$(aws s3 ls "s3://${S3_BUCKET}/daily/" --recursive | grep ".sql.gz" | wc -l)
        log "Found $count S3 backup(s):"
        log ""
        aws s3 ls "s3://${S3_BUCKET}/daily/" --recursive --human-readable | \
            grep ".sql.gz" | \
            awk '{printf "  Date: %s %s | Size: %s | File: %s\n", $1, $2, $3, $4}'
    else
        log "Cannot access S3 bucket (may not exist or insufficient permissions)"
    fi
}

backup_summary() {
    log ""
    log "=== Summary ==="

    local local_count=0
    if [[ -d "$BACKUP_DIR" ]]; then
        local_count=$(find "$BACKUP_DIR" -name "*.sql.gz" -type f 2>/dev/null | wc -l)
    fi

    local s3_count=0
    if command -v aws &> /dev/null; then
        s3_count=$(aws s3 ls "s3://${S3_BUCKET}/daily/" --recursive 2>/dev/null | grep ".sql.gz" | wc -l || echo "0")
    fi

    log "Local backups: $local_count"
    log "S3 backups: $s3_count"

    if [[ $local_count -eq 0 ]] && [[ $s3_count -eq 0 ]]; then
        log ""
        log "WARNING: No backups found! Run backup-postgres.sh to create backups."
    fi
}

main() {
    log "Purplex PostgreSQL Backup Inventory"
    log "======================================"
    log ""

    list_local_backups
    log ""
    list_s3_backups
    backup_summary
}

main "$@"