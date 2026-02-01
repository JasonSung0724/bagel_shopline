#!/bin/bash
# SSL Certificate Setup Script for carbs-reduced-admin.com
# This script sets up Let's Encrypt SSL certificates using Certbot

set -e  # Exit on error

echo "🔒 SSL Certificate Setup for carbs-reduced-admin.com"
echo "=================================================="
echo ""

# Configuration
DOMAIN="carbs-reduced-admin.com"
EMAIL="bagelshop2025@gmail.com"  # Change this to your email
SSL_DIR="/opt/bagel-shop/ssl"
CERTBOT_DIR="/opt/bagel-shop/certbot"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${YELLOW}Step 1: Installing Certbot...${NC}"
if ! command -v certbot &> /dev/null; then
    echo "Installing Certbot..."
    sudo apt-get update
    sudo apt-get install -y certbot
    echo -e "${GREEN}✓ Certbot installed${NC}"
else
    echo -e "${GREEN}✓ Certbot already installed${NC}"
fi

echo ""
echo -e "${YELLOW}Step 2: Creating SSL directory...${NC}"
sudo mkdir -p "$SSL_DIR"
sudo mkdir -p "$CERTBOT_DIR/www"
sudo chown -R $(whoami):$(whoami) "$SSL_DIR"
sudo chown -R $(whoami):$(whoami) "$CERTBOT_DIR"
echo -e "${GREEN}✓ Directories created${NC}"

echo ""
echo -e "${YELLOW}Step 3: Obtaining SSL certificate...${NC}"
echo "Domain: $DOMAIN"
echo "Email: $EMAIL"
echo ""

# Stop nginx temporarily if running
if docker ps | grep -q bagel-nginx; then
    echo "Stopping nginx container..."
    docker stop bagel-nginx || true
fi

# Get certificate using standalone mode (port 80)
sudo certbot certonly \
    --standalone \
    --non-interactive \
    --agree-tos \
    --email "$EMAIL" \
    --domains "$DOMAIN" \
    --domains "www.$DOMAIN" \
    --preferred-challenges http

echo -e "${GREEN}✓ SSL certificate obtained${NC}"

echo ""
echo -e "${YELLOW}Step 4: Copying certificates to project directory...${NC}"
sudo cp /etc/letsencrypt/live/$DOMAIN/fullchain.pem "$SSL_DIR/"
sudo cp /etc/letsencrypt/live/$DOMAIN/privkey.pem "$SSL_DIR/"
sudo chown $(whoami):$(whoami) "$SSL_DIR"/*.pem
sudo chmod 644 "$SSL_DIR"/fullchain.pem
sudo chmod 600 "$SSL_DIR"/privkey.pem
echo -e "${GREEN}✓ Certificates copied${NC}"

echo ""
echo -e "${YELLOW}Step 5: Setting up auto-renewal...${NC}"
# Create renewal script
cat > /tmp/renew-ssl.sh << 'EOF'
#!/bin/bash
# SSL Certificate Renewal Script
certbot renew --quiet
cp /etc/letsencrypt/live/carbs-reduced-admin.com/fullchain.pem /opt/bagel-shop/ssl/
cp /etc/letsencrypt/live/carbs-reduced-admin.com/privkey.pem /opt/bagel-shop/ssl/
docker restart bagel-nginx
EOF

sudo mv /tmp/renew-ssl.sh /etc/cron.weekly/renew-ssl
sudo chmod +x /etc/cron.weekly/renew-ssl
echo -e "${GREEN}✓ Auto-renewal configured (weekly check)${NC}"

echo ""
echo -e "${GREEN}=================================================="
echo "✅ SSL Setup Complete!"
echo "=================================================="
echo ""
echo "Next steps:"
echo "1. Start your services: cd /opt/bagel-shop && docker compose up -d"
echo "2. Test HTTPS: curl -I https://$DOMAIN"
echo "3. Visit: https://$DOMAIN"
echo ""
echo "Certificate locations:"
echo "  - Fullchain: $SSL_DIR/fullchain.pem"
echo "  - Private key: $SSL_DIR/privkey.pem"
echo ""
echo "Certificate will auto-renew weekly via cron."
echo "=================================================="${NC}
