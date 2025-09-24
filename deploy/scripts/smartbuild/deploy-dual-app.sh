#!/bin/bash

# SmartBuild Dual Application Deployment Script
# Deploys both SmartBuild SPA and SmartBuild Monitor to EC2

set -e

# Configuration
EC2_IP="${1:-98.83.207.85}"
KEY_NAME="${2:-smartbuild-20250824180036}"
KEY_PATH="./smartbuild-20250824180036.pem"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}SmartBuild Dual App Deployment${NC}"
echo -e "${GREEN}========================================${NC}"

# Check if key file exists
if [ ! -f "$KEY_PATH" ]; then
    echo -e "${RED}Error: SSH key not found at $KEY_PATH${NC}"
    exit 1
fi

# Set correct permissions for key
chmod 400 "$KEY_PATH"

echo -e "${YELLOW}Target EC2: $EC2_IP${NC}"

# Step 1: Stop both services
echo -e "\n${GREEN}Step 1: Stopping services...${NC}"
ssh -i "$KEY_PATH" ubuntu@"$EC2_IP" << 'EOF'
sudo systemctl stop smartbuild || true
sudo systemctl stop smartmonitor || true
EOF

# Step 2: Upload application files
echo -e "\n${GREEN}Step 2: Uploading application files...${NC}"

# Create file list for upload
cat > /tmp/upload_files.txt << 'FILELIST'
smartbuild_spa_middleware.py
smartbuild_monitor.py
version_config.py
CLAUDE.md
requirements.txt
.tmux.conf
FILELIST

# Upload main files
while IFS= read -r file; do
    if [ -f "../$file" ]; then
        echo "Uploading $file..."
        scp -i "$KEY_PATH" "../$file" ubuntu@"$EC2_IP":/opt/smartbuild/ 2>/dev/null || true
    fi
done < /tmp/upload_files.txt

# Upload utils directory
echo "Uploading utils directory..."
scp -i "$KEY_PATH" -r ../utils ubuntu@"$EC2_IP":/opt/smartbuild/ 2>/dev/null || true

# Upload assets directory
echo "Uploading assets directory..."
scp -i "$KEY_PATH" -r ../assets ubuntu@"$EC2_IP":/opt/smartbuild/ 2>/dev/null || true

# Upload .claude directory
echo "Uploading .claude directory..."
scp -i "$KEY_PATH" -r ../.claude ubuntu@"$EC2_IP":/opt/smartbuild/ 2>/dev/null || true

# Upload .md directory (hidden)
echo "Uploading .md directory..."
scp -i "$KEY_PATH" -r ../.md ubuntu@"$EC2_IP":/opt/smartbuild/ 2>/dev/null || true

# Step 3: Update Nginx configuration
echo -e "\n${GREEN}Step 3: Updating Nginx configuration...${NC}"
scp -i "$KEY_PATH" nginx-dual-app.conf ubuntu@"$EC2_IP":/tmp/
ssh -i "$KEY_PATH" ubuntu@"$EC2_IP" << 'EOF'
sudo mv /tmp/nginx-dual-app.conf /etc/nginx/sites-available/default
sudo nginx -t
sudo systemctl reload nginx
EOF

# Step 4: Update systemd services
echo -e "\n${GREEN}Step 4: Updating systemd services...${NC}"
scp -i "$KEY_PATH" smartbuild.service ubuntu@"$EC2_IP":/tmp/
scp -i "$KEY_PATH" smartmonitor.service ubuntu@"$EC2_IP":/tmp/

ssh -i "$KEY_PATH" ubuntu@"$EC2_IP" << 'EOF'
sudo mv /tmp/smartbuild.service /etc/systemd/system/
sudo mv /tmp/smartmonitor.service /etc/systemd/system/
sudo systemctl daemon-reload
EOF

# Step 5: Install Python dependencies
echo -e "\n${GREEN}Step 5: Checking Python dependencies...${NC}"
ssh -i "$KEY_PATH" ubuntu@"$EC2_IP" << 'EOF'
cd /opt/smartbuild
source venv/bin/activate
pip install -q plotly kaleido 2>/dev/null || true
EOF

# Step 6: Create necessary directories
echo -e "\n${GREEN}Step 6: Creating directories...${NC}"
ssh -i "$KEY_PATH" ubuntu@"$EC2_IP" << 'EOF'
cd /opt/smartbuild
mkdir -p sessions/active sessions/deleted logs backups
sudo chown -R ubuntu:ubuntu /opt/smartbuild
EOF

# Step 7: Start services
echo -e "\n${GREEN}Step 7: Starting services...${NC}"
ssh -i "$KEY_PATH" ubuntu@"$EC2_IP" << 'EOF'
sudo systemctl enable smartbuild
sudo systemctl enable smartmonitor
sudo systemctl start smartbuild
sudo systemctl start smartmonitor
sleep 5
EOF

# Step 8: Verify services
echo -e "\n${GREEN}Step 8: Verifying services...${NC}"
ssh -i "$KEY_PATH" ubuntu@"$EC2_IP" << 'EOF'
echo "=== SmartBuild SPA Status ==="
sudo systemctl status smartbuild --no-pager | head -10
echo ""
echo "=== SmartBuild Monitor Status ==="
sudo systemctl status smartmonitor --no-pager | head -10
echo ""
echo "=== Port Check ==="
sudo netstat -tlnp | grep -E ':(8504|8505)'
EOF

# Step 9: Test endpoints
echo -e "\n${GREEN}Step 9: Testing endpoints...${NC}"
echo "Testing main app..."
curl -s -o /dev/null -w "Main App (port 8505): HTTP %{http_code}\n" http://$EC2_IP/
echo "Testing monitor app..."
curl -s -o /dev/null -w "Monitor App (port 8504): HTTP %{http_code}\n" http://$EC2_IP/monitor/

echo -e "\n${GREEN}========================================${NC}"
echo -e "${GREEN}Deployment Complete!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo -e "${YELLOW}Access URLs:${NC}"
echo -e "Main App:    ${GREEN}http://$EC2_IP/${NC}"
echo -e "Monitor:     ${GREEN}http://$EC2_IP/monitor/${NC}"
echo ""
echo -e "${YELLOW}CloudFront URLs (if configured):${NC}"
echo -e "Main App:    ${GREEN}https://d10z4f7h6vaz0k.cloudfront.net/${NC}"
echo -e "Monitor:     ${GREEN}https://d10z4f7h6vaz0k.cloudfront.net/monitor/${NC}"
echo ""
echo -e "${YELLOW}Service Management:${NC}"
echo "View main app logs:    ssh -i $KEY_PATH ubuntu@$EC2_IP 'sudo journalctl -u smartbuild -f'"
echo "View monitor logs:     ssh -i $KEY_PATH ubuntu@$EC2_IP 'sudo journalctl -u smartmonitor -f'"
echo "Restart main app:      ssh -i $KEY_PATH ubuntu@$EC2_IP 'sudo systemctl restart smartbuild'"
echo "Restart monitor:       ssh -i $KEY_PATH ubuntu@$EC2_IP 'sudo systemctl restart smartmonitor'"

# Cleanup
rm -f /tmp/upload_files.txt