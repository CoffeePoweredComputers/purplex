#!/bin/bash
################################################################################
# PostgreSQL Backup Script for Purplex
#
# Purpose: Creates compressed PostgreSQL dumps and uploads to S3
# Usage: ./backup-postgres.sh
# Cron: 0 2 * * * /path/to/backup-postgres.sh
################################################################################

set -e  # Exit on error
set -u  # Exit on undefined variable

# =============================================================================
# CONFIGURATION
# =============================================================================

# Directories
BACKUP_DIR="${BACKUP_DIR:-/home/ubuntu/backups/postgres}"
LOG_DIR="${LOG_DIR:-/home/ubuntu/logs}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# S3 Configuration
S3_BUCKET="${S3_BUCKET:-purplex-db-backups}"
S3_PREFIX="${S3_PREFIX:-daily}"

# Backup Retention
LOCAL_RETENTION_DAYS="${LOCAL_RETENTION_DAYS:-7}"
S3_RETENTION_DAYS="${S3_RETENTION_DAYS:-30}"

# Database Configuration
DB_CONTAINER="${DB_CONTAINER:-purplex_postgres}"
DB_NAME="${DB_NAME:-purplex_prod}"
DB_USER="${DB_USER:-purplex_user}"

# Timestamp
TIMESTAMP=$(date +%Y-%m-%d_%H-%M-%S)
DATE_FOLDER=$(date +%Y-%m-%d)

# Backup Files
BACKUP_FILENAME="purplex_${DB_NAME}_${TIMESTAMP}.sql.gz"
BACKUP_PATH="${BACKUP_DIR}/${DATE_FOLDER}/${BACKUP_FILENAME}"
LOG_FILE="${LOG_DIR}/backup-postgres.log"

# =============================================================================
# FUNCTIONS
# =============================================================================

log() {
    local level=$1
    shift
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] [${level}] $*" | tee -a "${LOG_FILE}"
}

check_dependencies() {
    local deps=("docker" "gzip")
    for cmd in "${deps[@]}"; do
        if ! command -v "$cmd" &> /dev/null; then
            log "ERROR" "Required command not found: $cmd"
            exit 1
        fi
    done

    # Check for AWS CLI (optional - only needed for S3 upload)
    if ! command -v aws &> /dev/null; then
        log "WARN" "AWS CLI not found - S3 upload will be skipped"
    fi
}

check_container() {
    if ! docker ps --format '{{.Names}}' | grep -q "^${DB_CONTAINER}$"; then
        log "ERROR" "PostgreSQL container '${DB_CONTAINER}' is not running"
        exit 1
    fi
}

create_backup_directory() {
    mkdir -p "${BACKUP_DIR}/${DATE_FOLDER}"
    mkdir -p "${LOG_DIR}"
}

perform_backup() {
    log "INFO" "Starting backup of database: ${DB_NAME}"
    log "INFO" "Backup file: ${BACKUP_FILENAME}"

    # Create pg_dump backup with compression
    # Options:
    #   -Fc: Custom format (compressed, allows parallel restore)
    #   -Z9: Maximum compression
    #   --no-owner: Don't restore ownership
    #   --no-acl: Don't restore access privileges
    if docker exec "${DB_CONTAINER}" \
        pg_dump -U "${DB_USER}" \
        -Fc \
        -Z9 \
        --no-owner \
        --no-acl \
        "${DB_NAME}" | gzip > "${BACKUP_PATH}"; then

        log "INFO" "Backup created successfully"

        # Get backup file size
        local size=$(du -h "${BACKUP_PATH}" | cut -f1)
        log "INFO" "Backup size: ${size}"

        return 0
    else
        log "ERROR" "Backup failed"
        return 1
    fi
}

verify_backup() {
    log "INFO" "Verifying backup integrity"

    # Check file exists and is not empty
    if [[ ! -f "${BACKUP_PATH}" ]]; then
        log "ERROR" "Backup file not found: ${BACKUP_PATH}"
        return 1
    fi

    # Get file size (cross-platform compatible)
    local size
    if [[ "$OSTYPE" == "darwin"* ]]; then
        size=$(stat -f%z "${BACKUP_PATH}" 2>/dev/null)
    else
        size=$(stat -c%s "${BACKUP_PATH}" 2>/dev/null)
    fi

    if [[ $size -lt 1000 ]]; then
        log "ERROR" "Backup file too small (${size} bytes), possibly corrupted"
        return 1
    fi

    # Verify gzip integrity
    if ! gzip -t "${BACKUP_PATH}" 2>/dev/null; then
        log "ERROR" "Backup file is corrupted (gzip test failed)"
        return 1
    fi

    log "INFO" "Backup verification successful"
    return 0
}

upload_to_s3() {
    # Check if AWS CLI is available
    if ! command -v aws &> /dev/null; then
        log "WARN" "AWS CLI not available - skipping S3 upload"
        return 0
    fi

    log "INFO" "Uploading backup to S3: s3://${S3_BUCKET}/${S3_PREFIX}/${DATE_FOLDER}/"

    # Upload to S3 with server-side encryption
    if aws s3 cp "${BACKUP_PATH}" \
        "s3://${S3_BUCKET}/${S3_PREFIX}/${DATE_FOLDER}/${BACKUP_FILENAME}" \
        --storage-class STANDARD_IA \
        --server-side-encryption AES256 \
        --metadata "database=${DB_NAME},timestamp=${TIMESTAMP},host=$(hostname)" \
        --quiet 2>/dev/null; then

        log "INFO" "S3 upload successful"
        return 0
    else
        log "WARN" "S3 upload failed - backup saved locally only"
        return 1
    fi
}

cleanup_old_local_backups() {
    log "INFO" "Cleaning up local backups older than ${LOCAL_RETENTION_DAYS} days"

    find "${BACKUP_DIR}" -type f -name "*.sql.gz" -mtime +${LOCAL_RETENTION_DAYS} -delete 2>/dev/null || true

    # Remove empty directories
    find "${BACKUP_DIR}" -type d -empty -delete 2>/dev/null || true

    log "INFO" "Local cleanup completed"
}

send_notification() {
    local status=$1
    local message=$2

    # Optional: Send notification via SNS, email, etc.
    # Uncomment and configure if needed
    # if command -v aws &> /dev/null; then
    #     aws sns publish \
    #         --topic-arn "arn:aws:sns:region:account:purplex-backup-alerts" \
    #         --subject "Purplex Backup ${status}" \
    #         --message "${message}" 2>/dev/null || true
    # fi

    log "INFO" "Notification: ${status} - ${message}"
}

# =============================================================================
# MAIN EXECUTION
# =============================================================================

main() {
    log "INFO" "=========================================="
    log "INFO" "Starting PostgreSQL backup process"
    log "INFO" "=========================================="

    # Pre-flight checks
    check_dependencies
    check_container
    create_backup_directory

    # Perform backup
    if ! perform_backup; then
        send_notification "FAILED" "Backup creation failed for ${DB_NAME}"
        exit 1
    fi

    # Verify backup
    if ! verify_backup; then
        send_notification "FAILED" "Backup verification failed for ${DB_NAME}"
        exit 1
    fi

    # Upload to S3 (non-fatal if it fails)
    upload_to_s3

    # Cleanup old backups
    cleanup_old_local_backups

    # Success
    log "INFO" "Backup process completed successfully"
    send_notification "SUCCESS" "Backup completed for ${DB_NAME}"

    log "INFO" "=========================================="
}

# Run main function
main "$@"