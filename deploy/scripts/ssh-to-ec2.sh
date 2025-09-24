#!/bin/bash

# SSH Helper Script for SmartBuild EC2
# Easy SSH access to the production EC2 instance

EC2_IP="98.83.207.85"
PEM_FILE="smartbuild-20250824180036.pem"
USER="ubuntu"

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}Connecting to SmartBuild EC2 Instance...${NC}"
echo -e "${YELLOW}Instance: $EC2_IP (t3.large, us-east-1)${NC}"
echo ""

# Check if PEM file exists
if [ ! -f "$PEM_FILE" ]; then
    echo "Error: PEM file not found: $PEM_FILE"
    echo "Make sure you're running this script from the deploy/ directory"
    exit 1
fi

# Set correct permissions
chmod 400 "$PEM_FILE"

# Connect to EC2
ssh -o StrictHostKeyChecking=no -i "$PEM_FILE" "$USER@$EC2_IP"