#!/bin/bash
#
# Arakis VM Setup Script
# Ubuntu 22.04 LTS
#
# This script sets up a production VM for Arakis with:
# - Docker and Docker Compose
# - Nginx reverse proxy
# - UFW firewall
# - Certbot for SSL/TLS
# - System optimizations
#
# Usage: sudo bash setup_vm.sh <domain> <email> [repo-url]
#

set -e  # Exit on error
set -u  # Exit on undefined variable

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
DOMAIN="${1:-}"
EMAIL="${2:-}"
REPO_URL="${3:-https://github.com/mustafa-boorenie/arakis.git}"
INSTALL_DIR="/opt/arakis"
USER="arakis"

# Functions
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

check_root() {
    if [ "$EUID" -ne 0 ]; then
        log_error "Please run as root (use sudo)"
        exit 1
    fi
}

check_args() {
    if [ -z "$DOMAIN" ] || [ -z "$EMAIL" ]; then
        log_error "Usage: sudo bash setup_vm.sh <domain> <email> [repo-url]"
        log_error "Example: sudo bash setup_vm.sh arakis.example.com admin@example.com"
        exit 1
    fi
}

update_system() {
    log_info "Updating system packages..."
    apt-get update
    apt-get upgrade -y
    apt-get install -y \
        curl \
        wget \
        git \
        vim \
        htop \
        ufw \
        ca-certificates \
        gnupg \
        lsb-release
}

install_docker() {
    log_info "Installing Docker..."

    # Add Docker's official GPG key
    install -m 0755 -d /etc/apt/keyrings
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
    chmod a+r /etc/apt/keyrings/docker.gpg

    # Add Docker repository
    echo \
        "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
        $(lsb_release -cs) stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null

    # Install Docker
    apt-get update
    apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

    # Start and enable Docker
    systemctl start docker
    systemctl enable docker

    log_info "Docker installed: $(docker --version)"
}

install_nginx() {
    log_info "Installing Nginx..."
    apt-get install -y nginx
    systemctl start nginx
    systemctl enable nginx
    log_info "Nginx installed: $(nginx -v 2>&1)"
}

install_certbot() {
    log_info "Installing Certbot for SSL..."
    apt-get install -y certbot python3-certbot-nginx
    log_info "Certbot installed: $(certbot --version)"
}

configure_firewall() {
    log_info "Configuring UFW firewall..."

    # Reset UFW to default
    ufw --force reset

    # Default policies
    ufw default deny incoming
    ufw default allow outgoing

    # Allow SSH (IMPORTANT: Don't lock yourself out!)
    ufw allow ssh
    ufw allow 22/tcp

    # Allow HTTP and HTTPS
    ufw allow 80/tcp
    ufw allow 443/tcp

    # Enable firewall
    ufw --force enable

    log_info "Firewall configured and enabled"
    ufw status verbose
}

create_user() {
    log_info "Creating application user: $USER..."

    if id "$USER" &>/dev/null; then
        log_warn "User $USER already exists"
    else
        useradd -m -s /bin/bash "$USER"
        usermod -aG docker "$USER"
        log_info "User $USER created and added to docker group"
    fi
}

setup_application() {
    log_info "Setting up Arakis application..."

    # Create installation directory
    mkdir -p "$INSTALL_DIR"

    # Clone or update repository
    if [ -d "$INSTALL_DIR/.git" ]; then
        log_info "Repository exists, pulling latest changes..."
        cd "$INSTALL_DIR"
        git pull origin main
    else
        log_info "Cloning repository from $REPO_URL..."
        git clone "$REPO_URL" "$INSTALL_DIR"
    fi

    # Set ownership
    chown -R "$USER:$USER" "$INSTALL_DIR"

    # Create .env file if it doesn't exist
    if [ ! -f "$INSTALL_DIR/.env" ]; then
        log_info "Creating .env file..."
        cp "$INSTALL_DIR/.env.example" "$INSTALL_DIR/.env"

        # Generate secure SECRET_KEY
        SECRET_KEY=$(openssl rand -hex 32)
        sed -i "s/SECRET_KEY=.*/SECRET_KEY=$SECRET_KEY/" "$INSTALL_DIR/.env"

        # Generate secure database password
        DB_PASSWORD=$(openssl rand -base64 32 | tr -d "=+/" | cut -c1-32)
        sed -i "s/POSTGRES_PASSWORD=.*/POSTGRES_PASSWORD=$DB_PASSWORD/" "$INSTALL_DIR/.env"

        # Update DATABASE_URL for Docker
        sed -i "s|DATABASE_URL=.*|DATABASE_URL=postgresql+asyncpg://arakis:$DB_PASSWORD@postgres:5432/arakis|" "$INSTALL_DIR/.env"

        # Set DEBUG to false
        sed -i "s/DEBUG=.*/DEBUG=false/" "$INSTALL_DIR/.env"

        log_warn "IMPORTANT: Edit $INSTALL_DIR/.env and add your OPENAI_API_KEY and other credentials!"
        log_warn "File permissions: 600 (owner read/write only)"
        chmod 600 "$INSTALL_DIR/.env"
    else
        log_info ".env file already exists"
    fi
}

configure_nginx() {
    log_info "Configuring Nginx reverse proxy..."

    # Copy nginx configuration
    cp "$INSTALL_DIR/deploy/nginx.conf" "/etc/nginx/sites-available/arakis"

    # Replace domain placeholder
    sed -i "s/your-domain.com/$DOMAIN/g" "/etc/nginx/sites-available/arakis"

    # Enable site
    ln -sf "/etc/nginx/sites-available/arakis" "/etc/nginx/sites-enabled/arakis"

    # Remove default site
    rm -f /etc/nginx/sites-enabled/default

    # Test configuration
    nginx -t

    # Reload nginx
    systemctl reload nginx

    log_info "Nginx configured for domain: $DOMAIN"
}

setup_ssl() {
    log_info "Setting up SSL certificate with Let's Encrypt..."

    # Obtain SSL certificate
    certbot --nginx \
        -d "$DOMAIN" \
        --non-interactive \
        --agree-tos \
        --email "$EMAIL" \
        --redirect

    # Setup auto-renewal
    systemctl enable certbot.timer
    systemctl start certbot.timer

    log_info "SSL certificate obtained and auto-renewal configured"
}

setup_systemd_service() {
    log_info "Setting up systemd service..."

    cp "$INSTALL_DIR/deploy/arakis.service" "/etc/systemd/system/arakis.service"

    # Update paths in service file
    sed -i "s|/opt/arakis|$INSTALL_DIR|g" "/etc/systemd/system/arakis.service"

    # Reload systemd
    systemctl daemon-reload

    # Enable service (don't start yet - need to configure .env first)
    systemctl enable arakis.service

    log_info "Systemd service configured"
}

setup_backup_cron() {
    log_info "Setting up automated backups..."

    # Make backup script executable
    chmod +x "$INSTALL_DIR/deploy/backup.sh"

    # Add cron job for daily backups at 2 AM
    CRON_JOB="0 2 * * * $INSTALL_DIR/deploy/backup.sh >> /var/log/arakis-backup.log 2>&1"

    # Add to root crontab (needs root for docker commands)
    (crontab -l 2>/dev/null | grep -v "arakis-backup"; echo "$CRON_JOB") | crontab -

    log_info "Backup cron job added (daily at 2 AM)"
}

optimize_system() {
    log_info "Applying system optimizations..."

    # Increase file descriptor limits for Docker
    cat >> /etc/security/limits.conf <<EOF

# Arakis Docker optimizations
* soft nofile 65536
* hard nofile 65536
EOF

    # Configure sysctl for better network performance
    cat >> /etc/sysctl.conf <<EOF

# Arakis optimizations
net.core.somaxconn = 1024
net.ipv4.tcp_max_syn_backlog = 2048
vm.swappiness = 10
EOF

    sysctl -p

    log_info "System optimizations applied"
}

print_next_steps() {
    log_info "=========================================="
    log_info "Arakis VM Setup Complete!"
    log_info "=========================================="
    echo ""
    log_warn "NEXT STEPS:"
    echo ""
    echo "1. Edit configuration file:"
    echo "   sudo nano $INSTALL_DIR/.env"
    echo "   - Add your OPENAI_API_KEY"
    echo "   - Add UNPAYWALL_EMAIL"
    echo "   - Review other settings"
    echo ""
    echo "2. Start the application:"
    echo "   sudo systemctl start arakis"
    echo ""
    echo "3. Check status:"
    echo "   sudo systemctl status arakis"
    echo "   docker ps"
    echo ""
    echo "4. View logs:"
    echo "   sudo journalctl -u arakis -f"
    echo "   docker logs -f arakis-api"
    echo ""
    echo "5. Access your application:"
    echo "   https://$DOMAIN"
    echo "   https://$DOMAIN/docs (API documentation)"
    echo ""
    echo "6. Run database migrations:"
    echo "   cd $INSTALL_DIR"
    echo "   docker-compose exec api alembic upgrade head"
    echo ""
    log_info "=========================================="
    echo ""
    log_warn "IMPORTANT FILES:"
    echo "  - Application: $INSTALL_DIR"
    echo "  - Environment: $INSTALL_DIR/.env (chmod 600)"
    echo "  - Nginx config: /etc/nginx/sites-available/arakis"
    echo "  - Systemd service: /etc/systemd/system/arakis.service"
    echo "  - SSL certificates: /etc/letsencrypt/live/$DOMAIN/"
    echo ""
    log_info "Backups will run daily at 2 AM to: /var/backups/arakis/"
}

# Main execution
main() {
    log_info "Starting Arakis VM setup..."
    log_info "Domain: $DOMAIN"
    log_info "Email: $EMAIL"
    log_info "Repository: $REPO_URL"
    echo ""

    check_root
    check_args

    update_system
    install_docker
    install_nginx
    install_certbot
    configure_firewall
    create_user
    setup_application
    configure_nginx
    setup_ssl
    setup_systemd_service
    setup_backup_cron
    optimize_system

    print_next_steps

    log_info "Setup complete! 🚀"
}

# Run main function
main "$@"
