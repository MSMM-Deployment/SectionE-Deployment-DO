# Digital Ocean Deployment Guide
# Section E Resume Parser & Database System

Complete deployment guide for deploying the Section E Resume Parser application to Digital Ocean platform.

## 📋 Table of Contents

- [Overview](#overview)
- [Prerequisites](#prerequisites)
- [Deployment Methods](#deployment-methods)
- [Method 1: Digital Ocean Droplet (VM)](#method-1-digital-ocean-droplet-vm)
- [Method 2: Digital Ocean App Platform](#method-2-digital-ocean-app-platform)
- [Environment Configuration](#environment-configuration)
- [Domain & SSL Setup](#domain--ssl-setup)
- [Production Optimization](#production-optimization)
- [Monitoring & Maintenance](#monitoring--maintenance)
- [Troubleshooting](#troubleshooting)

## 🎯 Overview

This application is a **Python-based web application** with the following architecture:
- **Backend**: Python HTTP server (`src/web/serve_ui.py`) on port 8000
- **Frontend**: Static HTML/CSS/JS with modern authentication system
- **Database**: Supabase (PostgreSQL) - External service
- **AI Integration**: OpenAI GPT-4 API for document parsing
- **Document Processing**: PDF and Word document processing with system dependencies

## 🔧 Prerequisites

### Required Accounts & Services
1. **Digital Ocean Account** - For hosting infrastructure
2. **Supabase Account** - For PostgreSQL database (free tier available)
3. **OpenAI Account** - For GPT-4 API access
4. **Domain Name** (optional but recommended for production)

### Required Environment Variables
```bash
# Core Application
PORT=8000                          # Application port (configurable)

# Database Configuration
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your_supabase_anon_key

# AI Services
OPENAI_API_KEY=sk-your-openai-api-key

# Optional: Advanced Configuration
NODE_ENV=production
PYTHON_ENV=production
```

## 🚀 Deployment Methods

### Method 1: Digital Ocean Droplet (VM) - Recommended for Full Control

**Best for**: Complete control over environment, system dependencies, and custom configurations.

#### Step 1: Create Digital Ocean Droplet

1. **Login to Digital Ocean Console**
   - Go to [cloud.digitalocean.com](https://cloud.digitalocean.com)
   - Click "Create" → "Droplet"

2. **Configure Droplet**
   ```
   Image: Ubuntu 22.04 LTS
   Plan: Basic ($12/month minimum recommended)
   CPU: 2 vCPUs, 2GB RAM, 50GB SSD
   Region: Choose closest to your users
   Authentication: SSH Key (recommended) or Password
   Hostname: sectionE-parser-app
   Tags: production, sectionE-parser
   ```

3. **Create Droplet** and note the IP address

#### Step 2: Initial Server Setup

1. **Connect to Droplet**
   ```bash
   ssh root@YOUR_DROPLET_IP
   ```

2. **Update System**
   ```bash
   apt update && apt upgrade -y
   ```

3. **Create Application User**
   ```bash
   adduser --disabled-password --gecos "" appuser
   usermod -aG sudo appuser
   su - appuser
   ```

4. **Install System Dependencies**
   ```bash
   # Python and essential build tools
   sudo apt install -y python3 python3-pip python3-venv git curl wget
   
   # System dependencies for document processing
   sudo apt install -y antiword
   
   # Optional: Additional text processing tools
   sudo apt install -y poppler-utils
   
   # Nginx for reverse proxy (recommended)
   sudo apt install -y nginx
   
   # Process management
   sudo apt install -y supervisor
   
   # Security tools
   sudo apt install -y ufw fail2ban
   ```

#### Step 3: Deploy Application

1. **Clone Repository**
   ```bash
   cd /home/appuser
   git clone https://github.com/your-username/SectionE-Parser.git
   cd SectionE-Parser
   ```

2. **Setup Python Environment**
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   pip install --upgrade pip
   pip install -r requirements.txt
   ```

3. **Create Environment File**
   ```bash
   cp .env.example .env
   nano .env
   ```
   
   Add your configuration:
   ```bash
   PORT=8000
   SUPABASE_URL=https://your-project.supabase.co
   SUPABASE_KEY=your_supabase_anon_key
   OPENAI_API_KEY=sk-your-openai-api-key
   NODE_ENV=production
   PYTHON_ENV=production
   ```

4. **Test Application**
   ```bash
   # Verify installation
   python3 utils/verify_installation.py
   
   # Test server start
   python3 start_server.py
   ```
   
   Access `http://YOUR_DROPLET_IP:8000` to verify it's working.

#### Step 4: Production Configuration

1. **Create Systemd Service**
   ```bash
   sudo nano /etc/systemd/system/sectionE-parser.service
   ```
   
   Add service configuration:
   ```ini
   [Unit]
   Description=Section E Parser Web Application
   After=network.target
   
   [Service]
   Type=simple
   User=appuser
   Group=appuser
   WorkingDirectory=/home/appuser/SectionE-Parser
   Environment=PATH=/home/appuser/SectionE-Parser/venv/bin
   ExecStart=/home/appuser/SectionE-Parser/venv/bin/python start_server.py
   Restart=always
   RestartSec=10
   StandardOutput=syslog
   StandardError=syslog
   SyslogIdentifier=sectionE-parser
   
   [Install]
   WantedBy=multi-user.target
   ```

2. **Enable and Start Service**
   ```bash
   sudo systemctl daemon-reload
   sudo systemctl enable sectionE-parser
   sudo systemctl start sectionE-parser
   sudo systemctl status sectionE-parser
   ```

3. **Configure Nginx Reverse Proxy**
   ```bash
   sudo nano /etc/nginx/sites-available/sectionE-parser
   ```
   
   Add Nginx configuration:
   ```nginx
   server {
       listen 80;
       server_name YOUR_DOMAIN_OR_IP;
       
       client_max_body_size 10M;
       
       location / {
           proxy_pass http://localhost:8000;
           proxy_set_header Host $host;
           proxy_set_header X-Real-IP $remote_addr;
           proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
           proxy_set_header X-Forwarded-Proto $scheme;
           proxy_read_timeout 300;
           proxy_connect_timeout 300;
           proxy_send_timeout 300;
       }
       
       # Health check endpoint
       location /health {
           proxy_pass http://localhost:8000/health;
           access_log off;
       }
   }
   ```

4. **Enable Nginx Site**
   ```bash
   sudo ln -s /etc/nginx/sites-available/sectionE-parser /etc/nginx/sites-enabled/
   sudo nginx -t
   sudo systemctl reload nginx
   ```

#### Step 5: Security Configuration

1. **Configure Firewall**
   ```bash
   sudo ufw allow OpenSSH
   sudo ufw allow 'Nginx Full'
   sudo ufw --force enable
   ```

2. **Configure Fail2Ban**
   ```bash
   sudo nano /etc/fail2ban/jail.local
   ```
   
   Add:
   ```ini
   [DEFAULT]
   bantime = 3600
   findtime = 600
   maxretry = 3
   
   [nginx-http-auth]
   enabled = true
   
   [nginx-limit-req]
   enabled = true
   ```
   
   ```bash
   sudo systemctl enable fail2ban
   sudo systemctl start fail2ban
   ```

### Method 2: Digital Ocean App Platform - Easier Setup

**Best for**: Simplified deployment with managed infrastructure and automatic scaling.

#### Step 1: Prepare Repository

1. **Create `app.yaml` Configuration**
   ```yaml
   name: sectionE-parser
   services:
   - name: web
     source_dir: /
     github:
       repo: your-username/SectionE-Parser
       branch: main
     run_command: python start_server.py
     environment_slug: python
     instance_count: 1
     instance_size_slug: basic-xxs
     envs:
     - key: PORT
       value: "8080"
     - key: SUPABASE_URL
       value: "https://your-project.supabase.co"
       type: SECRET
     - key: SUPABASE_KEY
       type: SECRET
     - key: OPENAI_API_KEY
       type: SECRET
     - key: NODE_ENV
       value: "production"
     - key: PYTHON_ENV
       value: "production"
     http_port: 8080
   ```

2. **Create `requirements.txt`** (already exists)

3. **Create `runtime.txt`**
   ```
   python-3.9.16
   ```

4. **Create `Procfile`**
   ```
   web: python start_server.py
   ```

#### Step 2: Deploy to App Platform

1. **Create App from GitHub**
   - Go to Digital Ocean App Platform
   - Click "Create App"
   - Connect GitHub repository
   - Select branch: `main`

2. **Configure Environment Variables**
   - Set `SUPABASE_URL`, `SUPABASE_KEY`, `OPENAI_API_KEY` as encrypted variables
   - Set `PORT=8080` (App Platform requirement)

3. **Deploy Application**
   - Review configuration
   - Click "Create Resources"
   - Wait for deployment (5-10 minutes)

#### Step 3: Custom Domain (Optional)

1. **Add Domain in App Platform**
   - Go to Settings → Domains
   - Add your domain
   - Configure DNS records as instructed

## 🌐 Environment Configuration

### Database Setup (Supabase)

1. **Create Supabase Project**
   ```bash
   # Go to https://supabase.com
   # Create new project
   # Note the Project URL and API Keys
   ```

2. **Setup Database Schema**
   ```bash
   # Copy contents of sql/supabase_schema_simple.sql
   # Paste in Supabase SQL Editor
   # Execute to create tables and views
   ```

3. **Configure Environment Variables**
   ```bash
   SUPABASE_URL=https://your-project-id.supabase.co
   SUPABASE_KEY=your_anon_key_here
   ```

### OpenAI API Setup

1. **Get API Key**
   ```bash
   # Go to https://platform.openai.com/api-keys
   # Create new API key
   # Set usage limits if needed
   ```

2. **Add to Environment**
   ```bash
   OPENAI_API_KEY=sk-your-key-here
   ```

## 🔒 Domain & SSL Setup

### SSL Certificate (Free with Let's Encrypt)

1. **Install Certbot**
   ```bash
   sudo apt install -y certbot python3-certbot-nginx
   ```

2. **Get Certificate**
   ```bash
   sudo certbot --nginx -d yourdomain.com
   ```

3. **Auto-renewal**
   ```bash
   sudo systemctl enable certbot.timer
   ```

### DNS Configuration

Point your domain to the Digital Ocean Droplet:
```
Type: A Record
Name: @
Value: YOUR_DROPLET_IP
TTL: 300

Type: A Record  
Name: www
Value: YOUR_DROPLET_IP
TTL: 300
```

## ⚡ Production Optimization

### Performance Tuning

1. **Application Configuration**
   ```bash
   # In your .env file
   PYTHON_ENV=production
   NODE_ENV=production
   
   # Optimize Python
   export PYTHONOPTIMIZE=2
   export PYTHONDONTWRITEBYTECODE=1
   ```

2. **Nginx Optimization**
   ```nginx
   # Add to nginx configuration
   gzip on;
   gzip_types text/plain text/css application/json application/javascript;
   gzip_min_length 1000;
   
   # Security headers
   add_header X-Frame-Options DENY;
   add_header X-Content-Type-Options nosniff;
   add_header X-XSS-Protection "1; mode=block";
   ```

3. **Process Management**
   ```bash
   # For high traffic, consider multiple workers
   # Create systemd service with multiple instances
   ```

### Monitoring Setup

1. **Application Logs**
   ```bash
   # View application logs
   sudo journalctl -u sectionE-parser -f
   
   # View nginx logs
   sudo tail -f /var/log/nginx/access.log
   sudo tail -f /var/log/nginx/error.log
   ```

2. **System Monitoring**
   ```bash
   # Install monitoring tools
   sudo apt install -y htop iotop nethogs
   
   # Monitor resources
   htop
   ```

3. **Automated Backups**
   ```bash
   # Create backup script
   nano /home/appuser/backup.sh
   ```
   
   ```bash
   #!/bin/bash
   DATE=$(date +%Y%m%d_%H%M%S)
   BACKUP_DIR="/home/appuser/backups"
   
   mkdir -p $BACKUP_DIR
   
   # Backup application files
   tar -czf $BACKUP_DIR/app_$DATE.tar.gz /home/appuser/SectionE-Parser
   
   # Keep only last 7 days of backups
   find $BACKUP_DIR -name "app_*.tar.gz" -mtime +7 -delete
   ```
   
   ```bash
   chmod +x /home/appuser/backup.sh
   # Add to crontab for daily backup
   crontab -e
   # Add: 0 2 * * * /home/appuser/backup.sh
   ```

## 🔧 Build Commands Reference

### Local Development
```bash
# Setup local environment
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Start development server
python3 start_server.py

# Run tests
python3 tests/test_parser.py
python3 tests/test_docx_generator.py
```

### Production Build
```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install dependencies
sudo apt install -y python3 python3-pip python3-venv antiword nginx supervisor

# Setup application
git clone <repository>
cd SectionE-Parser
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with production values

# Test installation
python3 utils/verify_installation.py

# Setup systemd service (see configuration above)
sudo systemctl enable sectionE-parser
sudo systemctl start sectionE-parser
```

### Deployment Updates
```bash
# Pull latest changes
cd /home/appuser/SectionE-Parser
git pull origin main

# Update dependencies if needed
source venv/bin/activate
pip install -r requirements.txt

# Restart application
sudo systemctl restart sectionE-parser

# Check status
sudo systemctl status sectionE-parser
```

## 🔍 Monitoring & Maintenance

### Health Checks

1. **Application Health**
   ```bash
   # Check application status
   curl http://localhost:8000/health
   
   # Expected response:
   {"status": "healthy", "timestamp": "2024-01-09T10:30:00Z"}
   ```

2. **Service Status**
   ```bash
   sudo systemctl status sectionE-parser
   sudo systemctl status nginx
   ```

3. **Resource Usage**
   ```bash
   # Check disk usage
   df -h
   
   # Check memory usage
   free -h
   
   # Check process usage
   top
   ```

### Log Management

1. **Application Logs**
   ```bash
   # View recent logs
   sudo journalctl -u sectionE-parser --since "1 hour ago"
   
   # Follow logs in real-time
   sudo journalctl -u sectionE-parser -f
   ```

2. **Log Rotation**
   ```bash
   # Configure logrotate
   sudo nano /etc/logrotate.d/sectionE-parser
   ```
   
   ```
   /var/log/sectionE-parser/*.log {
       daily
       missingok
       rotate 30
       compress
       delaycompress
       copytruncate
   }
   ```

### Automated Monitoring

1. **Simple Uptime Monitor**
   ```bash
   nano /home/appuser/monitor.sh
   ```
   
   ```bash
   #!/bin/bash
   
   URL="http://localhost:8000/health"
   
   if ! curl -f $URL > /dev/null 2>&1; then
       echo "Application is down! Restarting..." | logger
       sudo systemctl restart sectionE-parser
   fi
   ```
   
   ```bash
   chmod +x /home/appuser/monitor.sh
   # Add to crontab: */5 * * * * /home/appuser/monitor.sh
   ```

## 🔧 Troubleshooting

### Common Issues

1. **Application Won't Start**
   ```bash
   # Check service status
   sudo systemctl status sectionE-parser
   
   # Check logs
   sudo journalctl -u sectionE-parser --since "10 minutes ago"
   
   # Common fixes:
   # - Check .env file exists and has correct values
   # - Verify Python virtual environment is activated
   # - Check file permissions
   ```

2. **Database Connection Issues**
   ```bash
   # Test Supabase connection
   python3 -c "
   import os
   from dotenv import load_dotenv
   from supabase import create_client
   
   load_dotenv()
   url = os.getenv('SUPABASE_URL')
   key = os.getenv('SUPABASE_KEY')
   
   print(f'URL: {url}')
   print(f'Key: {key[:20]}...')
   
   client = create_client(url, key)
   result = client.table('employees').select('*').limit(1).execute()
   print('Connection successful!')
   "
   ```

3. **High Memory Usage**
   ```bash
   # Check memory usage
   free -h
   
   # Restart application to clear memory
   sudo systemctl restart sectionE-parser
   
   # Consider upgrading droplet if consistently high
   ```

4. **SSL Certificate Issues**
   ```bash
   # Renew certificate manually
   sudo certbot renew
   
   # Check certificate status
   sudo certbot certificates
   
   # Test SSL configuration
   curl -I https://yourdomain.com
   ```

### Performance Issues

1. **Slow Response Times**
   ```bash
   # Check system resources
   htop
   
   # Check nginx access logs for slow requests
   sudo tail -f /var/log/nginx/access.log
   
   # Monitor database performance in Supabase dashboard
   ```

2. **File Processing Issues**
   ```bash
   # Check system dependencies
   which antiword
   which python3
   
   # Test file processing
   python3 utils/verify_installation.py
   ```

### Emergency Procedures

1. **Application Recovery**
   ```bash
   # Stop application
   sudo systemctl stop sectionE-parser
   
   # Restore from backup if needed
   cd /home/appuser
   tar -xzf backups/app_YYYYMMDD_HHMMSS.tar.gz
   
   # Restart application
   sudo systemctl start sectionE-parser
   ```

2. **Database Recovery**
   ```bash
   # Supabase handles backups automatically
   # Contact Supabase support for restore if needed
   # Always test database connection after issues
   ```

## 🎯 Advanced Configuration

### Environment-Specific Settings

1. **Development**
   ```bash
   NODE_ENV=development
   PYTHON_ENV=development
   DEBUG=true
   PORT=8000
   ```

2. **Staging**
   ```bash
   NODE_ENV=staging
   PYTHON_ENV=staging
   DEBUG=false
   PORT=8000
   ```

3. **Production**
   ```bash
   NODE_ENV=production
   PYTHON_ENV=production
   DEBUG=false
   PORT=8000
   ```

### Scaling Options

1. **Vertical Scaling** (Upgrade droplet)
   ```bash
   # In Digital Ocean console:
   # Droplet → Resize → Choose larger plan
   # Requires brief downtime
   ```

2. **Horizontal Scaling** (Multiple droplets + Load Balancer)
   ```bash
   # Create multiple droplets with same configuration
   # Add Digital Ocean Load Balancer
   # Configure health checks
   ```

3. **Database Scaling** (Supabase handles automatically)
   ```bash
   # Supabase scales automatically
   # Monitor usage in Supabase dashboard
   # Consider upgrading plan if needed
   ```

## 📞 Support & Resources

### Official Documentation
- [Digital Ocean Droplet Guide](https://docs.digitalocean.com/products/droplets/)
- [Digital Ocean App Platform](https://docs.digitalocean.com/products/app-platform/)
- [Supabase Documentation](https://supabase.com/docs)
- [OpenAI API Documentation](https://platform.openai.com/docs)

### Community Support
- Digital Ocean Community: [community.digitalocean.com](https://community.digitalocean.com)
- Application Issues: Create GitHub Issues in the repository

### Monitoring Services (Optional)
- **UptimeRobot**: Free website monitoring
- **New Relic**: Application performance monitoring
- **Datadog**: Infrastructure monitoring

---

## 🚀 Quick Deployment Checklist

- [ ] Digital Ocean account created
- [ ] Supabase project setup with schema
- [ ] OpenAI API key obtained
- [ ] Domain name configured (optional)
- [ ] Droplet created and configured
- [ ] Application deployed and tested
- [ ] SSL certificate installed
- [ ] Monitoring and backups configured
- [ ] Security measures implemented

**Congratulations! Your Section E Parser application is now running in production on Digital Ocean! 🎉** 