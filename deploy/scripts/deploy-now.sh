#!/bin/bash

# Quick deployment script with temporary key fix for WSL
# This script handles the Windows filesystem permission issue

set -e

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${BLUE}=== SmartBuild Quick Deployment ===${NC}"

# Fix key permissions by copying to home
echo -e "${YELLOW}Preparing SSH key...${NC}"
cp deploy/keys/smartbuild-20250824180036.pem ~/smartbuild-key.pem
chmod 400 ~/smartbuild-key.pem

KEY_PATH="$HOME/smartbuild-key.pem"
EC2_IP="98.83.207.85"

# Test connection
echo -e "${YELLOW}Testing connection...${NC}"
if ssh -o ConnectTimeout=5 -o StrictHostKeyChecking=no -i "$KEY_PATH" ubuntu@$EC2_IP "echo 'OK'" > /dev/null 2>&1; then
    echo -e "${GREEN}✅ Connection successful${NC}"
else
    echo "❌ Connection failed"
    exit 1
fi

echo -e "\n${BLUE}📦 Deploying all applications...${NC}"

# 1. Main App
echo "1/4: Main application..."
rsync -az --delete \
  -e "ssh -o StrictHostKeyChecking=no -i $KEY_PATH" \
  --exclude='sessions/' --exclude='__pycache__/' --exclude='.git/' \
  --exclude='logs/' --exclude='deploy/' --exclude='tests/' \
  smartbuild_spa_middleware_dynamic.py job_queue_monitor.py \
  version_config.py requirements.txt utils config .claude \
  ubuntu@$EC2_IP:/opt/smartbuild/

# 2. Job Monitor
echo "2/4: Job Monitor..."
ssh -o StrictHostKeyChecking=no -i "$KEY_PATH" ubuntu@$EC2_IP "mkdir -p /opt/smartmonitor"
rsync -az -e "ssh -o StrictHostKeyChecking=no -i $KEY_PATH" \
  smartbuild_monitor.py utils \
  ubuntu@$EC2_IP:/opt/smartmonitor/

# 3. Control Center
echo "3/4: Control Center..."
ssh -o StrictHostKeyChecking=no -i "$KEY_PATH" ubuntu@$EC2_IP "mkdir -p /opt/job_queue_control"
rsync -az -e "ssh -o StrictHostKeyChecking=no -i $KEY_PATH" \
  job_queue_control.py utils \
  ubuntu@$EC2_IP:/opt/job_queue_control/

# 4. UI Automation
echo "4/4: UI Automation..."
ssh -o StrictHostKeyChecking=no -i "$KEY_PATH" ubuntu@$EC2_IP "mkdir -p /opt/ui-automation/ui-automation-proxy"
rsync -az -e "ssh -o StrictHostKeyChecking=no -i $KEY_PATH" \
  --exclude='__pycache__/' --exclude='logs/' \
  ui-automation/ ubuntu@$EC2_IP:/opt/ui-automation/
rsync -az -e "ssh -o StrictHostKeyChecking=no -i $KEY_PATH" \
  --exclude='__pycache__/' --exclude='logs/' \
  ui-automation-proxy/ ubuntu@$EC2_IP:/opt/ui-automation/ui-automation-proxy/

# Copy proxy file to root
ssh -o StrictHostKeyChecking=no -i "$KEY_PATH" ubuntu@$EC2_IP << 'EOF'
  cp /opt/ui-automation/ui-automation-proxy/proxy_automation_complete.py /opt/ui-automation/
  chmod +x /opt/ui-automation/proxy_automation_complete.py
EOF

echo -e "\n${BLUE}🔧 Setting up services...${NC}"

# Create systemd services
ssh -o StrictHostKeyChecking=no -i "$KEY_PATH" ubuntu@$EC2_IP << 'EOF'

# Create directories
sudo mkdir -p /opt/smartbuild/sessions/active /opt/smartbuild/sessions/deleted
sudo chown -R ubuntu:ubuntu /opt/smartbuild /opt/smartmonitor /opt/job_queue_control /opt/ui-automation

# Main App Service
sudo tee /etc/systemd/system/smartbuild.service > /dev/null << 'SERVICE'
[Unit]
Description=SmartBuild Main Application
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/opt/smartbuild
Environment="PATH=/home/ubuntu/.local/bin:/usr/local/bin:/usr/bin"
ExecStart=/home/ubuntu/.local/bin/streamlit run smartbuild_spa_middleware_dynamic.py --server.port 8505 --server.address 0.0.0.0
Restart=always

[Install]
WantedBy=multi-user.target
SERVICE

# Job Queue Monitor
sudo tee /etc/systemd/system/job-queue-monitor.service > /dev/null << 'SERVICE'
[Unit]
Description=SmartBuild Job Queue Monitor
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/opt/smartbuild
ExecStart=/usr/bin/python3 job_queue_monitor.py
Restart=always

[Install]
WantedBy=multi-user.target
SERVICE

# Job Monitor UI
sudo tee /etc/systemd/system/smartmonitor.service > /dev/null << 'SERVICE'
[Unit]
Description=SmartBuild Job Monitor UI
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/opt/smartmonitor
Environment="PATH=/home/ubuntu/.local/bin:/usr/local/bin:/usr/bin"
ExecStart=/home/ubuntu/.local/bin/streamlit run smartbuild_monitor.py --server.port 8504 --server.address 0.0.0.0
Restart=always

[Install]
WantedBy=multi-user.target
SERVICE

# Control Center
sudo tee /etc/systemd/system/job-queue-control.service > /dev/null << 'SERVICE'
[Unit]
Description=SmartBuild Control Center
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/opt/job_queue_control
Environment="PATH=/home/ubuntu/.local/bin:/usr/local/bin:/usr/bin"
ExecStart=/home/ubuntu/.local/bin/streamlit run job_queue_control.py --server.port 8507 --server.address 0.0.0.0
Restart=always

[Install]
WantedBy=multi-user.target
SERVICE

# UI Automation
sudo tee /etc/systemd/system/ui-automation.service > /dev/null << 'SERVICE'
[Unit]
Description=SmartBuild UI Automation
After=network.target smartbuild.service

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/opt/ui-automation
Environment="PATH=/home/ubuntu/.local/bin:/usr/local/bin:/usr/bin"
ExecStart=/home/ubuntu/.local/bin/streamlit run proxy_automation_complete.py --server.port 8512 --server.address 0.0.0.0
Restart=always

[Install]
WantedBy=multi-user.target
SERVICE

# Reload and restart services
sudo systemctl daemon-reload
sudo systemctl enable smartbuild job-queue-monitor smartmonitor job-queue-control ui-automation

# Stop and restart in correct order
sudo systemctl stop smartbuild smartmonitor job-queue-control ui-automation 2>/dev/null || true
sudo systemctl stop job-queue-monitor 2>/dev/null || true
rm -f /opt/smartbuild/sessions/.job_queue_monitor.lock

sudo systemctl start job-queue-monitor
sleep 2
sudo systemctl start smartbuild
sudo systemctl start smartmonitor
sudo systemctl start job-queue-control
sudo systemctl start ui-automation

echo "Services restarted"
EOF

echo -e "\n${BLUE}✅ Verifying deployment...${NC}"

# Check services
ssh -o StrictHostKeyChecking=no -i "$KEY_PATH" ubuntu@$EC2_IP << 'EOF'
echo "Service Status:"
for service in smartbuild job-queue-monitor smartmonitor job-queue-control ui-automation; do
  status=$(systemctl is-active $service)
  if [ "$status" = "active" ]; then
    echo "✅ $service: active"
  else
    echo "❌ $service: $status"
  fi
done

echo ""
echo "Ports:"
sudo ss -tlnp | grep -E "8504|8505|8507|8512" | awk '{print "✅ Port " $4}'
EOF

echo -e "\n${GREEN}========================================${NC}"
echo -e "${GREEN}✅ DEPLOYMENT COMPLETE!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo "Applications available at:"
echo "  Main:     http://98.83.207.85:8505  (https://d10z4f7h6vaz0k.cloudfront.net)"
echo "  Monitor:  http://98.83.207.85:8504  (https://d1b2mw2j81ms4x.cloudfront.net)"
echo "  Control:  http://98.83.207.85:8507  (https://d23i1hoblpve1z.cloudfront.net)"
echo "  UI Auto:  http://98.83.207.85:8512  (https://d2hvw4a6x4umux.cloudfront.net)"

# Clean up temp key
rm -f ~/smartbuild-key.pem