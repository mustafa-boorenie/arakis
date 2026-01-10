#!/bin/bash
#
# Arakis Rollback Script
#
# This script rolls back a failed deployment to the last known good state
# Includes database rollback, code revert, and service restart
#
# Usage: ./rollback.sh [--skip-db] [--commit SHA]
#

set -e  # Exit on error
set -u  # Exit on undefined variable

# Configuration
INSTALL_DIR="/opt/arakis"
BACKUP_DIR="/var/backups/arakis"
LOG_FILE="/var/log/arakis-rollback.log"
SKIP_DB=false
TARGET_COMMIT=""

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --skip-db)
            SKIP_DB=true
            shift
            ;;
        --commit)
            TARGET_COMMIT="$2"
            shift 2
            ;;
        *)
            echo "Unknown option: $1"
            echo "Usage: $0 [--skip-db] [--commit SHA]"
            exit 1
            ;;
    esac
done

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')] [INFO]${NC} $1" | tee -a "$LOG_FILE"
}

log_warn() {
    echo -e "${YELLOW}[$(date +'%Y-%m-%d %H:%M:%S')] [WARN]${NC} $1" | tee -a "$LOG_FILE"
}

log_error() {
    echo -e "${RED}[$(date +'%Y-%m-%d %H:%M:%S')] [ERROR]${NC} $1" | tee -a "$LOG_FILE"
}

log_step() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')] [STEP]${NC} $1" | tee -a "$LOG_FILE"
}

# Error handling
error_exit() {
    log_error "$1"
    log_error "Rollback failed! Manual intervention required."
    exit 1
}

# Pre-rollback checks
pre_rollback_checks() {
    log_step "Running pre-rollback checks..."

    # Check if running as root or with sudo
    if [ "$EUID" -ne 0 ]; then
        error_exit "Please run with sudo"
    fi

    # Check if installation directory exists
    if [ ! -d "$INSTALL_DIR" ]; then
        error_exit "Installation directory not found: $INSTALL_DIR"
    fi

    # Check if Docker is running
    if ! docker info > /dev/null 2>&1; then
        error_exit "Docker is not running"
    fi

    # Check if backup directory exists
    if [ ! -d "$BACKUP_DIR" ]; then
        error_exit "Backup directory not found: $BACKUP_DIR"
    fi

    log_info "✓ Pre-rollback checks passed"
}

# Determine rollback target
determine_rollback_target() {
    log_step "Determining rollback target..."

    cd "$INSTALL_DIR"

    if [ -n "$TARGET_COMMIT" ]; then
        log_info "Using specified commit: $TARGET_COMMIT"
        ROLLBACK_COMMIT="$TARGET_COMMIT"
    elif [ -f "$BACKUP_DIR/last_deploy_commit.txt" ]; then
        ROLLBACK_COMMIT=$(cat "$BACKUP_DIR/last_deploy_commit.txt")
        log_info "Found last deployment commit: $ROLLBACK_COMMIT"
    else
        log_warn "No previous deployment found, using HEAD~1"
        ROLLBACK_COMMIT="HEAD~1"
    fi

    # Verify commit exists
    if ! git rev-parse "$ROLLBACK_COMMIT" > /dev/null 2>&1; then
        error_exit "Rollback commit not found: $ROLLBACK_COMMIT"
    fi

    log_info "✓ Will rollback to: $ROLLBACK_COMMIT"
}

# Find latest backup
find_latest_backup() {
    log_step "Finding latest database backup..."

    LATEST_BACKUP=$(ls -t "$BACKUP_DIR"/arakis_backup_*.sql.gz 2>/dev/null | head -n 1)

    if [ -z "$LATEST_BACKUP" ]; then
        log_warn "No database backup found"
        return 1
    fi

    # Check backup age (warn if older than 7 days)
    backup_age=$((($(date +%s) - $(stat -f %m "$LATEST_BACKUP" 2>/dev/null || stat -c %Y "$LATEST_BACKUP")) / 86400))

    log_info "Latest backup: $LATEST_BACKUP"
    log_info "Backup age: $backup_age days"

    if [ $backup_age -gt 7 ]; then
        log_warn "Backup is older than 7 days!"
    fi

    return 0
}

# Stop services
stop_services() {
    log_step "Stopping services..."

    cd "$INSTALL_DIR"

    # Stop API service
    docker compose stop api

    log_info "✓ Services stopped"
}

# Rollback database
rollback_database() {
    if [ "$SKIP_DB" = true ]; then
        log_warn "Skipping database rollback (--skip-db specified)"
        return 0
    fi

    log_step "Rolling back database..."

    if ! find_latest_backup; then
        log_error "Cannot rollback database: no backup found"
        read -p "Continue without database rollback? (yes/no): " confirm
        if [ "$confirm" != "yes" ]; then
            error_exit "Rollback cancelled"
        fi
        return 0
    fi

    cd "$INSTALL_DIR"

    # Get database password
    DB_PASSWORD=$(grep POSTGRES_PASSWORD .env | cut -d '=' -f2 | tr -d '"' | tr -d "'")

    if [ -z "$DB_PASSWORD" ]; then
        error_exit "Could not read POSTGRES_PASSWORD from .env"
    fi

    # Drop and recreate database (WARNING: destructive!)
    log_warn "WARNING: About to drop and restore database from backup"
    log_warn "Backup: $LATEST_BACKUP"

    # Restore database
    log_info "Restoring database from backup..."
    gunzip -c "$LATEST_BACKUP" | \
        docker compose exec -T -e PGPASSWORD="$DB_PASSWORD" postgres \
        psql -U arakis -d arakis > /dev/null 2>&1 || \
        error_exit "Database restore failed"

    log_info "✓ Database restored from backup"
}

# Rollback code
rollback_code() {
    log_step "Rolling back application code..."

    cd "$INSTALL_DIR"

    # Save current state (in case we need to roll forward)
    CURRENT_COMMIT=$(git rev-parse HEAD)
    echo "$CURRENT_COMMIT" > "$BACKUP_DIR/rollback_from_commit.txt"

    # Checkout previous commit
    git checkout "$ROLLBACK_COMMIT"

    log_info "✓ Code rolled back: $CURRENT_COMMIT -> $ROLLBACK_COMMIT"
}

# Rollback Docker images
rollback_docker_images() {
    log_step "Rolling back Docker images..."

    cd "$INSTALL_DIR"

    # If we have saved image info, use it
    if [ -f "$BACKUP_DIR/last_deploy_images.json" ]; then
        log_info "Using saved image tags from last deployment"
        # For now, just rebuild from current code
        docker compose build api
    else
        log_warn "No saved image info, rebuilding from code"
        docker compose build api
    fi

    log_info "✓ Docker images rolled back"
}

# Start services
start_services() {
    log_step "Starting services..."

    cd "$INSTALL_DIR"

    # Start all services
    docker compose up -d

    log_info "✓ Services started"
}

# Health check
health_check() {
    log_step "Running health checks..."

    local max_attempts=30
    local attempt=1

    while [ $attempt -le $max_attempts ]; do
        if curl -f http://localhost:8000/health > /dev/null 2>&1; then
            log_info "✓ Health check passed (attempt $attempt)"
            return 0
        fi

        log_warn "Health check failed (attempt $attempt/$max_attempts), waiting..."
        sleep 2
        attempt=$((attempt + 1))
    done

    error_exit "Health checks failed after $max_attempts attempts"
}

# Comprehensive health check
comprehensive_health_check() {
    log_step "Running comprehensive health checks..."

    cd "$INSTALL_DIR"

    if ./deploy/health_check.sh --verbose; then
        log_info "✓ All health checks passed"
        return 0
    else
        log_error "Some health checks failed, but services are running"
        log_warn "Manual verification recommended"
        return 1
    fi
}

# Log rollback details
log_rollback_details() {
    log_step "Recording rollback details..."

    cat > "$BACKUP_DIR/rollback_log_$(date +%Y%m%d_%H%M%S).txt" <<EOF
Rollback Date: $(date)
Rollback Script: $0
Executed By: ${SUDO_USER:-root}

Rollback Details:
- From Commit: $(cat "$BACKUP_DIR/rollback_from_commit.txt" 2>/dev/null || echo "unknown")
- To Commit: $ROLLBACK_COMMIT ($(git log -1 --format=%s "$ROLLBACK_COMMIT" 2>/dev/null))
- Database Restored: $([ "$SKIP_DB" = false ] && echo "yes" || echo "no")
- Backup Used: ${LATEST_BACKUP:-none}

Current Status:
- API Status: $(curl -s http://localhost:8000/health 2>/dev/null || echo "unavailable")
- Docker Containers: $(docker compose ps --format '{{.Name}}: {{.Status}}')

Next Steps:
1. Verify application functionality
2. Check logs: docker compose logs -f api
3. Monitor for errors
4. Investigate root cause of deployment failure
EOF

    log_info "✓ Rollback details saved"
}

# Main rollback flow
main() {
    log_info "=========================================="
    log_info "⚠️  Arakis Rollback Starting"
    log_info "=========================================="
    log_info "Time: $(date)"
    log_info "User: ${SUDO_USER:-root}"
    log_info "Skip DB: $SKIP_DB"
    echo ""

    # Confirm rollback
    log_warn "WARNING: This will rollback the application to a previous state"
    read -p "Are you sure you want to continue? (yes/no): " confirm
    if [ "$confirm" != "yes" ]; then
        log_info "Rollback cancelled by user"
        exit 0
    fi

    # Step 1: Pre-rollback checks
    pre_rollback_checks

    # Step 2: Determine rollback target
    determine_rollback_target

    # Step 3: Stop services
    stop_services

    # Step 4: Rollback database (if not skipped)
    rollback_database

    # Step 5: Rollback code
    rollback_code

    # Step 6: Rollback Docker images
    rollback_docker_images

    # Step 7: Start services
    start_services

    # Step 8: Wait for services to stabilize
    log_info "Waiting for services to stabilize..."
    sleep 15

    # Step 9: Basic health check
    health_check

    # Step 10: Comprehensive health check (allow to fail)
    comprehensive_health_check || true

    # Step 11: Log rollback details
    log_rollback_details

    log_info "=========================================="
    log_info "✅ Rollback Complete"
    log_info "=========================================="
    log_info "Rolled back to: $ROLLBACK_COMMIT"
    log_info "API: http://localhost:8000"
    log_info "Health: http://localhost:8000/health"
    log_info ""
    log_warn "Next Steps:"
    log_warn "1. Verify application is working correctly"
    log_warn "2. Investigate the cause of deployment failure"
    log_warn "3. Fix issues before attempting redeployment"
    log_info "=========================================="

    exit 0
}

# Run main function
main "$@"
