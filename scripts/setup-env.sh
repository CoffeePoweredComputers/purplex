#!/bin/bash

# Auto-detect IP addresses and update environment files
echo "Setting up environment with auto-detected IPs..."

# Detect public IP (works on EC2 and other environments)
PUBLIC_IP=$(curl -s http://checkip.amazonaws.com 2>/dev/null || curl -s http://ifconfig.me 2>/dev/null || echo "localhost")

# Detect EC2 instance metadata (if on EC2)
EC2_IP=$(curl -s http://169.254.169.254/latest/meta-data/public-ipv4 2>/dev/null || echo "")

# Use EC2 IP if available, otherwise use public IP
if [ ! -z "$EC2_IP" ]; then
    IP_ADDRESS=$EC2_IP
    echo "Detected EC2 public IP: $IP_ADDRESS"
else
    IP_ADDRESS=$PUBLIC_IP
    echo "Detected public IP: $IP_ADDRESS"
fi

# Update .env.production file with detected IP
if [ -f .env.production ]; then
    # Backup original
    cp .env.production .env.production.backup

    # Update IP-related variables
    sed -i "s|ALLOWED_HOSTS=.*|ALLOWED_HOSTS=${IP_ADDRESS},localhost,127.0.0.1|" .env.production
    sed -i "s|CSRF_TRUSTED_ORIGINS=.*|CSRF_TRUSTED_ORIGINS=http://${IP_ADDRESS},http://${IP_ADDRESS}:80,http://${IP_ADDRESS}:8000|" .env.production
    sed -i "s|CORS_ALLOWED_ORIGINS=.*|CORS_ALLOWED_ORIGINS=http://${IP_ADDRESS},http://${IP_ADDRESS}:80,http://${IP_ADDRESS}:8000|" .env.production

    echo "Updated .env.production with IP: $IP_ADDRESS"
else
    echo "Warning: .env.production not found"
fi

# Also create a simple .env if it doesn't exist
if [ ! -f .env ]; then
    cat > .env << EOF
# Auto-generated environment file
PUBLIC_IP=${IP_ADDRESS}
ALLOWED_HOSTS=${IP_ADDRESS},localhost,127.0.0.1
EOF
    echo "Created .env with IP: $IP_ADDRESS"
fi

echo "Environment setup complete!"
echo "Your application will be accessible at: http://${IP_ADDRESS}"