#!/bin/bash
#
# Arakis Health Check Script
#
# Verifies all services are running correctly and reports status
# Can be used for monitoring, alerts, or pre-deployment validation
#
# Usage: ./health_check.sh [--verbose] [--json]
#

set -u  # Exit on undefined variable

# Configuration
INSTALL_DIR="/opt/arakis"
VERBOSE=false
JSON_OUTPUT=false

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --verbose|-v)
            VERBOSE=true
            shift
            ;;
        --json)
            JSON_OUTPUT=true
            shift
            ;;
        --help|-h)
            echo "Usage: $0 [--verbose] [--json]"
            echo "  --verbose  Show detailed output"
            echo "  --json     Output results in JSON format"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

# Colors (only if not JSON output)
if [ "$JSON_OUTPUT" = false ]; then
    RED='\033[0;31m'
    GREEN='\033[0;32m'
    YELLOW='\033[1;33m'
    NC='\033[0m'
else
    RED=''
    GREEN=''
    YELLOW=''
    NC=''
fi

# Results tracking
TOTAL_CHECKS=0
PASSED_CHECKS=0
FAILED_CHECKS=0
WARNINGS=0

# Health check results
declare -A RESULTS

log_check() {
    local name=$1
    local status=$2
    local message=$3

    TOTAL_CHECKS=$((TOTAL_CHECKS + 1))
    RESULTS["$name"]="$status|$message"

    if [ "$status" = "PASS" ]; then
        PASSED_CHECKS=$((PASSED_CHECKS + 1))
        if [ "$VERBOSE" = true ] && [ "$JSON_OUTPUT" = false ]; then
            echo -e "${GREEN}✓${NC} $name: $message"
        fi
    elif [ "$status" = "FAIL" ]; then
        FAILED_CHECKS=$((FAILED_CHECKS + 1))
        if [ "$JSON_OUTPUT" = false ]; then
            echo -e "${RED}✗${NC} $name: $message"
        fi
    elif [ "$status" = "WARN" ]; then
        WARNINGS=$((WARNINGS + 1))
        if [ "$JSON_OUTPUT" = false ]; then
            echo -e "${YELLOW}⚠${NC} $name: $message"
        fi
    fi
}

# Check Docker is running
check_docker() {
    if docker info > /dev/null 2>&1; then
        log_check "Docker" "PASS" "Docker daemon is running"
    else
        log_check "Docker" "FAIL" "Docker daemon is not running"
    fi
}

# Check Docker Compose is installed
check_docker_compose() {
    if docker compose version > /dev/null 2>&1; then
        local version=$(docker compose version --short 2>/dev/null || echo "unknown")
        log_check "Docker Compose" "PASS" "Version: $version"
    else
        log_check "Docker Compose" "FAIL" "Docker Compose not installed"
    fi
}

# Check containers are running
check_containers() {
    local containers=("arakis-api" "arakis-postgres" "arakis-redis" "arakis-minio")

    for container in "${containers[@]}"; do
        if docker ps --format '{{.Names}}' | grep -q "^${container}$"; then
            local status=$(docker inspect --format='{{.State.Status}}' "$container" 2>/dev/null)
            local health=$(docker inspect --format='{{.State.Health.Status}}' "$container" 2>/dev/null)

            if [ "$status" = "running" ]; then
                if [ "$health" = "healthy" ] || [ "$health" = "<no value>" ]; then
                    log_check "Container: $container" "PASS" "Running and healthy"
                elif [ "$health" = "starting" ]; then
                    log_check "Container: $container" "WARN" "Running but health check starting"
                else
                    log_check "Container: $container" "FAIL" "Running but unhealthy: $health"
                fi
            else
                log_check "Container: $container" "FAIL" "Not running (status: $status)"
            fi
        else
            log_check "Container: $container" "FAIL" "Container not found"
        fi
    done
}

# Check API endpoint
check_api_endpoint() {
    local response=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/health 2>/dev/null)

    if [ "$response" = "200" ]; then
        log_check "API Health Endpoint" "PASS" "HTTP 200 OK"
    elif [ -z "$response" ]; then
        log_check "API Health Endpoint" "FAIL" "No response (connection refused)"
    else
        log_check "API Health Endpoint" "FAIL" "HTTP $response"
    fi
}

# Check API response content
check_api_response() {
    local response=$(curl -s http://localhost:8000/health 2>/dev/null)

    if echo "$response" | grep -q '"status":"healthy"'; then
        log_check "API Response" "PASS" "Status: healthy"
    elif [ -z "$response" ]; then
        log_check "API Response" "FAIL" "No response"
    else
        log_check "API Response" "WARN" "Unexpected response: $response"
    fi
}

# Check database connectivity
check_database() {
    if docker compose -f "$INSTALL_DIR/docker-compose.yml" exec -T postgres pg_isready -U arakis > /dev/null 2>&1; then
        log_check "PostgreSQL" "PASS" "Database accepting connections"
    else
        log_check "PostgreSQL" "FAIL" "Database not accepting connections"
    fi
}

# Check Redis
check_redis() {
    local response=$(docker compose -f "$INSTALL_DIR/docker-compose.yml" exec -T redis redis-cli ping 2>/dev/null | tr -d '\r')

    if [ "$response" = "PONG" ]; then
        log_check "Redis" "PASS" "Redis responding to ping"
    else
        log_check "Redis" "FAIL" "Redis not responding (got: $response)"
    fi
}

# Check MinIO
check_minio() {
    local response=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:9000/minio/health/live 2>/dev/null)

    if [ "$response" = "200" ]; then
        log_check "MinIO" "PASS" "MinIO health check OK"
    else
        log_check "MinIO" "FAIL" "MinIO health check failed (HTTP $response)"
    fi
}

# Check Nginx (if running)
check_nginx() {
    if systemctl is-active --quiet nginx 2>/dev/null; then
        if nginx -t > /dev/null 2>&1; then
            log_check "Nginx" "PASS" "Nginx running with valid config"
        else
            log_check "Nginx" "WARN" "Nginx running but config has issues"
        fi
    else
        log_check "Nginx" "WARN" "Nginx not running (optional)"
    fi
}

# Check SSL certificate (if exists)
check_ssl() {
    local cert_dir="/etc/letsencrypt/live"

    if [ -d "$cert_dir" ] && [ "$(ls -A $cert_dir 2>/dev/null)" ]; then
        local domain=$(ls "$cert_dir" | head -n 1)
        local cert_file="$cert_dir/$domain/fullchain.pem"

        if [ -f "$cert_file" ]; then
            local expiry=$(openssl x509 -enddate -noout -in "$cert_file" 2>/dev/null | cut -d= -f2)
            local expiry_epoch=$(date -d "$expiry" +%s 2>/dev/null || echo 0)
            local now_epoch=$(date +%s)
            local days_left=$(( ($expiry_epoch - $now_epoch) / 86400 ))

            if [ $days_left -gt 30 ]; then
                log_check "SSL Certificate" "PASS" "Valid for $days_left days"
            elif [ $days_left -gt 0 ]; then
                log_check "SSL Certificate" "WARN" "Expires in $days_left days"
            else
                log_check "SSL Certificate" "FAIL" "Certificate expired"
            fi
        else
            log_check "SSL Certificate" "WARN" "Certificate file not found"
        fi
    else
        log_check "SSL Certificate" "WARN" "No SSL certificates found (optional)"
    fi
}

# Check disk space
check_disk_space() {
    local usage=$(df -h "$INSTALL_DIR" | awk 'NR==2 {print $5}' | sed 's/%//')

    if [ "$usage" -lt 80 ]; then
        log_check "Disk Space" "PASS" "Usage: ${usage}%"
    elif [ "$usage" -lt 90 ]; then
        log_check "Disk Space" "WARN" "Usage: ${usage}% (getting high)"
    else
        log_check "Disk Space" "FAIL" "Usage: ${usage}% (critical)"
    fi
}

# Check memory usage
check_memory() {
    local total=$(free -m | awk 'NR==2 {print $2}')
    local used=$(free -m | awk 'NR==2 {print $3}')
    local percent=$(( 100 * used / total ))

    if [ "$percent" -lt 80 ]; then
        log_check "Memory Usage" "PASS" "Usage: ${percent}% (${used}MB/${total}MB)"
    elif [ "$percent" -lt 90 ]; then
        log_check "Memory Usage" "WARN" "Usage: ${percent}% (${used}MB/${total}MB)"
    else
        log_check "Memory Usage" "FAIL" "Usage: ${percent}% (${used}MB/${total}MB) - critical"
    fi
}

# Check environment file
check_env_file() {
    if [ -f "$INSTALL_DIR/.env" ]; then
        # Check for required variables
        local required_vars=("OPENAI_API_KEY" "DATABASE_URL" "SECRET_KEY")
        local missing_vars=()

        for var in "${required_vars[@]}"; do
            if ! grep -q "^${var}=" "$INSTALL_DIR/.env" 2>/dev/null; then
                missing_vars+=("$var")
            fi
        done

        if [ ${#missing_vars[@]} -eq 0 ]; then
            log_check "Environment File" "PASS" "All required variables present"
        else
            log_check "Environment File" "WARN" "Missing variables: ${missing_vars[*]}"
        fi
    else
        log_check "Environment File" "FAIL" ".env file not found"
    fi
}

# Check systemd service (if exists)
check_systemd_service() {
    if systemctl is-enabled arakis > /dev/null 2>&1; then
        if systemctl is-active --quiet arakis; then
            log_check "Systemd Service" "PASS" "Service enabled and active"
        else
            log_check "Systemd Service" "WARN" "Service enabled but not active"
        fi
    else
        log_check "Systemd Service" "WARN" "Service not configured (optional)"
    fi
}

# Print results
print_results() {
    if [ "$JSON_OUTPUT" = true ]; then
        # JSON output
        echo "{"
        echo "  \"timestamp\": \"$(date -u +%Y-%m-%dT%H:%M:%SZ)\","
        echo "  \"summary\": {"
        echo "    \"total\": $TOTAL_CHECKS,"
        echo "    \"passed\": $PASSED_CHECKS,"
        echo "    \"failed\": $FAILED_CHECKS,"
        echo "    \"warnings\": $WARNINGS"
        echo "  },"
        echo "  \"checks\": {"

        local first=true
        for check in "${!RESULTS[@]}"; do
            if [ "$first" = true ]; then
                first=false
            else
                echo ","
            fi

            IFS='|' read -r status message <<< "${RESULTS[$check]}"
            echo -n "    \"$check\": {\"status\": \"$status\", \"message\": \"$message\"}"
        done

        echo ""
        echo "  }"
        echo "}"
    else
        # Human-readable output
        echo ""
        echo "=========================================="
        echo "Arakis Health Check Summary"
        echo "=========================================="
        echo "Total checks: $TOTAL_CHECKS"
        echo -e "${GREEN}Passed: $PASSED_CHECKS${NC}"
        echo -e "${RED}Failed: $FAILED_CHECKS${NC}"
        echo -e "${YELLOW}Warnings: $WARNINGS${NC}"
        echo "=========================================="

        if [ $FAILED_CHECKS -eq 0 ]; then
            echo -e "${GREEN}✓ All critical checks passed${NC}"
        else
            echo -e "${RED}✗ Some checks failed - review above${NC}"
        fi
    fi
}

# Main execution
main() {
    if [ "$JSON_OUTPUT" = false ]; then
        echo "Running Arakis health checks..."
        echo ""
    fi

    # Change to install directory if it exists
    if [ -d "$INSTALL_DIR" ]; then
        cd "$INSTALL_DIR"
    fi

    # Run all checks
    check_docker
    check_docker_compose
    check_containers
    check_api_endpoint
    check_api_response
    check_database
    check_redis
    check_minio
    check_nginx
    check_ssl
    check_disk_space
    check_memory
    check_env_file
    check_systemd_service

    # Print results
    print_results

    # Exit code based on failures
    if [ $FAILED_CHECKS -eq 0 ]; then
        exit 0
    else
        exit 1
    fi
}

# Run main
main "$@"
