#!/bin/bash
# Backup Script for Sales Agent Platform
# Supports: PostgreSQL, Redis, Application Files

set -e

# Configuration
BACKUP_DIR="${BACKUP_DIR:-/var/backups/sales-agent}"
S3_BUCKET="${S3_BUCKET:-s3://sales-agent-backups}"
RETENTION_DAYS="${RETENTION_DAYS:-30}"
POSTGRES_HOST="${POSTGRES_HOST:-localhost}"
POSTGRES_DB="${POSTGRES_DB:-sales_agent}"
POSTGRES_USER="${POSTGRES_USER:-postgres}"
REDIS_HOST="${REDIS_HOST:-localhost}"
REDIS_PORT="${REDIS_PORT:-6379}"

# Timestamp
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
DATE=$(date +%Y%m%d)

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Logging
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Usage
usage() {
    cat << EOF
Usage: $0 [OPTIONS]

Backup script for Sales Agent platform components.

OPTIONS:
    --full              Full backup (database + files)
    --db                Database backup only (PostgreSQL)
    --wal               WAL archive backup (PostgreSQL incremental)
    --redis             Redis backup (RDB snapshot)
    --files             Application files backup
    --upload            Upload to S3/cloud storage
    --verify            Verify backup integrity
    --cleanup           Clean old backups (older than RETENTION_DAYS)
    --help              Show this help message

ENVIRONMENT VARIABLES:
    BACKUP_DIR          Local backup directory (default: /var/backups/sales-agent)
    S3_BUCKET           S3 bucket for cloud backups (default: s3://sales-agent-backups)
    RETENTION_DAYS      Days to retain backups (default: 30)
    POSTGRES_HOST       PostgreSQL host (default: localhost)
    POSTGRES_DB         PostgreSQL database name (default: sales_agent)
    POSTGRES_USER       PostgreSQL user (default: postgres)
    REDIS_HOST          Redis host (default: localhost)
    REDIS_PORT          Redis port (default: 6379)

EXAMPLES:
    # Full backup
    $0 --full --upload

    # Database backup only
    $0 --db

    # WAL backup (incremental)
    $0 --wal --upload

    # Cleanup old backups
    $0 --cleanup

EOF
    exit 1
}

# Create backup directories
setup_backup_dirs() {
    log_info "Creating backup directories..."
    mkdir -p "$BACKUP_DIR/postgres"
    mkdir -p "$BACKUP_DIR/wal"
    mkdir -p "$BACKUP_DIR/redis"
    mkdir -p "$BACKUP_DIR/files"
}

# PostgreSQL full backup
backup_postgres() {
    log_info "Starting PostgreSQL backup..."
    
    BACKUP_FILE="$BACKUP_DIR/postgres/sales_agent_${TIMESTAMP}.sql.gz"
    
    pg_dump -h "$POSTGRES_HOST" \
            -U "$POSTGRES_USER" \
            -d "$POSTGRES_DB" \
            --format=custom \
            --compress=9 \
            --file="$BACKUP_FILE.tmp"
    
    if [ $? -eq 0 ]; then
        mv "$BACKUP_FILE.tmp" "$BACKUP_FILE"
        
        # Calculate checksum
        sha256sum "$BACKUP_FILE" > "$BACKUP_FILE.sha256"
        
        # Get backup size
        SIZE=$(du -h "$BACKUP_FILE" | cut -f1)
        
        log_info "PostgreSQL backup completed: $BACKUP_FILE ($SIZE)"
        echo "$BACKUP_FILE"
    else
        log_error "PostgreSQL backup failed!"
        rm -f "$BACKUP_FILE.tmp"
        exit 1
    fi
}

# PostgreSQL WAL archiving
backup_wal() {
    log_info "Archiving PostgreSQL WAL files..."
    
    WAL_DIR="/var/lib/postgresql/data/pg_wal"
    WAL_BACKUP="$BACKUP_DIR/wal/wal_${TIMESTAMP}.tar.gz"
    
    if [ -d "$WAL_DIR" ]; then
        tar -czf "$WAL_BACKUP" -C "$WAL_DIR" .
        
        SIZE=$(du -h "$WAL_BACKUP" | cut -f1)
        log_info "WAL backup completed: $WAL_BACKUP ($SIZE)"
        echo "$WAL_BACKUP"
    else
        log_warn "WAL directory not found: $WAL_DIR"
    fi
}

# Redis backup
backup_redis() {
    log_info "Starting Redis backup..."
    
    BACKUP_FILE="$BACKUP_DIR/redis/redis_${TIMESTAMP}.rdb"
    
    # Trigger BGSAVE
    redis-cli -h "$REDIS_HOST" -p "$REDIS_PORT" BGSAVE
    
    # Wait for BGSAVE to complete
    sleep 2
    while [ "$(redis-cli -h "$REDIS_HOST" -p "$REDIS_PORT" LASTSAVE)" = "$(redis-cli -h "$REDIS_HOST" -p "$REDIS_PORT" LASTSAVE)" ]; do
        sleep 1
    done
    
    # Copy RDB file
    RDB_FILE="/var/lib/redis/dump.rdb"
    if [ -f "$RDB_FILE" ]; then
        cp "$RDB_FILE" "$BACKUP_FILE"
        gzip "$BACKUP_FILE"
        
        SIZE=$(du -h "$BACKUP_FILE.gz" | cut -f1)
        log_info "Redis backup completed: $BACKUP_FILE.gz ($SIZE)"
        echo "$BACKUP_FILE.gz"
    else
        log_warn "Redis RDB file not found: $RDB_FILE"
    fi
}

# Application files backup
backup_files() {
    log_info "Backing up application files..."
    
    BACKUP_FILE="$BACKUP_DIR/files/app_files_${TIMESTAMP}.tar.gz"
    
    # Backup critical files (excluding data and logs)
    tar -czf "$BACKUP_FILE" \
        --exclude='*.pyc' \
        --exclude='__pycache__' \
        --exclude='.git' \
        --exclude='node_modules' \
        --exclude='venv' \
        --exclude='*.log' \
        -C /workspaces/sales-agent \
        src/ \
        infra/ \
        docs/ \
        pyproject.toml \
        requirements.txt \
        docker-compose.yml \
        Dockerfile
    
    SIZE=$(du -h "$BACKUP_FILE" | cut -f1)
    log_info "Application files backup completed: $BACKUP_FILE ($SIZE)"
    echo "$BACKUP_FILE"
}

# Upload to cloud storage
upload_to_cloud() {
    local FILE=$1
    
    log_info "Uploading to cloud storage: $FILE"
    
    # Check if AWS CLI is available
    if command -v aws &> /dev/null; then
        aws s3 cp "$FILE" "$S3_BUCKET/$(basename $FILE)" --storage-class STANDARD_IA
        
        if [ $? -eq 0 ]; then
            log_info "Upload successful: $S3_BUCKET/$(basename $FILE)"
        else
            log_error "Upload failed!"
            exit 1
        fi
    elif command -v gsutil &> /dev/null; then
        # Google Cloud Storage
        gsutil cp "$FILE" "$S3_BUCKET/$(basename $FILE)"
        
        if [ $? -eq 0 ]; then
            log_info "Upload successful: $S3_BUCKET/$(basename $FILE)"
        else
            log_error "Upload failed!"
            exit 1
        fi
    else
        log_warn "No cloud CLI found (aws/gsutil). Skipping upload."
    fi
}

# Verify backup integrity
verify_backup() {
    local FILE=$1
    
    log_info "Verifying backup integrity: $FILE"
    
    # Check if file exists
    if [ ! -f "$FILE" ]; then
        log_error "Backup file not found: $FILE"
        return 1
    fi
    
    # Check if checksum file exists
    if [ -f "$FILE.sha256" ]; then
        sha256sum -c "$FILE.sha256"
        if [ $? -eq 0 ]; then
            log_info "Checksum verification passed"
        else
            log_error "Checksum verification failed!"
            return 1
        fi
    else
        log_warn "No checksum file found, skipping verification"
    fi
    
    # Try to decompress (basic integrity check)
    if [[ "$FILE" == *.gz ]]; then
        gzip -t "$FILE"
        if [ $? -eq 0 ]; then
            log_info "Compression integrity check passed"
        else
            log_error "File is corrupted (gzip test failed)"
            return 1
        fi
    fi
    
    return 0
}

# Cleanup old backups
cleanup_old_backups() {
    log_info "Cleaning up backups older than $RETENTION_DAYS days..."
    
    find "$BACKUP_DIR" -type f -mtime +$RETENTION_DAYS -print -delete
    
    log_info "Cleanup completed"
}

# Full backup
full_backup() {
    log_info "Starting full backup..."
    
    setup_backup_dirs
    
    # Backup all components
    POSTGRES_FILE=$(backup_postgres)
    REDIS_FILE=$(backup_redis)
    FILES_BACKUP=$(backup_files)
    
    # Verify backups
    verify_backup "$POSTGRES_FILE"
    verify_backup "$REDIS_FILE"
    verify_backup "$FILES_BACKUP"
    
    log_info "Full backup completed successfully"
    
    # Create manifest
    MANIFEST="$BACKUP_DIR/manifest_${TIMESTAMP}.txt"
    cat > "$MANIFEST" << EOF
Sales Agent Backup Manifest
Timestamp: $TIMESTAMP
Date: $DATE

PostgreSQL: $(basename $POSTGRES_FILE)
Redis: $(basename $REDIS_FILE)
Files: $(basename $FILES_BACKUP)

Total Size: $(du -sh $BACKUP_DIR | cut -f1)
EOF
    
    echo "$MANIFEST"
}

# Main
main() {
    if [ $# -eq 0 ]; then
        usage
    fi
    
    DO_FULL=false
    DO_DB=false
    DO_WAL=false
    DO_REDIS=false
    DO_FILES=false
    DO_UPLOAD=false
    DO_VERIFY=false
    DO_CLEANUP=false
    
    while [ $# -gt 0 ]; do
        case "$1" in
            --full)
                DO_FULL=true
                shift
                ;;
            --db)
                DO_DB=true
                shift
                ;;
            --wal)
                DO_WAL=true
                shift
                ;;
            --redis)
                DO_REDIS=true
                shift
                ;;
            --files)
                DO_FILES=true
                shift
                ;;
            --upload)
                DO_UPLOAD=true
                shift
                ;;
            --verify)
                DO_VERIFY=true
                shift
                ;;
            --cleanup)
                DO_CLEANUP=true
                shift
                ;;
            --help)
                usage
                ;;
            *)
                log_error "Unknown option: $1"
                usage
                ;;
        esac
    done
    
    # Execute requested operations
    if [ "$DO_FULL" = true ]; then
        MANIFEST=$(full_backup)
        
        if [ "$DO_UPLOAD" = true ]; then
            upload_to_cloud "$MANIFEST"
        fi
    fi
    
    if [ "$DO_DB" = true ]; then
        setup_backup_dirs
        BACKUP_FILE=$(backup_postgres)
        
        if [ "$DO_UPLOAD" = true ]; then
            upload_to_cloud "$BACKUP_FILE"
        fi
    fi
    
    if [ "$DO_WAL" = true ]; then
        setup_backup_dirs
        BACKUP_FILE=$(backup_wal)
        
        if [ "$DO_UPLOAD" = true ]; then
            upload_to_cloud "$BACKUP_FILE"
        fi
    fi
    
    if [ "$DO_REDIS" = true ]; then
        setup_backup_dirs
        BACKUP_FILE=$(backup_redis)
        
        if [ "$DO_UPLOAD" = true ]; then
            upload_to_cloud "$BACKUP_FILE"
        fi
    fi
    
    if [ "$DO_FILES" = true ]; then
        setup_backup_dirs
        BACKUP_FILE=$(backup_files)
        
        if [ "$DO_UPLOAD" = true ]; then
            upload_to_cloud "$BACKUP_FILE"
        fi
    fi
    
    if [ "$DO_CLEANUP" = true ]; then
        cleanup_old_backups
    fi
    
    log_info "All backup operations completed successfully"
}

# Run main
main "$@"
