#!/bin/bash
set -e

DOMAIN="${1:-purplex.org}"
EMAIL="${2:-admin@purplex.org}"

echo "========================================="
echo "Purplex SSL Certificate Setup"
echo "========================================="
echo "Domain: $DOMAIN"
echo "Contact email: $EMAIL"
echo ""

# Create required directories
echo "Creating certificate directories..."
mkdir -p logs/certbot

# Check if DNS is configured
echo ""
echo "Checking DNS configuration..."
CURRENT_IP=$(dig +short $DOMAIN | tail -n1)
if [ -z "$CURRENT_IP" ]; then
    echo "ERROR: DNS not configured for $DOMAIN"
    echo "Please ensure your domain's A record points to your server's IP address"
    exit 1
fi
echo "DNS resolved to: $CURRENT_IP"

# Check if nginx config already has the domain
if ! grep -q "$DOMAIN" nginx/nginx.conf; then
    echo "WARNING: nginx.conf doesn't contain $DOMAIN"
    echo "The configuration should already be set for purplex.org"
fi

# Start nginx to handle ACME challenge
echo ""
echo "Starting nginx for ACME challenge..."
docker-compose up -d nginx

# Wait for nginx to be ready
echo "Waiting for nginx to be ready..."
sleep 5

# Request certificate
echo ""
echo "Requesting SSL certificate from Let's Encrypt..."
echo "This may take a few minutes..."
docker-compose run --rm certbot certonly \
  --webroot \
  --webroot-path=/var/www/certbot \
  --email "$EMAIL" \
  --agree-tos \
  --no-eff-email \
  -d "$DOMAIN" \
  -d "www.$DOMAIN"

# Check if certificate was created
if [ ! -d "$(docker volume inspect purplex_certbot-etc -f '{{ .Mountpoint }}')/live/$DOMAIN" ]; then
    echo ""
    echo "ERROR: Certificate creation failed"
    echo "Please check the logs above for errors"
    exit 1
fi

# Reload nginx with new certificates
echo ""
echo "Reloading nginx with SSL configuration..."
docker-compose exec nginx nginx -s reload

echo ""
echo "========================================="
echo "SSL Setup Complete!"
echo "========================================="
echo ""
echo "Your site should now be accessible at:"
echo "  https://$DOMAIN"
echo "  https://www.$DOMAIN"
echo ""
echo "Certificate will auto-renew every 12 hours (if expiring within 30 days)"
echo ""
echo "Next steps:"
echo "1. Test your site: curl -I https://$DOMAIN"
echo "2. Check SSL rating: https://www.ssllabs.com/ssltest/analyze.html?d=$DOMAIN"
echo "3. Update your .env.production file with HTTPS URLs"
echo ""
