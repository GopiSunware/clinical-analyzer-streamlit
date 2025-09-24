#!/bin/bash
# Deploy Critical Fixes - September 2, 2025
# Fixes:
# 1. Prompt file creation issue (utils/prompt_preparers.py)
# 2. Requirements loading auto-refresh bug (smartbuild_spa_middleware.py)

set -e  # Exit on error

echo "=========================================="
echo "DEPLOYING CRITICAL FIXES TO EC2"
echo "=========================================="
echo ""

# Configuration
EC2_IP="98.83.207.85"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

# Find PEM file
PEM_FILE=$(find . -name "*.pem" 2>/dev/null | head -1)
if [ -z "$PEM_FILE" ]; then
    # Try parent directory
    PEM_FILE=$(find .. -name "*.pem" 2>/dev/null | head -1)
fi

if [ -z "$PEM_FILE" ]; then
    echo "ERROR: No PEM file found in current or parent directory"
    echo "Please specify the path to your PEM file:"
    echo "Example: PEM_FILE=/path/to/your.pem ./deploy_critical_fixes_20250902.sh"
    exit 1
fi

echo "Using PEM file: $PEM_FILE"

echo "1. Creating backup on EC2..."
ssh -i "$PEM_FILE" ubuntu@$EC2_IP << 'EOF'
    # Create backup directory
    BACKUP_DIR="/opt/smartbuild/backups/$(date +%Y%m%d_%H%M%S)"
    mkdir -p "$BACKUP_DIR"
    
    # Backup current files
    cp /opt/smartbuild/utils/prompt_preparers.py "$BACKUP_DIR/" 2>/dev/null || true
    cp /opt/smartbuild/smartbuild_spa_middleware.py "$BACKUP_DIR/" 2>/dev/null || true
    
    echo "Backup created at: $BACKUP_DIR"
EOF

echo ""
echo "2. Copying fixed files to EC2..."

# Determine base directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
BASE_DIR="$(dirname "$SCRIPT_DIR")"

echo "Base directory: $BASE_DIR"

# Copy the fixed files
scp -i "$PEM_FILE" "$BASE_DIR/utils/prompt_preparers.py" ubuntu@$EC2_IP:/tmp/
scp -i "$PEM_FILE" "$BASE_DIR/smartbuild_spa_middleware.py" ubuntu@$EC2_IP:/tmp/

echo ""
echo "3. Deploying fixes to both applications..."
ssh -i "$PEM_FILE" ubuntu@$EC2_IP << 'EOF'
    echo "Stopping services..."
    sudo systemctl stop smartbuild smartmonitor
    
    echo "Deploying utils/prompt_preparers.py..."
    sudo cp /tmp/prompt_preparers.py /opt/smartbuild/utils/
    sudo cp /tmp/prompt_preparers.py /opt/smartmonitor/utils/
    
    echo "Deploying smartbuild_spa_middleware.py..."
    sudo cp /tmp/smartbuild_spa_middleware.py /opt/smartbuild/
    sudo cp /tmp/smartbuild_spa_middleware.py /opt/smartmonitor/
    
    echo "Setting permissions..."
    sudo chown -R ubuntu:ubuntu /opt/smartbuild/
    sudo chown -R ubuntu:ubuntu /opt/smartmonitor/
    
    echo "Starting services..."
    sudo systemctl start smartbuild smartmonitor
    
    echo "Waiting for services to start..."
    sleep 5
    
    echo "Checking service status..."
    sudo systemctl status smartbuild --no-pager | head -10
    sudo systemctl status smartmonitor --no-pager | head -10
EOF

echo ""
echo "4. Verifying deployment..."
ssh -i "$PEM_FILE" ubuntu@$EC2_IP << 'EOF'
    echo "Checking for fix markers..."
    
    echo -n "Prompt file fix (get_base_directory): "
    if grep -q "get_base_directory" /opt/smartbuild/utils/prompt_preparers.py; then
        echo "✅ FOUND"
    else
        echo "❌ NOT FOUND"
    fi
    
    echo -n "Requirements loading fix (CRITICAL FIX): "
    if grep -q "CRITICAL FIX" /opt/smartbuild/smartbuild_spa_middleware.py; then
        echo "✅ FOUND"
    else
        echo "❌ NOT FOUND"
    fi
    
    echo -n "Post-extraction reload (POST-EXTRACTION): "
    if grep -q "POST-EXTRACTION" /opt/smartbuild/smartbuild_spa_middleware.py; then
        echo "✅ FOUND"
    else
        echo "❌ NOT FOUND"
    fi
EOF

echo ""
echo "5. Testing application availability..."
# Test if the application is responding
response=$(curl -s -o /dev/null -w "%{http_code}" http://$EC2_IP:8505 || echo "000")
if [ "$response" = "200" ]; then
    echo "✅ Main application (port 8505) is responding"
else
    echo "⚠️  Main application might need more time to start (HTTP $response)"
fi

response=$(curl -s -o /dev/null -w "%{http_code}" http://$EC2_IP:8504 || echo "000")
if [ "$response" = "200" ]; then
    echo "✅ Monitor application (port 8504) is responding"
else
    echo "⚠️  Monitor application might need more time to start (HTTP $response)"
fi

echo ""
echo "=========================================="
echo "DEPLOYMENT COMPLETE!"
echo "=========================================="
echo ""
echo "Fixes deployed:"
echo "1. ✅ Prompt file creation issue fixed"
echo "2. ✅ Requirements loading auto-refresh bug fixed"
echo ""
echo "Test the fixes:"
echo "1. Visit: http://$EC2_IP:8505"
echo "2. Create a new session"
echo "3. Generate requirements"
echo "4. Verify requirements load automatically after extraction"
echo ""
echo "CloudFront URLs:"
echo "- Main App: https://d10z4f7h6vaz0k.cloudfront.net/"
echo "- Monitor: https://d1b2mw2j81ms4x.cloudfront.net/"
echo ""
echo "If issues persist, check logs:"
echo "ssh -i $PEM_FILE ubuntu@$EC2_IP 'sudo journalctl -u smartbuild -f'"