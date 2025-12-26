#!/bin/bash
# ===========================================
# Manual Deployment Script
# Run this on the GCP VM to deploy updates
# ===========================================

set -e

PROJECT_DIR="/opt/bagel-shop"
REGISTRY="asia-east1-docker.pkg.dev"
PROJECT_ID="mybagel-458109"
REPO="bagel-repo"

echo "========================================"
echo "Bagel Shop - Deployment"
echo "========================================"

cd $PROJECT_DIR

# Pull latest code
echo "[1/5] Pulling latest code..."
git pull origin main

# Configure Docker auth
echo "[2/5] Authenticating to Artifact Registry..."
gcloud auth configure-docker $REGISTRY --quiet

# Pull latest images
echo "[3/5] Pulling latest images..."
docker compose pull

# Restart services
echo "[4/5] Restarting services..."
docker compose down
docker compose up -d

# Clean up old images
echo "[5/5] Cleaning up old images..."
docker image prune -f

echo ""
echo "========================================"
echo "Deployment Complete!"
echo "========================================"
echo ""
echo "Service Status:"
docker compose ps
echo ""
echo "View logs: docker compose logs -f"
