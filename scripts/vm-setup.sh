#!/bin/bash
# ===========================================
# GCP VM Initial Setup Script
# Run this on a fresh GCP VM instance
# ===========================================

set -e

echo "========================================"
echo "Bagel Shop - GCP VM Setup"
echo "========================================"

# Update system
echo "[1/6] Updating system packages..."
sudo apt-get update
sudo apt-get upgrade -y

# Install Docker
echo "[2/6] Installing Docker..."
if ! command -v docker &> /dev/null; then
    curl -fsSL https://get.docker.com -o get-docker.sh
    sudo sh get-docker.sh
    sudo usermod -aG docker $USER
    rm get-docker.sh
    echo "Docker installed successfully"
else
    echo "Docker already installed"
fi

# Install Docker Compose
echo "[3/6] Installing Docker Compose..."
if ! command -v docker-compose &> /dev/null; then
    sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
    sudo chmod +x /usr/local/bin/docker-compose
    echo "Docker Compose installed successfully"
else
    echo "Docker Compose already installed"
fi

# Install Git
echo "[4/6] Installing Git..."
sudo apt-get install -y git

# Create project directory
echo "[5/6] Setting up project directory..."
sudo mkdir -p /opt/bagel-shop
sudo chown $USER:$USER /opt/bagel-shop

# Configure Docker for Artifact Registry
echo "[6/6] Configuring Docker authentication..."
gcloud auth configure-docker asia-east1-docker.pkg.dev --quiet

echo ""
echo "========================================"
echo "Setup Complete!"
echo "========================================"
echo ""
echo "Next steps:"
echo "1. Clone your repository:"
echo "   cd /opt/bagel-shop"
echo "   git clone <your-repo-url> ."
echo ""
echo "2. Copy config files:"
echo "   - src/config/config.json"
echo "   - src/config/mybagel-458109-30f35338f350.json"
echo ""
echo "3. Start services:"
echo "   docker compose up -d"
echo ""
echo "4. View logs:"
echo "   docker compose logs -f"
echo ""
echo "NOTE: You may need to logout and login again for Docker permissions to take effect."
