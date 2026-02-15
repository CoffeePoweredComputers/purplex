#!/bin/bash
set -e

# EC2 Instance Setup Script for Purplex
# Run this on a fresh Ubuntu EC2 instance to prepare it for deployment

echo "================================================"
echo "EC2 Setup Script for Purplex"
echo "================================================"

# Color codes for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

print_status() {
    echo -e "${GREEN}[+]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[*]${NC} $1"
}

# Update system
print_status "Updating system packages..."
sudo apt-get update
sudo apt-get upgrade -y

# Install Docker
print_status "Installing Docker..."
if ! command -v docker &> /dev/null; then
    curl -fsSL https://get.docker.com -o get-docker.sh
    sudo sh get-docker.sh
    sudo usermod -aG docker $USER
    rm get-docker.sh
    print_warning "Docker installed. You may need to log out and back in for group changes to take effect."
else
    print_status "Docker already installed"
fi

# Install Docker Compose
print_status "Installing Docker Compose..."
if ! command -v docker-compose &> /dev/null; then
    sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
    sudo chmod +x /usr/local/bin/docker-compose
else
    print_status "Docker Compose already installed"
fi

# Install AWS CLI (if needed for ECR)
print_status "Installing AWS CLI..."
if ! command -v aws &> /dev/null; then
    sudo apt-get install -y awscli
else
    print_status "AWS CLI already installed"
fi

# Install other useful tools
print_status "Installing additional tools..."
sudo apt-get install -y \
    git \
    htop \
    ncdu \
    unzip \
    jq \
    certbot \
    python3-certbot-nginx

# Configure firewall
print_status "Configuring firewall..."
sudo ufw allow 22/tcp    # SSH
sudo ufw allow 80/tcp    # HTTP
sudo ufw allow 443/tcp   # HTTPS
sudo ufw --force enable

# Create application directory
print_status "Creating application directory..."
mkdir -p ~/purplex
cd ~/purplex

# Setup log rotation
print_status "Setting up log rotation..."
sudo tee /etc/logrotate.d/purplex > /dev/null << 'EOF'
/home/ubuntu/purplex/logs/*.log {
    daily
    rotate 30
    compress
    delaycompress
    notifempty
    create 0640 ubuntu ubuntu
    sharedscripts
    postrotate
        docker-compose -f /home/ubuntu/purplex/docker-compose.yml kill -s USR1 web
    endscript
}
EOF

# Setup swap (helpful for t2.micro instances)
print_status "Setting up swap space..."
if [ ! -f /swapfile ]; then
    sudo fallocate -l 2G /swapfile
    sudo chmod 600 /swapfile
    sudo mkswap /swapfile
    sudo swapon /swapfile
    echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
else
    print_status "Swap already configured"
fi

# Optimize Docker for production
print_status "Optimizing Docker configuration..."
sudo tee /etc/docker/daemon.json > /dev/null << 'EOF'
{
    "log-driver": "json-file",
    "log-opts": {
        "max-size": "10m",
        "max-file": "3"
    },
    "storage-driver": "overlay2",
    "live-restore": true,
    "userland-proxy": false
}
EOF

sudo systemctl restart docker

# Create systemd service for auto-start
print_status "Creating systemd service..."
sudo tee /etc/systemd/system/purplex.service > /dev/null << 'EOF'
[Unit]
Description=Purplex Application
Requires=docker.service
After=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=/home/ubuntu/purplex
ExecStart=/usr/local/bin/docker-compose up -d
ExecStop=/usr/local/bin/docker-compose down
StandardOutput=journal
User=ubuntu

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable purplex.service

# Setup CloudWatch agent (optional)
print_warning "To setup CloudWatch monitoring, run:"
echo "  wget https://s3.amazonaws.com/amazoncloudwatch-agent/ubuntu/amd64/latest/amazon-cloudwatch-agent.deb"
echo "  sudo dpkg -i amazon-cloudwatch-agent.deb"

# Create backup script
print_status "Creating backup script..."
cat > ~/backup-purplex.sh << 'EOF'
#!/bin/bash
BACKUP_DIR="/home/ubuntu/backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
mkdir -p $BACKUP_DIR

# Backup database
docker-compose exec -T postgres pg_dump -U purplex_user purplex_prod > $BACKUP_DIR/db_backup_$TIMESTAMP.sql

# Backup media files
tar -czf $BACKUP_DIR/media_backup_$TIMESTAMP.tar.gz -C /home/ubuntu/purplex media/

# Keep only last 7 days of backups
find $BACKUP_DIR -type f -mtime +7 -delete

echo "Backup completed: $TIMESTAMP"
EOF

chmod +x ~/backup-purplex.sh

# Setup cron for automated backups
print_status "Setting up automated backups..."
(crontab -l 2>/dev/null; echo "0 2 * * * /home/ubuntu/backup-purplex.sh > /home/ubuntu/backup.log 2>&1") | crontab -

# Display system information
print_status "System setup complete!"
echo ""
echo "================================================"
echo "System Information:"
echo "================================================"
echo "Docker version: $(docker --version)"
echo "Docker Compose version: $(docker-compose --version)"
echo "Python version: $(python3 --version)"
echo "Available memory: $(free -h | grep Mem | awk '{print $2}')"
echo "Available disk: $(df -h / | tail -1 | awk '{print $4}')"
echo ""
echo "Security Groups to configure in AWS Console:"
echo "  - Port 22: SSH (your IP only)"
echo "  - Port 80: HTTP (0.0.0.0/0)"
echo "  - Port 443: HTTPS (0.0.0.0/0)"
echo ""
print_warning "Next steps:"
echo "1. Configure AWS security groups"
echo "2. Set up Elastic IP (optional but recommended)"
echo "3. Configure Route 53 DNS (if using)"
echo "4. Run the deployment script"
echo "5. Set up SSL certificates"
echo "================================================"