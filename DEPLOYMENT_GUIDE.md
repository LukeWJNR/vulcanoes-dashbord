# Volcano Dashboard Deployment Guide

This guide provides step-by-step instructions for deploying the Volcano Monitoring Dashboard in a production environment using Docker. This containerized approach ensures security and prevents unauthorized code changes.

## Prerequisites

Before deploying, ensure you have:

- A Linux server with at least 2GB RAM and 1 CPU core
- Docker and Docker Compose installed
- Database credentials for PostgreSQL
- Twilio account for SMS alerts (if using early warning system)
- Root or sudo access to the server
- Domain name (for HTTPS setup, optional)

## Step 1: Server Preparation

Update your server and install Docker if not already installed:

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Docker and Docker Compose
sudo apt install -y docker.io docker-compose
sudo systemctl enable --now docker

# Verify Docker is running
sudo docker --version
sudo docker-compose --version
```

## Step 2: Copy Application Files

1. Obtain the application files:
   - Download the zip file OR
   - Clone from version control

2. Create a directory for the application:
   ```bash
   sudo mkdir -p /opt/volcano-dashboard
   sudo chown -R $(whoami):$(whoami) /opt/volcano-dashboard
   ```

3. Extract or copy files to this directory:
   ```bash
   # If using zip file:
   unzip volcano-dashboard.zip -d /opt/volcano-dashboard
   
   # If using git:
   git clone <repository-url> /opt/volcano-dashboard
   ```

## Step 3: Configure Environment Variables

1. Navigate to the application directory:
   ```bash
   cd /opt/volcano-dashboard
   ```

2. Create an environment file:
   ```bash
   cp .env.example .env
   ```

3. Edit the `.env` file with your credentials:
   ```bash
   nano .env
   ```
   
   Update all fields marked with `your_*_here` with your actual credentials.

## Step 4: Basic Deployment

For a basic deployment:

```bash
sudo ./deploy.sh
```

This will:
- Build the Docker container
- Configure permissions
- Start the application
- Verify it's running correctly

## Step 5: Production Enhancements (Optional but Recommended)

For a fully production-ready deployment with all security and reliability enhancements:

```bash
# For all enhancements:
sudo ./setup-production.sh --all --domain=yourdomain.com --email=your@email.com

# OR install specific enhancements:
sudo ./setup-production.sh --nginx --domain=yourdomain.com --email=your@email.com
sudo ./setup-production.sh --backups
sudo ./setup-production.sh --monitoring
```

This will set up:
1. **HTTPS with Nginx**: Secure access via HTTPS
2. **Automated Database Backups**: Daily backups with retention management
3. **System Monitoring**: CPU, memory, disk, and application monitoring with alerts
4. **Container Auto-Restart**: Automatic recovery from failures

## Step 6: Verify Deployment

1. Check if the application is running:
   ```bash
   sudo docker-compose ps
   ```
   
   You should see the `app` container running (and `watchtower` if using production enhancements).

2. Access the dashboard:
   - Basic deployment: `http://your-server-ip:5000`
   - With HTTPS: `https://yourdomain.com`

## Monitoring and Maintenance

### Checking Application Logs

```bash
sudo docker-compose logs -f app
```

### Checking Monitoring Status

```bash
sudo systemctl status volcano-monitor
sudo journalctl -u volcano-monitor
```

### Viewing Database Backups

```bash
ls -la /var/backups/volcano-dashboard
```

### Manually Running a Backup

```bash
sudo /usr/local/bin/backup-database.sh
```

## Troubleshooting

If the deployment fails:

1. Check container logs:
   ```bash
   sudo docker-compose logs
   ```

2. Ensure all environment variables are set correctly in `.env`

3. Verify network connectivity to the database

4. Check file permissions:
   ```bash
   sudo ls -la /opt/volcano-dashboard/data
   sudo ls -la /opt/volcano-dashboard/backups
   ```

5. If using HTTPS, check Nginx logs:
   ```bash
   sudo journalctl -u nginx
   sudo cat /var/log/nginx/error.log
   ```

## Updating the Application

When updates are available:

1. Navigate to the application directory:
   ```bash
   cd /opt/volcano-dashboard
   ```

2. Run the deployment script again:
   ```bash
   sudo ./deploy.sh
   ```

The Watchtower service (if installed) will also automatically check for container updates daily.

## Security Features

This deployment includes several security features:

- **Read-only container**: The application runs in a read-only filesystem
- **Environment variables**: Secrets are stored securely in environment variables
- **Non-root user**: The application runs as a non-privileged user
- **Resource limits**: CPU and memory constraints are applied
- **Health checks**: Automatic detection of application issues
- **Auto-restart**: Automatic recovery from failures
- **HTTPS encryption**: Secure communication with TLS (if enabled)
- **Security headers**: Protection against common web vulnerabilities
- **Regular backups**: Protection against data loss
- **System monitoring**: Early detection of resource issues