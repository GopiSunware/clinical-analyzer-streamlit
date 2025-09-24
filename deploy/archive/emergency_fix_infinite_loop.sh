#!/bin/bash
# Emergency Fix for Infinite Loop Issue
# September 2, 2025

set -e

echo "==========================================" 
echo "EMERGENCY FIX - INFINITE RERUN LOOP"
echo "=========================================="
echo ""

# Configuration
EC2_IP="98.83.207.85"
PEM_FILE="./smartbuild-20250824180036.pem"

echo "1. Copying fixed file to EC2..."
scp -i "$PEM_FILE" ../smartbuild_spa_middleware.py ubuntu@$EC2_IP:/tmp/

echo ""
echo "2. Deploying emergency fix..."
ssh -i "$PEM_FILE" ubuntu@$EC2_IP << 'EOF'
    echo "Backing up current file..."
    sudo cp /opt/smartbuild/smartbuild_spa_middleware.py /opt/smartbuild/smartbuild_spa_middleware.py.backup_infinite_loop
    
    echo "Deploying fixed file..."
    sudo cp /tmp/smartbuild_spa_middleware.py /opt/smartbuild/
    sudo cp /tmp/smartbuild_spa_middleware.py /opt/smartmonitor/
    sudo chown ubuntu:ubuntu /opt/smartbuild/smartbuild_spa_middleware.py
    sudo chown ubuntu:ubuntu /opt/smartmonitor/smartbuild_spa_middleware.py
    
    echo "Restarting services..."
    sudo systemctl restart smartbuild smartmonitor
    
    echo "Waiting for services to start..."
    sleep 5
    
    echo "Checking service status..."
    sudo systemctl status smartbuild --no-pager | head -5
EOF

echo ""
echo "3. Verifying fix..."
curl -s -o /dev/null -w "HTTP Status: %{http_code}\n" http://$EC2_IP:8505

echo ""
echo "=========================================="
echo "EMERGENCY FIX DEPLOYED!"
echo "=========================================="
echo ""
echo "Test the site now:"
echo "- CloudFront: https://d10z4f7h6vaz0k.cloudfront.net/"
echo "- Direct: http://$EC2_IP:8505"
echo ""
echo "The infinite loop has been fixed by:"
echo "1. Removing st.rerun() from force reload section"
echo "2. Adding flag to prevent multiple reload attempts"
echo ""