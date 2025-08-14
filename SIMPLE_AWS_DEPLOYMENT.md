# Simple AWS Deployment Guide for Purplex

## Target: 800 University Students
A straightforward EC2 deployment without unnecessary complexity.

## Quick Deployment (1 Day)

### Step 1: Launch EC2 Instance
```bash
# Instance specifications for 800 students:
- Type: t3.large (2 vCPU, 8 GB RAM)
- Storage: 50 GB gp3 SSD  
- OS: Ubuntu 22.04 LTS
- Security Group: ONLY allow ports 22 (SSH), 80 (HTTP), 443 (HTTPS)
- CRITICAL: Port 8000 must NEVER be exposed in security groups or firewall rules
```

### Step 2: Initial Server Setup
```bash
# Connect to instance
ssh -i your-key.pem ubuntu@your-ip

# Install essentials
sudo apt update && sudo apt install -y \
    python3-pip python3-venv \
    postgresql postgresql-contrib \
    redis-server nginx git \
    certbot python3-certbot-nginx

# Start services
sudo systemctl start postgresql redis-server
sudo systemctl enable postgresql redis-server

# Configure firewall (UFW) - CRITICAL SECURITY
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow ssh
sudo ufw allow 'Nginx Full'
# NEVER allow port 8000 - it should only be accessible via nginx proxy
sudo ufw deny 8000
sudo ufw --force enable
sudo ufw status
echo "Firewall configured - Port 8000 is blocked from external access"
```

### Step 3: Deploy Application
```bash
# Clone and setup
git clone https://github.com/your-repo/purplex.git
cd purplex
python3 -m venv env
source env/bin/activate
pip install -r requirements.txt

# Setup database
sudo -u postgres createdb purplex
sudo -u postgres createuser purplex_user
# Set a strong password for the database user
sudo -u postgres psql -c "ALTER USER purplex_user PASSWORD 'STRONG_DATABASE_PASSWORD_HERE';"
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE purplex TO purplex_user;"

# Configure environment
cp .env.production.template .env.production
# CRITICAL: Edit .env.production with secure settings:
# - DJANGO_SECRET_KEY=GENERATE_RANDOM_SECRET_KEY_HERE
# - DATABASE_URL=postgresql://purplex_user:STRONG_DATABASE_PASSWORD_HERE@localhost:5432/purplex
# - OPENAI_API_KEY=YOUR_OPENAI_API_KEY_HERE
# - All passwords must be strong and unique

# Run migrations
python manage.py migrate
python manage.py collectstatic --noinput
```

### Step 4: Secure Nginx Configuration
```nginx
# /etc/nginx/sites-available/purplex
server {
    listen 80;
    server_name your-domain.com;
    
    # Redirect all HTTP to HTTPS (REQUIRED for production)
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name your-domain.com;
    
    # SSL Configuration (certificates will be added by certbot)
    ssl_certificate /etc/letsencrypt/live/your-domain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/your-domain.com/privkey.pem;
    
    # Strong SSL security
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-RSA-AES256-GCM-SHA512:DHE-RSA-AES256-GCM-SHA512:ECDHE-RSA-AES256-GCM-SHA384:DHE-RSA-AES256-GCM-SHA384;
    ssl_prefer_server_ciphers off;
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 10m;
    
    # Security headers
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;
    add_header Content-Security-Policy "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline';" always;
    
    # Hide nginx version and server info
    server_tokens off;
    add_header X-Robots-Tag "noindex, nofollow" always;
    
    location / {
        # SECURITY: Only proxy to localhost - never expose port 8000 externally
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # Security headers for proxied requests
        proxy_hide_header X-Powered-By;
        proxy_hide_header Server;
        
        # Timeouts for security
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
        
        # Buffer settings to prevent DoS
        proxy_buffer_size 4k;
        proxy_buffers 8 4k;
        proxy_busy_buffers_size 8k;
    }
    
    location /static/ {
        alias /home/ubuntu/purplex/staticfiles/;
        expires 1y;
        add_header Cache-Control "public, immutable";
    }
}

# Enable the site and restart nginx
sudo ln -s /etc/nginx/sites-available/purplex /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

### Step 5: Run with Gunicorn
```bash
# Create simple systemd service
sudo tee /etc/systemd/system/purplex.service << EOF
[Unit]
Description=Purplex
After=network.target

[Service]
User=ubuntu
WorkingDirectory=/home/ubuntu/purplex
ExecStart=/home/ubuntu/purplex/env/bin/gunicorn \
    --workers 3 \
    --bind 127.0.0.1:8000 \
    --timeout 60 \
    --max-requests 1000 \
    --max-requests-jitter 100 \
    --preload \
    --access-logfile /var/log/purplex/access.log \
    --error-logfile /var/log/purplex/error.log \
    --capture-output \
    purplex.wsgi:application

# Create log directory
ExecStartPre=/bin/mkdir -p /var/log/purplex
ExecStartPre=/bin/chown ubuntu:ubuntu /var/log/purplex

[Install]
WantedBy=multi-user.target
EOF

# Start service
sudo systemctl daemon-reload
sudo systemctl start purplex
sudo systemctl enable purplex
```

### Step 6: Add SSL (MANDATORY for Production)
```bash
# PRODUCTION: Use Let's Encrypt (FREE and automated)
sudo certbot --nginx -d your-domain.com
sudo certbot renew --dry-run

# Set up automatic renewal
echo "0 12 * * * /usr/bin/certbot renew --quiet" | sudo crontab -

# DEVELOPMENT ONLY: Self-signed certificate (NOT for production)
# Only use this for local testing - never in production
sudo openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
    -keyout /etc/ssl/private/purplex.key \
    -out /etc/ssl/certs/purplex.crt \
    -subj "/CN=localhost"

# Verify SSL configuration
sudo nginx -t
sudo systemctl reload nginx

# Test HTTPS redirect
curl -I http://your-domain.com
# Should return 301 redirect to https
```

## Background Tasks (Celery)

### Simple Celery Setup
```bash
# Create Celery service
sudo tee /etc/systemd/system/purplex-celery.service << EOF
[Unit]
Description=Purplex Celery
After=network.target

[Service]
User=ubuntu
WorkingDirectory=/home/ubuntu/purplex
ExecStart=/home/ubuntu/purplex/env/bin/celery \
    -A purplex.celery_simple worker -l info

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl start purplex-celery
sudo systemctl enable purplex-celery
```

## Monitoring

### Basic Health Checks
```bash
# Check application (through nginx proxy - NEVER direct port 8000)
curl https://your-domain.com/health/
# OR for internal localhost check only:
curl http://localhost/health/

# Check database connections  
sudo -u postgres psql -c "SELECT count(*) FROM pg_stat_activity"

# Check logs
sudo journalctl -u purplex -f
```

### Simple Monitoring Script
```bash
#!/bin/bash
# monitor.sh - Run via cron every 5 minutes

# Check if app is running (through nginx - NEVER direct port access)
if ! curl -f -k https://localhost/health/ > /dev/null 2>&1; then
    echo "App is down" | mail -s "Purplex Alert" admin@your-domain.com
    sudo systemctl restart purplex
    sudo systemctl restart nginx
fi

# Check memory usage
if [ $(free | grep Mem | awk '{print ($3/$2)*100}' | cut -d. -f1) -gt 90 ]; then
    echo "High memory usage" | mail -s "Purplex Alert" admin@your-domain.com
fi
```

## Backup Strategy

### Daily Database Backup
```bash
# Add to crontab
0 2 * * * pg_dump purplex | gzip > /backups/purplex_$(date +\%Y\%m\%d).sql.gz

# Keep last 7 days
find /backups -name "*.sql.gz" -mtime +7 -delete
```

## Scaling Considerations

### When You Actually Need More (Evidence-Based)
- **CPU consistently > 80%**: Upgrade to t3.xlarge
- **Memory consistently > 7GB**: Upgrade to t3.xlarge  
- **Response times > 2s**: Check database indexes first
- **Database connections > 90**: Fix Django CONN_MAX_AGE first

### What You DON'T Need for 800 Students
- ❌ Load balancers
- ❌ Auto-scaling groups
- ❌ Container orchestration (ECS/EKS)
- ❌ Terraform infrastructure as code
- ❌ Multi-AZ deployments
- ❌ Read replicas

## Security Checklist (MANDATORY)

Before going live, verify ALL of these security requirements:

### ✅ Network Security
- [ ] Port 8000 is BLOCKED in AWS Security Groups
- [ ] Port 8000 is BLOCKED in UFW firewall (`sudo ufw status` shows deny 8000)
- [ ] Only ports 22, 80, 443 are allowed in Security Groups
- [ ] SSH key access only (no password authentication)

### ✅ SSL/TLS Security  
- [ ] HTTPS is working (`curl -I https://your-domain.com`)
- [ ] HTTP redirects to HTTPS (no plain HTTP access)
- [ ] SSL certificate is valid and auto-renewing
- [ ] Strong SSL ciphers configured in nginx
- [ ] HSTS header is present

### ✅ Application Security
- [ ] Django SECRET_KEY is strong and unique (not default)
- [ ] Database password is strong (`STRONG_DATABASE_PASSWORD_HERE` replaced)
- [ ] All `.env` files have secure credentials
- [ ] Port 8000 only accessible via localhost (test: `curl http://your-domain.com:8000` should fail)
- [ ] Debug mode is OFF in production (`DEBUG=False`)

### ✅ Access Control
- [ ] Firewall defaults to deny incoming traffic
- [ ] Only necessary services are running
- [ ] Log files have proper permissions
- [ ] Database access is restricted to application user only

### ✅ Monitoring & Logging
- [ ] Access logs are being written
- [ ] Error logs are being monitored  
- [ ] SSL certificate expiration monitoring
- [ ] Application health checks working

**CRITICAL**: Test port 8000 blocking with: `curl http://your-domain.com:8000` - this MUST fail.

## Total Deployment Time: 4-6 Hours

1. **Hour 1-2**: Server setup and dependencies
2. **Hour 3-4**: Application deployment and configuration
3. **Hour 5-6**: Testing and SSL setup

## Monthly Cost: ~$30-40
- t3.large instance: ~$60/month (or ~$30 with 1-year reserved)
- 50GB storage: ~$5/month
- Data transfer: ~$5/month

This simple approach is sufficient for 800 university students and can be scaled up if actual usage data shows it's needed.