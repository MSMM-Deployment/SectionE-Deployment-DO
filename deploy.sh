#!/bin/bash

# =================================================================
# Digital Ocean Droplet Deployment Script
# Section E Resume Parser & Database System
# =================================================================

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
APP_NAME="sectionE-parser"
APP_USER="appuser"
APP_DIR="/home/$APP_USER/SectionE-Parser"
SERVICE_NAME="sectionE-parser"
NGINX_SITE="sectionE-parser"

echo -e "${BLUE}==================================================================${NC}"
echo -e "${BLUE} Section E Parser - Digital Ocean Deployment Script${NC}"
echo -e "${BLUE}==================================================================${NC}"

# Check if running as root
if [ "$EUID" -eq 0 ]; then
    echo -e "${RED}❌ Do not run this script as root. Run as the app user.${NC}"
    exit 1
fi

# Function to print status
print_status() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Check prerequisites
check_prerequisites() {
    print_info "Checking prerequisites..."
    
    # Check if Python 3 is installed
    if ! command_exists python3; then
        print_error "Python 3 is not installed"
        exit 1
    fi
    
    # Check if git is installed
    if ! command_exists git; then
        print_error "Git is not installed"
        exit 1
    fi
    
    # Check if pip is installed
    if ! command_exists pip3; then
        print_error "pip3 is not installed"
        exit 1
    fi
    
    print_status "Prerequisites check passed"
}

# Update application code
update_code() {
    print_info "Updating application code..."
    
    cd "$APP_DIR"
    
    # Check if git repository exists
    if [ ! -d ".git" ]; then
        print_error "Not a git repository. Please clone the repository first."
        exit 1
    fi
    
    # Stash any local changes
    git stash push -m "Auto-stash before deployment $(date)"
    
    # Pull latest changes
    git pull origin main
    
    print_status "Code updated successfully"
}

# Update Python dependencies
update_dependencies() {
    print_info "Updating Python dependencies..."
    
    cd "$APP_DIR"
    
    # Activate virtual environment
    source venv/bin/activate
    
    # Update pip
    pip install --upgrade pip
    
    # Install/update requirements
    pip install -r requirements.txt
    
    print_status "Dependencies updated successfully"
}

# Run tests
run_tests() {
    print_info "Running application tests..."
    
    cd "$APP_DIR"
    source venv/bin/activate
    
    # Run verification script
    if [ -f "utils/verify_installation.py" ]; then
        python3 utils/verify_installation.py
        if [ $? -eq 0 ]; then
            print_status "Application tests passed"
        else
            print_warning "Some tests failed, but continuing deployment"
        fi
    else
        print_warning "No test script found, skipping tests"
    fi
}

# Restart application service
restart_service() {
    print_info "Restarting application service..."
    
    # Check if service exists
    if systemctl list-units --type=service | grep -q "$SERVICE_NAME"; then
        sudo systemctl restart "$SERVICE_NAME"
        
        # Wait a moment for service to start
        sleep 5
        
        # Check if service is running
        if systemctl is-active --quiet "$SERVICE_NAME"; then
            print_status "Service restarted successfully"
        else
            print_error "Service failed to start"
            sudo systemctl status "$SERVICE_NAME"
            exit 1
        fi
    else
        print_warning "Service $SERVICE_NAME not found. Please set up the service first."
        print_info "Manual start: python3 start_server.py"
    fi
}

# Check application health
check_health() {
    print_info "Checking application health..."
    
    # Wait for application to start
    sleep 10
    
    # Check health endpoint
    if command_exists curl; then
        if curl -f http://localhost:8000/health >/dev/null 2>&1; then
            print_status "Application is healthy"
        else
            print_error "Health check failed"
            print_info "Check logs: sudo journalctl -u $SERVICE_NAME -f"
            exit 1
        fi
    else
        print_warning "curl not available, skipping health check"
    fi
}

# Reload Nginx (if applicable)
reload_nginx() {
    print_info "Reloading Nginx configuration..."
    
    # Check if Nginx is installed and running
    if command_exists nginx && systemctl is-active --quiet nginx; then
        # Test Nginx configuration
        if sudo nginx -t >/dev/null 2>&1; then
            sudo systemctl reload nginx
            print_status "Nginx reloaded successfully"
        else
            print_error "Nginx configuration test failed"
            sudo nginx -t
        fi
    else
        print_warning "Nginx not running or not installed"
    fi
}

# Create backup
create_backup() {
    print_info "Creating backup..."
    
    BACKUP_DIR="/home/$APP_USER/backups"
    DATE=$(date +%Y%m%d_%H%M%S)
    
    mkdir -p "$BACKUP_DIR"
    
    # Create backup
    tar -czf "$BACKUP_DIR/app_backup_$DATE.tar.gz" -C "/home/$APP_USER" "SectionE-Parser" --exclude="SectionE-Parser/venv" --exclude="SectionE-Parser/.git"
    
    # Keep only last 5 backups
    ls -t "$BACKUP_DIR"/app_backup_*.tar.gz | tail -n +6 | xargs -r rm
    
    print_status "Backup created: app_backup_$DATE.tar.gz"
}

# Cleanup function
cleanup() {
    print_info "Cleaning up temporary files..."
    
    cd "$APP_DIR"
    
    # Remove Python cache files
    find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
    find . -name "*.pyc" -delete 2>/dev/null || true
    
    # Remove temporary files
    rm -rf temp_processing/* 2>/dev/null || true
    
    print_status "Cleanup completed"
}

# Main deployment function
deploy() {
    echo -e "${BLUE}Starting deployment...${NC}"
    
    # Create backup before deployment
    create_backup
    
    # Run deployment steps
    check_prerequisites
    update_code
    update_dependencies
    run_tests
    restart_service
    check_health
    reload_nginx
    cleanup
    
    echo -e "${GREEN}==================================================================${NC}"
    echo -e "${GREEN}🎉 Deployment completed successfully!${NC}"
    echo -e "${GREEN}==================================================================${NC}"
    echo -e "${GREEN}Application is now running at:${NC}"
    echo -e "${GREEN}  - Local: http://localhost:8000${NC}"
    if [ -n "$DOMAIN" ]; then
        echo -e "${GREEN}  - Domain: https://$DOMAIN${NC}"
    fi
    echo -e "${GREEN}==================================================================${NC}"
}

# Help function
show_help() {
    echo "Usage: $0 [OPTION]"
    echo ""
    echo "Digital Ocean deployment script for Section E Parser"
    echo ""
    echo "Options:"
    echo "  deploy    Run full deployment (default)"
    echo "  update    Update code and restart service only"
    echo "  test      Run tests only"
    echo "  backup    Create backup only"
    echo "  health    Check application health"
    echo "  help      Show this help message"
    echo ""
    echo "Examples:"
    echo "  ./deploy.sh                # Full deployment"
    echo "  ./deploy.sh update         # Quick update"
    echo "  ./deploy.sh test           # Run tests"
    echo "  ./deploy.sh health         # Health check"
}

# Parse command line arguments
case "${1:-deploy}" in
    "deploy")
        deploy
        ;;
    "update")
        print_info "Running quick update..."
        update_code
        restart_service
        check_health
        print_status "Update completed"
        ;;
    "test")
        run_tests
        ;;
    "backup")
        create_backup
        ;;
    "health")
        check_health
        ;;
    "help"|"-h"|"--help")
        show_help
        ;;
    *)
        print_error "Unknown option: $1"
        show_help
        exit 1
        ;;
esac 