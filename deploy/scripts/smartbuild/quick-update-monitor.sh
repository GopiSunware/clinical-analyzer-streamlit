#!/bin/bash

# Quick Update Script for SmartBuild Monitor Only
# Use this for quick updates to just the monitor app

set -e

# Configuration
EC2_IP="${1:-98.83.207.85}"
KEY_PATH="./smartbuild-20250824180036.pem"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Quick Update: SmartBuild Monitor${NC}"
echo -e "${GREEN}========================================${NC}"

# Check if key file exists
if [ ! -f "$KEY_PATH" ]; then
    echo -e "${RED}Error: SSH key not found at $KEY_PATH${NC}"
    exit 1
fi

# Set correct permissions for key
chmod 400 "$KEY_PATH"

# Upload monitor file
echo -e "${YELLOW}Uploading smartbuild_monitor.py...${NC}"
scp -i "$KEY_PATH" ../smartbuild_monitor.py ubuntu@"$EC2_IP":/opt/smartbuild/

# Restart monitor service
echo -e "${YELLOW}Restarting monitor service...${NC}"
ssh -i "$KEY_PATH" ubuntu@"$EC2_IP" 'sudo systemctl restart smartmonitor'

# Wait for service to start
sleep 3

# Check status
echo -e "\n${GREEN}Service Status:${NC}"
ssh -i "$KEY_PATH" ubuntu@"$EC2_IP" 'sudo systemctl status smartmonitor --no-pager | head -10'

echo -e "\n${GREEN}Update Complete!${NC}"
echo -e "Monitor URL: ${GREEN}http://$EC2_IP/monitor/${NC}"
echo -e "CloudFront:  ${GREEN}https://d10z4f7h6vaz0k.cloudfront.net/monitor/${NC}"