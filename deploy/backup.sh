#!/bin/bash
#
# Arakis Database Backup Script
#
# This script backs up PostgreSQL database and optionally uploads to S3
# Automatically rotates old backups
#
# Usage: ./backup.sh [--upload-s3] [--retention-days N]
#

set -e  # Exit on error
set -u  # Exit on undefined variable

# Configuration
BACKUP_DIR="/var/backups/arakis"
INSTALL_DIR="/opt/arakis"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="arakis_backup_${TIMESTAMP}.sql.gz"
RETENTION_DAYS=30  # Keep backups for 30 days by default
UPLOAD_S3=false

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --upload-s3)
            UPLOAD_S3=true
            shift
            ;;
        --retention-days)
            RETENTION_DAYS="$2"
            shift 2
            ;;
        *)
            echo "Unknown option: $1"
            echo "Usage: $0 [--upload-s3] [--retention-days N]"
            exit 1
            ;;
    esac
done

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log_info() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1"
}

log_error() {
    echo -e "${RED}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1"
}

# Create backup directory if it doesn't exist
mkdir -p "$BACKUP_DIR"

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    log_error "Docker is not running!"
    exit 1
fi

# Check if postgres container is running
if ! docker ps --format '{{.Names}}' | grep -q "arakis-postgres"; then
    log_error "PostgreSQL container is not running!"
    exit 1
fi

log_info "Starting database backup..."

# Perform backup
cd "$INSTALL_DIR"

# Get database credentials from .env
DB_PASSWORD=$(grep POSTGRES_PASSWORD .env | cut -d '=' -f2 | tr -d '"' | tr -d "'")

if [ -z "$DB_PASSWORD" ]; then
    log_error "Could not read POSTGRES_PASSWORD from .env"
    exit 1
fi

# Create backup using pg_dump
log_info "Dumping database..."
docker compose exec -T -e PGPASSWORD="$DB_PASSWORD" postgres pg_dump -U arakis -d arakis | gzip > "$BACKUP_DIR/$BACKUP_FILE"

# Check if backup was successful
if [ -f "$BACKUP_DIR/$BACKUP_FILE" ]; then
    BACKUP_SIZE=$(du -h "$BACKUP_DIR/$BACKUP_FILE" | cut -f1)
    log_info "Backup created: $BACKUP_FILE (size: $BACKUP_SIZE)"
else
    log_error "Backup failed!"
    exit 1
fi

# Verify backup integrity
log_info "Verifying backup integrity..."
if gunzip -t "$BACKUP_DIR/$BACKUP_FILE" 2>/dev/null; then
    log_info "Backup integrity verified ✓"
else
    log_error "Backup file is corrupted!"
    exit 1
fi

# Upload to S3 if requested
if [ "$UPLOAD_S3" = true ]; then
    log_info "Uploading to S3..."

    # Check if AWS CLI is installed
    if ! command -v aws &> /dev/null; then
        log_warn "AWS CLI not installed. Skipping S3 upload."
        log_warn "Install with: sudo apt-get install awscli"
    else
        # Get S3 bucket from .env
        S3_BUCKET=$(grep S3_BUCKET_NAME .env | cut -d '=' -f2 | tr -d '"' | tr -d "'")

        if [ -n "$S3_BUCKET" ]; then
            aws s3 cp "$BACKUP_DIR/$BACKUP_FILE" "s3://$S3_BUCKET/backups/$BACKUP_FILE"
            log_info "Uploaded to S3: s3://$S3_BUCKET/backups/$BACKUP_FILE"
        else
            log_warn "S3_BUCKET_NAME not found in .env. Skipping S3 upload."
        fi
    fi
fi

# Rotate old backups
log_info "Rotating old backups (keeping last $RETENTION_DAYS days)..."
find "$BACKUP_DIR" -name "arakis_backup_*.sql.gz" -type f -mtime +$RETENTION_DAYS -delete

REMAINING_BACKUPS=$(find "$BACKUP_DIR" -name "arakis_backup_*.sql.gz" -type f | wc -l)
log_info "Backups in $BACKUP_DIR: $REMAINING_BACKUPS"

# Backup Docker volumes (optional)
log_info "Backing up Docker volumes..."

# Create volume backup directory
VOLUME_BACKUP_DIR="$BACKUP_DIR/volumes_${TIMESTAMP}"
mkdir -p "$VOLUME_BACKUP_DIR"

# Backup Redis data
if docker ps --format '{{.Names}}' | grep -q "arakis-redis"; then
    log_info "Backing up Redis data..."
    docker compose exec -T redis redis-cli SAVE > /dev/null 2>&1 || true
    docker cp arakis-redis:/data/dump.rdb "$VOLUME_BACKUP_DIR/redis_dump.rdb" 2>/dev/null || log_warn "Redis backup skipped"
fi

# Backup MinIO data (if needed)
# Note: MinIO PDFs are large - consider separate backup strategy
# docker run --rm -v arakis_minio_data:/data -v $VOLUME_BACKUP_DIR:/backup alpine tar czf /backup/minio_data.tar.gz /data

# Compress volume backups
if [ -d "$VOLUME_BACKUP_DIR" ] && [ "$(ls -A $VOLUME_BACKUP_DIR)" ]; then
    cd "$BACKUP_DIR"
    tar czf "volumes_${TIMESTAMP}.tar.gz" "volumes_${TIMESTAMP}"
    rm -rf "$VOLUME_BACKUP_DIR"
    VOLUME_SIZE=$(du -h "volumes_${TIMESTAMP}.tar.gz" | cut -f1)
    log_info "Volume backup created: volumes_${TIMESTAMP}.tar.gz (size: $VOLUME_SIZE)"

    # Rotate old volume backups
    find "$BACKUP_DIR" -name "volumes_*.tar.gz" -type f -mtime +$RETENTION_DAYS -delete
fi

# Create backup manifest
MANIFEST_FILE="$BACKUP_DIR/backup_manifest_${TIMESTAMP}.txt"
cat > "$MANIFEST_FILE" <<EOF
Arakis Backup Manifest
======================
Timestamp: $(date)
Backup File: $BACKUP_FILE
Backup Size: $BACKUP_SIZE

Database Info:
$(docker compose -f $INSTALL_DIR/docker-compose.yml exec -T postgres psql -U arakis -d arakis -c "SELECT version();" 2>/dev/null || echo "N/A")

Table Count:
$(docker compose -f $INSTALL_DIR/docker-compose.yml exec -T postgres psql -U arakis -d arakis -c "SELECT count(*) FROM information_schema.tables WHERE table_schema = 'public';" 2>/dev/null || echo "N/A")

Docker Containers:
$(docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Image}}")

Disk Usage:
$(df -h $BACKUP_DIR)
EOF

log_info "Manifest created: $MANIFEST_FILE"

# Summary
log_info "=========================================="
log_info "Backup Complete!"
log_info "=========================================="
log_info "Database backup: $BACKUP_DIR/$BACKUP_FILE"
log_info "Backup size: $BACKUP_SIZE"
log_info "Total backups: $REMAINING_BACKUPS"
log_info "Retention: $RETENTION_DAYS days"
if [ "$UPLOAD_S3" = true ]; then
    log_info "S3 upload: Enabled"
fi
log_info "=========================================="

# Exit with success
exit 0
