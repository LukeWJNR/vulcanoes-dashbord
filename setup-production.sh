#!/bin/bash
# Setup script for Volcano Dashboard production environment
# This script will set up HTTPS, database backups, monitoring, and auto-restart policies

set -e

# Check if we're in Replit or similar cloud environment where root isn't available
if [ -d /home/runner ]; then
  echo "Detected Replit environment - proceeding without root check"
  REPLIT_ENV=true
elif [ "$EUID" -ne 0 ]; then
  echo "Please run as root or with sudo"
  exit 1
fi

echo "🌋 Setting up Volcano Dashboard production environment..."

# Variables
DOMAIN=""
EMAIL=""
INSTALL_NGINX=false
INSTALL_BACKUPS=false
INSTALL_MONITORING=false

# Parse command line arguments
while [[ $# -gt 0 ]]; do
  case "$1" in
    --domain=*)
      DOMAIN="${1#*=}"
      shift
      ;;
    --email=*)
      EMAIL="${1#*=}"
      shift
      ;;
    --nginx)
      INSTALL_NGINX=true
      shift
      ;;
    --backups)
      INSTALL_BACKUPS=true
      shift
      ;;
    --monitoring)
      INSTALL_MONITORING=true
      shift
      ;;
    --all)
      INSTALL_NGINX=true
      INSTALL_BACKUPS=true
      INSTALL_MONITORING=true
      shift
      ;;
    *)
      echo "Unknown option: $1"
      echo "Usage: $0 [--domain=yourdomain.com] [--email=your@email.com] [--nginx] [--backups] [--monitoring] [--all]"
      exit 1
      ;;
  esac
done

# Create necessary directories
mkdir -p logs
mkdir -p backups

# 1. Set up Nginx and HTTPS
if [ "$INSTALL_NGINX" = true ]; then
  if [ -z "$DOMAIN" ] || [ -z "$EMAIL" ]; then
    echo "Error: Domain and email are required for Nginx setup."
    echo "Usage: $0 --nginx --domain=yourdomain.com --email=your@email.com"
    exit 1
  fi
  
  echo "🔒 Setting up Nginx with HTTPS..."
  
  # Install Nginx if not already installed
  if ! command -v nginx &> /dev/null; then
    apt-get update
    apt-get install -y nginx
  fi
  
  # Copy Nginx configuration
  sed -i "s/your-domain.com/$DOMAIN/g" nginx/volcano-dashboard.conf
  cp nginx/volcano-dashboard.conf /etc/nginx/sites-available/
  
  # Enable the site
  ln -sf /etc/nginx/sites-available/volcano-dashboard.conf /etc/nginx/sites-enabled/
  
  # Set up SSL certificates
  ./nginx/setup-ssl.sh --domain "$DOMAIN" --email "$EMAIL"
  
  # Restart Nginx
  systemctl restart nginx
  
  echo "✅ Nginx with HTTPS has been set up successfully!"
fi

# 2. Set up database backups
if [ "$INSTALL_BACKUPS" = true ]; then
  echo "💾 Setting up database backups..."
  
  # Copy backup script
  cp scripts/backup-database.sh /usr/local/bin/
  chmod +x /usr/local/bin/backup-database.sh
  
  # Create backup directory
  mkdir -p /var/backups/volcano-dashboard
  
  # Set up cron job for daily backups
  echo "0 2 * * * root /usr/local/bin/backup-database.sh > /var/log/volcano-backup.log 2>&1" > /etc/cron.d/volcano-backup
  chmod 644 /etc/cron.d/volcano-backup
  
  echo "✅ Database backups have been set up successfully!"
fi

# 3. Set up system monitoring
if [ "$INSTALL_MONITORING" = true ]; then
  echo "📊 Setting up system monitoring..."
  
  # Install required packages
  apt-get update
  apt-get install -y curl mailutils
  
  # Copy monitoring script
  cp scripts/monitor-system.sh /usr/local/bin/
  chmod +x /usr/local/bin/monitor-system.sh
  
  # Set up systemd service
  cp scripts/volcano-monitor.service /etc/systemd/system/
  systemctl daemon-reload
  systemctl enable volcano-monitor.service
  systemctl start volcano-monitor.service
  
  echo "✅ System monitoring has been set up successfully!"
fi

# 4. Docker auto-restart is already configured in docker-compose.yml

# If in Replit environment, skip Docker commands
if [ "$REPLIT_ENV" = true ]; then
  echo "🔨 Replit environment detected, skipping Docker container management..."
  echo "🔄 Production enhancements have been prepared for deployment on a real server"
  echo "💡 These configurations will not work directly in Replit but are ready for export"
else
  # Build and start the Docker containers
  echo "🔨 Building and starting Docker containers with auto-restart policies..."
  docker-compose down
  docker-compose build --no-cache
  docker-compose up -d
fi

echo "✨ Volcano Dashboard production environment setup has been completed successfully!"
echo "📊 The dashboard is now available at:"
if [ "$INSTALL_NGINX" = true ]; then
  echo "  🔒 https://$DOMAIN (secure with HTTPS)"
else
  echo "  http://localhost:5000"
fi