#!/bin/bash
# Deployment script for Volcano Dashboard
set -e  # Exit immediately if a command exits with a non-zero status

# Check if we're in Replit or similar cloud environment where root isn't available
if [ -d /home/runner ]; then
  echo "Detected Replit environment - proceeding without root check"
  REPLIT_ENV=true
elif [ "$EUID" -ne 0 ]; then
  echo "Please run as root or with sudo"
  exit 1
fi

# Check if .env file exists
if [ ! -f .env ]; then
  echo "Error: .env file not found. Please create it with required environment variables."
  exit 1
fi

echo "🌋 Deploying Volcano Dashboard..."

# Pull latest code if using git
if [ -d .git ] && [ -f .git/config ]; then
  # Check if 'origin' remote exists
  if git remote | grep -q "^origin$"; then
    echo "📥 Pulling latest code..."
    git pull origin main
  else
    echo "📝 Git repository exists but no 'origin' remote is configured. Skipping code pull."
  fi
else
  echo "📝 Not a git repository. Skipping code pull."
fi

# If in Replit environment, skip Docker commands
if [ "$REPLIT_ENV" = true ]; then
  echo "🔨 Replit environment detected, skipping Docker container management..."
  echo "🔄 Starting Streamlit application directly..."
  
  # Set permissions for data directories
  echo "🔒 Setting secure permissions..."
  chmod -R 755 ./data
  find ./data -type f -exec chmod 644 {} \;
  
  # Create a logs directory for consistency
  mkdir -p logs
  
  echo "✅ Setup completed for Replit environment!"
  echo "📊 The Volcano Dashboard is now available through the Replit workflow"
else
  # Build and start the Docker containers
  echo "🔨 Building and starting Docker containers..."
  docker-compose down
  docker-compose build --no-cache
  docker-compose up -d
  
  # Set permissions for data directories
  echo "🔒 Setting secure permissions..."
  chmod -R 755 ./data
  find ./data -type f -exec chmod 644 {} \;
  
  # Check if the application is running
  echo "🔍 Checking if application is running..."
  sleep 5
  if curl -s http://localhost:5000 > /dev/null; then
    echo "✅ Application is up and running on port 5000!"
  else
    echo "❌ Application failed to start. Check logs with: docker-compose logs"
    exit 1
  fi
fi

echo "✨ Deployment completed successfully!"
echo "📊 The Volcano Dashboard is now available at: http://localhost:5000"