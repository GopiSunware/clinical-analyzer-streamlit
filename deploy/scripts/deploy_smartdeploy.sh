#!/bin/bash

# SmartDeploy Deployment Script
# Deploys SmartDeploy v6 Enhanced to EC2

set -e

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Configuration
EC2_IP="98.83.207.85"
KEY_FILE="deploy/keys/smartbuild-20250824180036.pem"
REMOTE_USER="ubuntu"
APP_PORT="8506"
APP_NAME="SmartDeploy"
SERVICE_NAME="smartdeploy"
REMOTE_DIR="/opt/smartdeploy"

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}   SmartDeploy v6 Enhanced Deployment  ${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""

# Check if key file exists
if [ ! -f "$KEY_FILE" ]; then
    echo -e "${RED}Error: SSH key file not found at $KEY_FILE${NC}"
    exit 1
fi

# Set key permissions
chmod 400 $KEY_FILE

echo -e "${YELLOW}Step 1: Creating remote directory structure...${NC}"
ssh -i $KEY_FILE $REMOTE_USER@$EC2_IP << 'EOF'
    sudo mkdir -p /opt/smartdeploy/{utils,deployments,logs,.claude/agents}
    sudo chown -R ubuntu:ubuntu /opt/smartdeploy
    echo "Directory structure created."
EOF

echo -e "${YELLOW}Step 2: Copying SmartDeploy files to EC2...${NC}"
# Copy main files
scp -i $KEY_FILE smartdeploy/smartdeploy_v6_enhanced.py $REMOTE_USER@$EC2_IP:/opt/smartdeploy/
scp -i $KEY_FILE smartdeploy/start_smartdeploy_v6.sh $REMOTE_USER@$EC2_IP:/opt/smartdeploy/

# Copy utils
scp -i $KEY_FILE smartdeploy/utils/*.py $REMOTE_USER@$EC2_IP:/opt/smartdeploy/utils/ 2>/dev/null || true

# Copy agent configurations if they exist
if [ -d ".claude/agents" ]; then
    scp -i $KEY_FILE .claude/agents/*.md $REMOTE_USER@$EC2_IP:/opt/smartdeploy/.claude/agents/ 2>/dev/null || true
fi

echo -e "${YELLOW}Step 3: Installing dependencies...${NC}"
ssh -i $KEY_FILE $REMOTE_USER@$EC2_IP << 'EOF'
    cd /opt/smartdeploy

    # Install Python dependencies
    pip3 install streamlit streamlit-autorefresh pyyaml boto3

    # Ensure AWS CLI is installed
    which aws || sudo apt-get install -y awscli

    # Ensure tmux is installed
    which tmux || sudo apt-get install -y tmux

    echo "Dependencies installed."
EOF

echo -e "${YELLOW}Step 4: Creating systemd service...${NC}"
ssh -i $KEY_FILE $REMOTE_USER@$EC2_IP << 'EOF'
sudo tee /etc/systemd/system/smartdeploy.service > /dev/null << 'SERVICE'
[Unit]
Description=SmartDeploy v6 Enhanced - CloudFormation Deployment Pipeline
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/opt/smartdeploy
Environment="PATH=/home/ubuntu/.local/bin:/usr/local/bin:/usr/bin:/bin"
Environment="AWS_DEFAULT_REGION=us-east-1"
ExecStart=/home/ubuntu/.local/bin/streamlit run smartdeploy_v6_enhanced.py --server.port 8506 --server.address 0.0.0.0
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
SERVICE

sudo systemctl daemon-reload
sudo systemctl enable smartdeploy.service
echo "Systemd service created and enabled."
EOF

echo -e "${YELLOW}Step 5: Starting SmartDeploy service...${NC}"
ssh -i $KEY_FILE $REMOTE_USER@$EC2_IP << 'EOF'
    # Stop if running
    sudo systemctl stop smartdeploy 2>/dev/null || true

    # Start service
    sudo systemctl start smartdeploy

    # Wait for startup
    sleep 5

    # Check status
    sudo systemctl status smartdeploy --no-pager | head -15
EOF

echo -e "${YELLOW}Step 6: Verifying deployment...${NC}"
# Test the service
if curl -s -o /dev/null -w "%{http_code}" http://$EC2_IP:$APP_PORT | grep -q "200\|302"; then
    echo -e "${GREEN}✅ SmartDeploy is running successfully!${NC}"
else
    echo -e "${RED}⚠️ SmartDeploy might not be responding correctly${NC}"
fi

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}       Deployment Complete!             ${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo "Access SmartDeploy at:"
echo -e "  EC2 URL: ${GREEN}http://$EC2_IP:$APP_PORT${NC}"
echo ""
echo "To check logs:"
echo "  ssh -i $KEY_FILE $REMOTE_USER@$EC2_IP"
echo "  sudo journalctl -u smartdeploy -f"
echo ""
echo "To restart service:"
echo "  ssh -i $KEY_FILE $REMOTE_USER@$EC2_IP"
echo "  sudo systemctl restart smartdeploy"