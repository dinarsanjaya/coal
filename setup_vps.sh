#!/bin/bash

echo "=== COAL Mining Bot - VPS Setup ==="
echo ""

# Update system
echo "1. Updating system..."
sudo apt update && sudo apt upgrade -y

# Install Python 3 and pip
echo "2. Installing Python..."
sudo apt install -y python3 python3-pip

# Install Node.js and PM2
echo "3. Installing Node.js and PM2..."
curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
sudo apt install -y nodejs
sudo npm install -g pm2

# Install Python dependencies
echo "4. Installing Python dependencies..."
pip3 install requests

# Create logs directory
echo "5. Creating logs directory..."
mkdir -p logs

# Setup PM2 startup
echo "6. Setting up PM2 startup..."
pm2 startup
# Follow the command that PM2 shows

echo ""
echo "=== Setup Complete! ==="
echo ""
echo "Next steps:"
echo "1. Edit config.json with your wallet and API key"
echo "2. Edit ecosystem.config.js - change 'cwd' path to your VPS path"
echo "3. Run: pm2 start ecosystem.config.js"
echo "4. Run: pm2 save"
echo ""
