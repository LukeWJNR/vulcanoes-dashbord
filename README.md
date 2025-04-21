# Volcano Monitoring Dashboard

A comprehensive Streamlit-based volcano monitoring dashboard that provides immersive geological insights through advanced data visualization, interactive exploration, and cutting-edge early warning technologies.

## Features

- Interactive global volcano map with real-time data
- Scientific 3D eruption visualizations
- Volcano animations showing magma chambers and eruption processes
- Early warning system with email and SMS alerts
- SAR data animations from COMET Volcano Portal
- Scientific paper analysis for volcanology research
- Anak Krakatau collapse case study
- Sound profiles of different volcano types
- Favorites and notes management

## Technology Stack

- **Framework**: Streamlit
- **Data Sources**: USGS, WOVOdat, Smithsonian GVP
- **Visualizations**: Folium, Plotly, Three.js
- **Alerting**: Twilio SMS system
- **Database**: PostgreSQL
- **Containerization**: Docker
- **Optional AI**: Anthropic Claude

## Deployment (Production)

The application is containerized using Docker for secure, consistent deployments. To deploy:

1. Clone the repository

2. Create an environment file:
   ```
   cp .env.example .env
   ```
   Edit `.env` with your database and Twilio credentials.

3. Run the deployment script:
   ```
   sudo ./deploy.sh
   ```

The script will:
- Pull the latest code (if using git)
- Build and start the Docker containers
- Set secure permissions for data directories
- Verify the application is running

Your application will be available at `http://localhost:5000`

### Production Enhancements

For a fully production-ready deployment with enhanced security and reliability:

```bash
# Install all production enhancements
sudo ./setup-production.sh --all --domain=yourdomain.com --email=your@email.com
```

This sets up:
- HTTPS with Nginx and Let's Encrypt
- Automated database backups with retention management
- System monitoring with alerts
- Container auto-restart policies

See `DEPLOYMENT_GUIDE.md` for complete details.

### Manual Deployment with Docker

If you prefer to deploy manually:

1. Build the Docker image:
   ```
   docker build -t volcano-dashboard .
   ```

2. Start the application with docker-compose:
   ```
   docker-compose up -d
   ```

3. Check logs if needed:
   ```
   docker-compose logs -f
   ```

## Security Features

The production deployment includes several security features:

- **Read-only filesystem**: The application container runs with a read-only filesystem
- **Limited write access**: Only specific volumes mounted for writing (logs)
- **Non-root user**: The application runs as a non-privileged user
- **Resource limits**: CPU and memory constraints are applied
- **Environment variables**: Secrets are stored in environment variables, not in code
- **Data directory permissions**: Strict filesystem permissions

## Development Setup

For local development:

1. Install Python 3.11+
2. Install dependencies:
   ```
   pip install -r requirements.txt
   ```
3. Set up PostgreSQL database
4. Create a `.env` file with required credentials
5. Run the application:
   ```
   streamlit run app.py
   ```

## Environment Variables

The following environment variables are required:

- `PGHOST`, `PGUSER`, `PGPASSWORD`, `PGDATABASE`, `PGPORT`: PostgreSQL connection details
- `DATABASE_URL`: PostgreSQL connection string
- `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, `TWILIO_PHONE_NUMBER`: For SMS alerts
- `ANTHROPIC_API_KEY`: Optional for AI features

## License

All rights reserved. This codebase is proprietary and not for distribution.