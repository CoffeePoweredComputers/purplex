#!/bin/bash

# AWS EC2 Deployment Script for Purplex
# This script automates the deployment process on an EC2 instance

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
PROJECT_DIR="/home/ubuntu/purplex"
VENV_DIR="$PROJECT_DIR/env"
LOG_FILE="/home/ubuntu/deployment.log"

# Functions
log() {
    echo -e "${GREEN}[$(date '+%Y-%m-%d %H:%M:%S')]${NC} $1" | tee -a $LOG_FILE
}

error() {
    echo -e "${RED}[ERROR]${NC} $1" | tee -a $LOG_FILE
    exit 1
}

warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1" | tee -a $LOG_FILE
}

# Check if running as ubuntu user
if [ "$USER" != "ubuntu" ]; then
    error "This script should be run as the ubuntu user"
fi

log "Starting Purplex deployment..."

# Step 1: System Updates
log "Updating system packages..."
sudo apt update && sudo apt upgrade -y || error "Failed to update system packages"

# Step 2: Install Dependencies
log "Installing system dependencies..."
sudo apt install -y \
    python3-pip \
    python3-venv \
    postgresql \
    postgresql-contrib \
    redis-server \
    nginx \
    git \
    docker.io \
    docker-compose \
    nodejs \
    npm \
    certbot \
    python3-certbot-nginx \
    htop \
    supervisor || error "Failed to install dependencies"

# Add user to docker group
sudo usermod -aG docker $USER

# Step 3: Clone/Update Repository
if [ -d "$PROJECT_DIR" ]; then
    log "Updating existing repository..."
    cd $PROJECT_DIR
    git stash
    git pull origin main || git pull origin master || warning "Failed to pull latest changes"
else
    log "Cloning repository..."
    cd /home/ubuntu
    read -p "Enter your Git repository URL: " GIT_REPO
    git clone $GIT_REPO purplex || error "Failed to clone repository"
    cd $PROJECT_DIR
fi

# Step 4: Setup Python Environment
log "Setting up Python virtual environment..."
if [ ! -d "$VENV_DIR" ]; then
    python3 -m venv $VENV_DIR || error "Failed to create virtual environment"
fi

source $VENV_DIR/bin/activate
pip install --upgrade pip
# Using production requirements from modular structure
pip install -r requirements/production.txt || error "Failed to install Python dependencies"

# Step 5: Setup Frontend
log "Building frontend..."
cd $PROJECT_DIR/purplex/client
# Use yarn instead of npm (as per project conventions)
yarn install || npm install || error "Failed to install Node dependencies"
yarn build || npm run build || error "Failed to build frontend"
cd $PROJECT_DIR

# Step 6: Environment Configuration
if [ ! -f "$PROJECT_DIR/.env" ]; then
    log "Creating environment configuration..."
    cat > $PROJECT_DIR/.env << 'EOF'
# Environment
PURPLEX_ENV=production

# Django
DJANGO_SECRET_KEY=CHANGE_THIS_TO_A_RANDOM_SECRET_KEY
DJANGO_DEBUG=False
ALLOWED_HOSTS=localhost,127.0.0.1

# Database
DATABASE_URL=postgresql://purplex:purplex_password@localhost:5432/purplex
POSTGRES_PASSWORD=purplex_password

# Redis
REDIS_URL=redis://localhost:6379/0
CELERY_BROKER_URL=redis://localhost:6379/1

# OpenAI
OPENAI_API_KEY=your-openai-key-here
GPT_MODEL=gpt-4o-mini

# Firebase
FIREBASE_CREDENTIALS_PATH=/home/ubuntu/purplex/firebase-credentials.json
EOF
    
    warning "Please edit $PROJECT_DIR/.env with your actual configuration values"
    read -p "Press enter when you've updated the .env file..."
fi

# Step 7: Database Setup
log "Setting up PostgreSQL database..."
sudo -u postgres psql << EOF 2>/dev/null || warning "Database might already exist"
CREATE DATABASE purplex;
CREATE USER purplex WITH PASSWORD 'purplex_password';
GRANT ALL PRIVILEGES ON DATABASE purplex TO purplex;
ALTER USER purplex CREATEDB;
EOF

# Run migrations
log "Running database migrations..."
source $VENV_DIR/bin/activate
python manage.py migrate || error "Failed to run migrations"

# Collect static files
log "Collecting static files..."
python manage.py collectstatic --noinput || error "Failed to collect static files"

# Step 8: Create Systemd Services
log "Creating systemd services..."

# Gunicorn service
sudo tee /etc/systemd/system/purplex.service > /dev/null << EOF
[Unit]
Description=Purplex Django Application
After=network.target

[Service]
User=ubuntu
Group=ubuntu
WorkingDirectory=$PROJECT_DIR
Environment="PATH=$VENV_DIR/bin"
EnvironmentFile=$PROJECT_DIR/.env
ExecStart=$VENV_DIR/bin/gunicorn \\
    --workers 4 \\
    --bind unix:$PROJECT_DIR/purplex.sock \\
    --log-level info \\
    --access-logfile - \\
    --error-logfile - \\
    purplex.wsgi:application

Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# Celery worker service
sudo tee /etc/systemd/system/purplex-celery.service > /dev/null << EOF
[Unit]
Description=Purplex Celery Worker
After=network.target

[Service]
User=ubuntu
Group=ubuntu
WorkingDirectory=$PROJECT_DIR
Environment="PATH=$VENV_DIR/bin"
EnvironmentFile=$PROJECT_DIR/.env
ExecStart=$VENV_DIR/bin/celery -A purplex.celery_simple worker -l info

Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# Celery beat service
sudo tee /etc/systemd/system/purplex-celery-beat.service > /dev/null << EOF
[Unit]
Description=Purplex Celery Beat
After=network.target

[Service]
User=ubuntu
Group=ubuntu
WorkingDirectory=$PROJECT_DIR
Environment="PATH=$VENV_DIR/bin"
EnvironmentFile=$PROJECT_DIR/.env
ExecStart=$VENV_DIR/bin/celery -A purplex.celery_simple beat -l info

Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# Step 9: Configure Nginx
log "Configuring Nginx..."

# Get server IP or domain
read -p "Enter your server's IP address or domain name: " SERVER_NAME

sudo tee /etc/nginx/sites-available/purplex > /dev/null << EOF
upstream purplex_backend {
    server unix:$PROJECT_DIR/purplex.sock;
}

server {
    listen 80;
    server_name $SERVER_NAME;

    client_max_body_size 10M;

    location /static/ {
        alias $PROJECT_DIR/staticfiles/;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }

    location /media/ {
        alias $PROJECT_DIR/media/;
        expires 7d;
    }

    location / {
        root $PROJECT_DIR/purplex/client/dist;
        try_files \$uri \$uri/ /index.html;
    }

    location /api/ {
        proxy_pass http://purplex_backend;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_connect_timeout 30s;
        proxy_read_timeout 30s;
    }

    location /admin/ {
        proxy_pass http://purplex_backend;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }
}
EOF

# Enable site
sudo ln -sf /etc/nginx/sites-available/purplex /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default

# Test Nginx configuration
sudo nginx -t || error "Nginx configuration is invalid"

# Step 10: Start Services
log "Starting services..."

# Reload systemd
sudo systemctl daemon-reload

# Start and enable PostgreSQL
sudo systemctl start postgresql
sudo systemctl enable postgresql

# Start and enable Redis
sudo systemctl start redis-server
sudo systemctl enable redis-server

# Start and enable Purplex services
sudo systemctl start purplex
sudo systemctl enable purplex
sudo systemctl start purplex-celery
sudo systemctl enable purplex-celery
sudo systemctl start purplex-celery-beat
sudo systemctl enable purplex-celery-beat

# Restart Nginx
sudo systemctl restart nginx
sudo systemctl enable nginx

# Step 11: Create superuser
log "Creating Django superuser..."
source $VENV_DIR/bin/activate
python manage.py createsuperuser --noinput --username admin --email admin@example.com 2>/dev/null || warning "Superuser might already exist"

# Step 12: Setup Firewall
log "Configuring firewall..."
sudo ufw allow OpenSSH
sudo ufw allow 'Nginx Full'
sudo ufw --force enable

# Step 13: Create update script
log "Creating update script..."
cat > /home/ubuntu/update-purplex.sh << 'EOF'
#!/bin/bash
cd /home/ubuntu/purplex
git pull
source env/bin/activate
pip install -r requirements/production.txt
python manage.py migrate
python manage.py collectstatic --noinput
cd purplex/client
yarn install || npm install
yarn build || npm run build
sudo systemctl restart purplex
sudo systemctl restart purplex-celery
sudo systemctl restart purplex-celery-beat
sudo systemctl restart nginx
echo "Update complete!"
EOF
chmod +x /home/ubuntu/update-purplex.sh

# Step 14: Display Status
log "Deployment complete! Checking service status..."

echo ""
echo "=================================="
echo "Service Status:"
echo "=================================="
sudo systemctl status purplex --no-pager | head -n 5
sudo systemctl status purplex-celery --no-pager | head -n 5
sudo systemctl status nginx --no-pager | head -n 5
sudo systemctl status postgresql --no-pager | head -n 5
sudo systemctl status redis-server --no-pager | head -n 5

echo ""
echo "=================================="
echo "Deployment Summary:"
echo "=================================="
echo -e "${GREEN}✓${NC} System packages installed"
echo -e "${GREEN}✓${NC} Python environment configured"
echo -e "${GREEN}✓${NC} Frontend built"
echo -e "${GREEN}✓${NC} Database configured"
echo -e "${GREEN}✓${NC} Services started"
echo -e "${GREEN}✓${NC} Nginx configured"
echo -e "${GREEN}✓${NC} Firewall enabled"
echo ""
echo -e "${GREEN}Your application should now be accessible at:${NC}"
echo -e "  ${YELLOW}http://$SERVER_NAME${NC}"
echo ""
echo -e "${GREEN}Admin panel:${NC}"
echo -e "  ${YELLOW}http://$SERVER_NAME/admin${NC}"
echo ""
echo -e "${YELLOW}IMPORTANT NEXT STEPS:${NC}"
echo "1. Update the .env file with your actual configuration"
echo "2. Upload your firebase-credentials.json file"
echo "3. Set a secure password for the admin user:"
echo "   python manage.py changepassword admin"
echo "4. Consider setting up SSL with Let's Encrypt:"
echo "   sudo certbot --nginx -d $SERVER_NAME"
echo ""
echo "To update the application in the future, run:"
echo "  /home/ubuntu/update-purplex.sh"
echo ""
echo "Log file: $LOG_FILE"