#!/bin/bash

# Quick Update Script for SmartBuild SPA Main App Only
# Use this for quick updates to just the main app

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
echo -e "${GREEN}Quick Update: SmartBuild SPA Main${NC}"
echo -e "${GREEN}========================================${NC}"

# Check if key file exists
if [ ! -f "$KEY_PATH" ]; then
    echo -e "${RED}Error: SSH key not found at $KEY_PATH${NC}"
    exit 1
fi

# Set correct permissions for key
chmod 400 "$KEY_PATH"

# Upload main app file
echo -e "${YELLOW}Uploading smartbuild_spa_middleware.py...${NC}"
scp -i "$KEY_PATH" ../smartbuild_spa_middleware.py ubuntu@"$EC2_IP":/opt/smartbuild/

# Also upload version config if it exists
if [ -f "../version_config.py" ]; then
    echo -e "${YELLOW}Uploading version_config.py...${NC}"
    scp -i "$KEY_PATH" ../version_config.py ubuntu@"$EC2_IP":/opt/smartbuild/
fi

# Restart main service
echo -e "${YELLOW}Restarting main service...${NC}"
ssh -i "$KEY_PATH" ubuntu@"$EC2_IP" 'sudo systemctl restart smartbuild'

# Wait for service to start
sleep 3

# Check status
echo -e "\n${GREEN}Service Status:${NC}"
ssh -i "$KEY_PATH" ubuntu@"$EC2_IP" 'sudo systemctl status smartbuild --no-pager | head -10'

echo -e "\n${GREEN}Update Complete!${NC}"
echo -e "Main App URL: ${GREEN}http://$EC2_IP/${NC}"
echo -e "CloudFront:   ${GREEN}https://d10z4f7h6vaz0k.cloudfront.net/${NC}"