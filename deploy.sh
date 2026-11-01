#!/usr/bin/env bash
# ==============================================================================
# ImpEx AI — Automated Hostinger VPS Deployment Script
# OS: Ubuntu 22.04 / 24.04 LTS on Hostinger VPS
# ==============================================================================
set -e

echo "=== [1/5] Updating System Packages & Installing Docker ==="
sudo apt-get update && sudo apt-get upgrade -y
sudo apt-get install -y ca-certificates curl gnupg lsb-release git

# Install Docker if not present
if ! command -v docker &> /dev/null; then
    echo "Installing Docker..."
    sudo install -m 0755 -d /etc/apt/keyrings
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
    sudo chmod a+r /etc/apt/keyrings/docker.gpg
    echo \
      "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
      $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
    sudo apt-get update
    sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
fi

echo "=== [2/5] Creating Hostinger Production Environment File ==="
if [ ! -f backend/.env ]; then
    cp backend/.env.example backend/.env 2>/dev/null || true
    echo "Created backend/.env. Update with your real Hostinger SMTP credentials and Gemini API Key."
fi

echo "=== [3/5] Building & Launching Docker Containers ==="
sudo docker compose down 2>/dev/null || true
sudo docker compose up --build -d

echo "=== [4/5] Checking Container Health ==="
sleep 5
sudo docker compose ps

echo "=== [5/5] Deployment Complete! ==="
echo "Your ImpEx AI Application is live on port 80 / 443!"
echo "Access in your browser: http://$(curl -s ifconfig.me)"

