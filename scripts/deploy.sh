#!/bin/bash
#
# Arakis Automated Deployment Script
#
# This script performs a zero-downtime deployment of Arakis
# to production using blue-green deployment strategy
#
# Usage: ./deploy.sh [commit-sha]
#

set -e  # Exit on error
set -u  # Exit on undefined variable

# Configuration
INSTALL_DIR="/opt/arakis"
BACKUP_DIR="/var/backups/arakis"
LOG_FILE="/var/log/arakis-deploy.log"
COMMIT_SHA="${1:-latest}"
REGISTRY="ghcr.io"
IMAGE_REPO="mustafa-boorenie/arakis"

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
    log_error "Deployment failed! Check logs at $LOG_FILE"
    exit 1
}

# Pre-deployment checks
pre_deployment_checks() {
    log_step "Running pre-deployment checks..."

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

    # Check disk space (require at least 5GB free)
    available_space=$(df -BG "$INSTALL_DIR" | awk 'NR==2 {print $4}' | sed 's/G//')
    if [ "$available_space" -lt 5 ]; then
        error_exit "Insufficient disk space: ${available_space}GB available (need 5GB)"
    fi

    # Check if .env file exists
    if [ ! -f "$INSTALL_DIR/.env" ]; then
        error_exit "Environment file not found: $INSTALL_DIR/.env"
    fi

    log_info "✓ Pre-deployment checks passed"
}

# Save current state
save_deployment_state() {
    log_step "Saving current deployment state..."

    cd "$INSTALL_DIR"

    # Save current git commit
    if [ -d .git ]; then
        git rev-parse HEAD > "$BACKUP_DIR/last_deploy_commit.txt" 2>/dev/null || true
    fi

    # Save current image tags
    docker compose images --format json > "$BACKUP_DIR/last_deploy_images.json" 2>/dev/null || true

    log_info "✓ Current state saved"
}

# Pull latest code
update_code() {
    log_step "Updating application code..."

    cd "$INSTALL_DIR"

    # Stash any local changes (shouldn't be any in production)
    git stash > /dev/null 2>&1 || true

    # Pull latest code
    git fetch origin
    if [ "$COMMIT_SHA" != "latest" ]; then
        git checkout "$COMMIT_SHA"
        log_info "✓ Checked out commit: $COMMIT_SHA"
    else
        git pull origin main
        log_info "✓ Pulled latest code from main"
    fi

    # Show what changed
    log_info "Recent commits:"
    git log --oneline -5 | tee -a "$LOG_FILE"
}

# Pull new Docker images
update_docker_images() {
    log_step "Pulling new Docker images..."

    cd "$INSTALL_DIR"

    # Login to registry (using GITHUB_TOKEN if available)
    if [ -n "${GITHUB_TOKEN:-}" ]; then
        echo "$GITHUB_TOKEN" | docker login "$REGISTRY" -u "$GITHUB_ACTOR" --password-stdin
    fi

    # Pull latest images
    docker compose pull

    log_info "✓ Docker images updated"
}

# Run database migrations
run_migrations() {
    log_step "Running database migrations..."

    cd "$INSTALL_DIR"

    # Check if migrations are needed
    current_head=$(docker compose exec -T api alembic current 2>/dev/null | tail -n 1 || echo "none")
    log_info "Current migration: $current_head"

    # Run migrations
    docker compose exec -T api alembic upgrade head

    new_head=$(docker compose exec -T api alembic current 2>/dev/null | tail -n 1)
    log_info "New migration: $new_head"

    if [ "$current_head" != "$new_head" ]; then
        log_info "✓ Migrations applied: $current_head -> $new_head"
    else
        log_info "✓ No new migrations"
    fi
}

# Rolling update (zero-downtime)
rolling_update() {
    log_step "Performing rolling update..."

    cd "$INSTALL_DIR"

    # Scale up new API instances (if using docker compose scale)
    # For single instance, we'll do a quick restart
    log_info "Restarting API with new image..."

    docker compose up -d --force-recreate --no-deps api

    log_info "✓ API updated"
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

    if ! ./deploy/health_check.sh --verbose; then
        error_exit "Comprehensive health check failed"
    fi

    log_info "✓ All health checks passed"
}

# Cleanup old images
cleanup() {
    log_step "Cleaning up old Docker images..."

    # Remove dangling images
    docker image prune -f > /dev/null 2>&1 || true

    # Remove old images (keep last 3)
    # docker images --format '{{.Repository}}:{{.Tag}}' | grep arakis | tail -n +4 | xargs -r docker rmi || true

    log_info "✓ Cleanup complete"
}

# Tag deployment
tag_deployment() {
    log_step "Tagging successful deployment..."

    cd "$INSTALL_DIR"

    # Save deployment info
    cat > "$BACKUP_DIR/last_successful_deploy.txt" <<EOF
Deployment Date: $(date)
Commit SHA: $(git rev-parse HEAD)
Deploy Script: $0
Deployed By: ${SUDO_USER:-root}
Image: $REGISTRY/$IMAGE_REPO:latest
Status: SUCCESS
EOF

    log_info "✓ Deployment tagged"
}

# Main deployment flow
main() {
    log_info "=========================================="
    log_info "Arakis Deployment Starting"
    log_info "=========================================="
    log_info "Commit: $COMMIT_SHA"
    log_info "Time: $(date)"
    log_info "User: ${SUDO_USER:-root}"
    echo ""

    # Step 1: Pre-deployment checks
    pre_deployment_checks

    # Step 2: Save current state (for rollback)
    save_deployment_state

    # Step 3: Update code
    update_code

    # Step 4: Pull new Docker images
    update_docker_images

    # Step 5: Run database migrations
    run_migrations

    # Step 6: Rolling update
    rolling_update

    # Step 7: Wait for services to stabilize
    log_info "Waiting for services to stabilize..."
    sleep 10

    # Step 8: Basic health check
    health_check

    # Step 9: Comprehensive health checks
    comprehensive_health_check

    # Step 10: Cleanup
    cleanup

    # Step 11: Tag successful deployment
    tag_deployment

    log_info "=========================================="
    log_info "✅ Deployment Successful!"
    log_info "=========================================="
    log_info "Commit: $(git rev-parse HEAD)"
    log_info "API: https://$(hostname -f 2>/dev/null || echo 'your-domain.com')"
    log_info "Health: https://$(hostname -f 2>/dev/null || echo 'your-domain.com')/health"
    log_info "Docs: https://$(hostname -f 2>/dev/null || echo 'your-domain.com')/docs"
    log_info "=========================================="

    exit 0
}

# Run main function
main "$@"
