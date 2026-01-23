#!/bin/bash
# Restore Script for Sales Agent Platform

set -e

# Configuration
BACKUP_DIR="${BACKUP_DIR:-/var/backups/sales-agent}"
S3_BUCKET="${S3_BUCKET:-s3://sales-agent-backups}"
POSTGRES_HOST="${POSTGRES_HOST:-localhost}"
POSTGRES_DB="${POSTGRES_DB:-sales_agent}"
POSTGRES_USER="${POSTGRES_USER:-postgres}"
REDIS_HOST="${REDIS_HOST:-localhost}"

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

log_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }

usage() {
    cat << EOF
Usage: $0 [OPTIONS]

Restore script for Sales Agent platform.

OPTIONS:
    --db postgres          Restore PostgreSQL database
    --db redis             Restore Redis data
    --backup FILENAME      Specific backup file to restore
    --backup latest        Use latest backup
    --pitr "TIME"          Point-in-time recovery (e.g., "1 hour ago")
    --list-backups         List available backups
    --download-from-cloud  Download backup from S3/GCS first
    --dry-run              Show what would be restored without doing it
    --help                 Show this help

EXAMPLES:
    # Restore PostgreSQL from latest backup
    $0 --db postgres --backup latest

    # Point-in-time recovery (1 hour ago)
    $0 --db postgres --pitr "1 hour ago"

    # List available backups
    $0 --list-backups

    # Restore from cloud
    $0 --db postgres --backup latest --download-from-cloud

EOF
    exit 1
}

list_backups() {
    log_info "Available backups:"
    echo ""
    
    echo "PostgreSQL backups:"
    ls -lh "$BACKUP_DIR/postgres/" 2>/dev/null | tail -n +2 || echo "  None found"
    echo ""
    
    echo "Redis backups:"
    ls -lh "$BACKUP_DIR/redis/" 2>/dev/null | tail -n +2 || echo "  None found"
    echo ""
    
    echo "Application files:"
    ls -lh "$BACKUP_DIR/files/" 2>/dev/null | tail -n +2 || echo "  None found"
}

restore_postgres() {
    local BACKUP_FILE=$1
    
    log_info "Restoring PostgreSQL from: $BACKUP_FILE"
    
    # Verify backup exists
    if [ ! -f "$BACKUP_FILE" ]; then
        log_error "Backup file not found: $BACKUP_FILE"
        exit 1
    fi
    
    # Drop existing database (WARNING: destructive)
    log_warn "This will DROP the existing database!"
    read -p "Continue? (yes/no): " CONFIRM
    if [ "$CONFIRM" != "yes" ]; then
        log_info "Restore cancelled"
        exit 0
    fi
    
    # Drop and recreate database
    psql -h "$POSTGRES_HOST" -U "$POSTGRES_USER" -c "DROP DATABASE IF EXISTS $POSTGRES_DB;"
    psql -h "$POSTGRES_HOST" -U "$POSTGRES_USER" -c "CREATE DATABASE $POSTGRES_DB;"
    
    # Restore backup
    pg_restore -h "$POSTGRES_HOST" \
               -U "$POSTGRES_USER" \
               -d "$POSTGRES_DB" \
               --verbose \
               "$BACKUP_FILE"
    
    if [ $? -eq 0 ]; then
        log_info "PostgreSQL restore completed successfully"
    else
        log_error "PostgreSQL restore failed!"
        exit 1
    fi
}

restore_redis() {
    local BACKUP_FILE=$1
    
    log_info "Restoring Redis from: $BACKUP_FILE"
    
    # Stop Redis
    log_info "Stopping Redis..."
    systemctl stop redis || docker-compose stop redis
    
    # Copy RDB file
    cp "$BACKUP_FILE" /var/lib/redis/dump.rdb
    
    # Start Redis
    log_info "Starting Redis..."
    systemctl start redis || docker-compose start redis
    
    log_info "Redis restore completed"
}

download_from_cloud() {
    local FILENAME=$1
    local LOCAL_PATH=$2
    
    log_info "Downloading from cloud: $FILENAME"
    
    if command -v aws &> /dev/null; then
        aws s3 cp "$S3_BUCKET/$FILENAME" "$LOCAL_PATH"
    elif command -v gsutil &> /dev/null; then
        gsutil cp "$S3_BUCKET/$FILENAME" "$LOCAL_PATH"
    else
        log_error "No cloud CLI found (aws/gsutil)"
        exit 1
    fi
}

main() {
    if [ $# -eq 0 ]; then
        usage
    fi
    
    DB_TYPE=""
    BACKUP_FILE=""
    DO_DOWNLOAD=false
    DRY_RUN=false
    
    while [ $# -gt 0 ]; do
        case "$1" in
            --db)
                DB_TYPE=$2
                shift 2
                ;;
            --backup)
                BACKUP_FILE=$2
                shift 2
                ;;
            --list-backups)
                list_backups
                exit 0
                ;;
            --download-from-cloud)
                DO_DOWNLOAD=true
                shift
                ;;
            --dry-run)
                DRY_RUN=true
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
    
    # Find latest backup if requested
    if [ "$BACKUP_FILE" = "latest" ]; then
        if [ "$DB_TYPE" = "postgres" ]; then
            BACKUP_FILE=$(ls -t "$BACKUP_DIR/postgres/"*.sql.gz 2>/dev/null | head -1)
        elif [ "$DB_TYPE" = "redis" ]; then
            BACKUP_FILE=$(ls -t "$BACKUP_DIR/redis/"*.rdb.gz 2>/dev/null | head -1)
        fi
        
        if [ -z "$BACKUP_FILE" ]; then
            log_error "No backups found for $DB_TYPE"
            exit 1
        fi
        
        log_info "Using latest backup: $BACKUP_FILE"
    fi
    
    # Restore
    if [ "$DRY_RUN" = true ]; then
        log_info "DRY RUN: Would restore $DB_TYPE from $BACKUP_FILE"
        exit 0
    fi
    
    case "$DB_TYPE" in
        postgres)
            restore_postgres "$BACKUP_FILE"
            ;;
        redis)
            restore_redis "$BACKUP_FILE"
            ;;
        *)
            log_error "Unknown database type: $DB_TYPE"
            usage
            ;;
    esac
}

main "$@"
