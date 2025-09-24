#!/bin/bash

# SmartBuild Complete Suite Deployment Script
# Deploys all 4 applications to EC2
# Last Updated: December 2024

set -e  # Exit on error

# Configuration
KEY_PATH="deploy/keys/smartbuild-20250824180036.pem"
EC2_IP="98.83.207.85"
EC2_USER="ubuntu"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  SmartBuild Suite Deployment to EC2${NC}"
echo -e "${BLUE}========================================${NC}"
echo -e "Target: ${GREEN}$EC2_IP${NC}"
echo -e "Time: $(date)"
echo ""

# Check if key file exists
if [ ! -f "$KEY_PATH" ]; then
    echo -e "${RED}❌ Error: SSH key not found at $KEY_PATH${NC}"
    exit 1
fi

# Set key permissions
chmod 400 $KEY_PATH

# Function to check SSH connection
check_ssh() {
    echo -e "${YELLOW}Checking SSH connection...${NC}"
    if ssh -o ConnectTimeout=5 -i "$KEY_PATH" "$EC2_USER@$EC2_IP" "echo 'SSH OK'" > /dev/null 2>&1; then
        echo -e "${GREEN}✅ SSH connection successful${NC}"
    else
        echo -e "${RED}❌ Cannot connect to EC2. Please check your connection.${NC}"
        exit 1
    fi
}

# Check SSH first
check_ssh

echo -e "\n${BLUE}📦 Step 1: Deploying Main Application & Core Files${NC}"
echo "------------------------------------------------"

# Deploy main application
rsync -avz --delete \
  -e "ssh -i $KEY_PATH" \
  --exclude='sessions/' \
  --exclude='__pycache__/' \
  --exclude='*.pyc' \
  --exclude='.git/' \
  --exclude='logs/' \
  --exclude='tests/' \
  --exclude='deploy/' \
  --exclude='archive/' \
  --exclude='.gitignore' \
  --include='smartbuild_spa_middleware_dynamic.py' \
  --include='job_queue_monitor.py' \
  --include='utils/**' \
  --include='config/**' \
  --include='.claude/**' \
  --include='requirements.txt' \
  --include='version_config.py' \
  smartbuild_spa_middleware_dynamic.py \
  job_queue_monitor.py \
  version_config.py \
  requirements.txt \
  utils \
  config \
  .claude \
  $EC2_USER@$EC2_IP:/opt/smartbuild/

echo -e "${GREEN}✅ Main application deployed${NC}"

echo -e "\n${BLUE}📦 Step 2: Deploying Job Monitor UI${NC}"
echo "------------------------------------------------"

# Deploy Job Monitor
ssh -i "$KEY_PATH" "$EC2_USER@$EC2_IP" "mkdir -p /opt/smartmonitor"
rsync -avz \
  -e "ssh -i $KEY_PATH" \
  smartbuild_monitor.py \
  $EC2_USER@$EC2_IP:/opt/smartmonitor/

# Copy utils to smartmonitor
rsync -avz \
  -e "ssh -i $KEY_PATH" \
  utils \
  $EC2_USER@$EC2_IP:/opt/smartmonitor/

echo -e "${GREEN}✅ Job Monitor deployed${NC}"

echo -e "\n${BLUE}📦 Step 3: Deploying Control Center${NC}"
echo "------------------------------------------------"

# Deploy Control Center
ssh -i "$KEY_PATH" "$EC2_USER@$EC2_IP" "mkdir -p /opt/job_queue_control"
rsync -avz \
  -e "ssh -i $KEY_PATH" \
  job_queue_control.py \
  $EC2_USER@$EC2_IP:/opt/job_queue_control/

# Copy utils to control center
rsync -avz \
  -e "ssh -i $KEY_PATH" \
  utils \
  $EC2_USER@$EC2_IP:/opt/job_queue_control/

echo -e "${GREEN}✅ Control Center deployed${NC}"

echo -e "\n${BLUE}📦 Step 4: Deploying UI Automation (NEW Version with Iframe)${NC}"
echo "------------------------------------------------"

# Deploy UI Automation
ssh -i "$KEY_PATH" "$EC2_USER@$EC2_IP" "mkdir -p /opt/ui-automation/ui-automation-proxy"

# Deploy original UI automation files
rsync -avz \
  -e "ssh -i $KEY_PATH" \
  --exclude='__pycache__/' \
  --exclude='*.pyc' \
  --exclude='logs/' \
  --exclude='videos/' \
  ui-automation/ \
  $EC2_USER@$EC2_IP:/opt/ui-automation/

# Deploy new proxy automation files
rsync -avz \
  -e "ssh -i $KEY_PATH" \
  --exclude='__pycache__/' \
  --exclude='*.pyc' \
  --exclude='logs/' \
  --exclude='videos/' \
  ui-automation-proxy/ \
  $EC2_USER@$EC2_IP:/opt/ui-automation/ui-automation-proxy/

# Copy the main proxy file to root for easier access
ssh -i "$KEY_PATH" "$EC2_USER@$EC2_IP" << 'EOF'
  cp /opt/ui-automation/ui-automation-proxy/proxy_automation_complete.py /opt/ui-automation/
  chmod +x /opt/ui-automation/proxy_automation_complete.py

  # Create logs directories
  mkdir -p /opt/ui-automation/logs
  mkdir -p /opt/ui-automation/ui-automation-proxy/logs
EOF

echo -e "${GREEN}✅ UI Automation deployed${NC}"

echo -e "\n${BLUE}🔧 Step 5: Creating Session Directories${NC}"
echo "------------------------------------------------"

ssh -i "$KEY_PATH" "$EC2_USER@$EC2_IP" << 'EOF'
  # Create session directories for all apps
  sudo mkdir -p /opt/smartbuild/sessions/active
  sudo mkdir -p /opt/smartbuild/sessions/deleted
  sudo mkdir -p /opt/smartmonitor/sessions/active
  sudo mkdir -p /opt/job_queue_control/sessions/active
  sudo mkdir -p /opt/ui-automation/sessions/active

  # Set permissions
  sudo chown -R ubuntu:ubuntu /opt/smartbuild
  sudo chown -R ubuntu:ubuntu /opt/smartmonitor
  sudo chown -R ubuntu:ubuntu /opt/job_queue_control
  sudo chown -R ubuntu:ubuntu /opt/ui-automation
EOF

echo -e "${GREEN}✅ Directories created${NC}"

echo -e "\n${BLUE}🔧 Step 6: Installing Python Dependencies${NC}"
echo "------------------------------------------------"

ssh -i "$KEY_PATH" "$EC2_USER@$EC2_IP" << 'EOF'
  # Install required Python packages
  pip install --upgrade pip
  pip install streamlit pandas plotly streamlit-autorefresh
  pip install playwright websockets aiohttp

  # Install Playwright browsers for UI automation
  cd /opt/ui-automation
  python -m playwright install chromium
  python -m playwright install-deps
EOF

echo -e "${GREEN}✅ Dependencies installed${NC}"

echo -e "\n${BLUE}🔧 Step 7: Setting up Systemd Services${NC}"
echo "------------------------------------------------"

# Create all systemd service files
ssh -i "$KEY_PATH" "$EC2_USER@$EC2_IP" << 'EOF'

# 1. Main Application Service
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
RestartSec=10

[Install]
WantedBy=multi-user.target
SERVICE

# 2. Job Queue Monitor Service (Background)
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
RestartSec=10

[Install]
WantedBy=multi-user.target
SERVICE

# 3. Job Monitor UI Service
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
RestartSec=10

[Install]
WantedBy=multi-user.target
SERVICE

# 4. Control Center Service
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
RestartSec=10

[Install]
WantedBy=multi-user.target
SERVICE

# 5. UI Automation Service (NEW)
sudo tee /etc/systemd/system/ui-automation.service > /dev/null << 'SERVICE'
[Unit]
Description=SmartBuild UI Automation with Iframe Proxy
After=network.target smartbuild.service

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/opt/ui-automation
Environment="PATH=/home/ubuntu/.local/bin:/usr/local/bin:/usr/bin"
Environment="DISPLAY=:99"
ExecStart=/home/ubuntu/.local/bin/streamlit run proxy_automation_complete.py --server.port 8512 --server.address 0.0.0.0
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
SERVICE

# Reload systemd
sudo systemctl daemon-reload

# Enable all services
sudo systemctl enable smartbuild.service
sudo systemctl enable job-queue-monitor.service
sudo systemctl enable smartmonitor.service
sudo systemctl enable job-queue-control.service
sudo systemctl enable ui-automation.service

echo "✅ All services configured"
EOF

echo -e "${GREEN}✅ Systemd services created${NC}"

echo -e "\n${BLUE}🚀 Step 8: Starting All Services${NC}"
echo "------------------------------------------------"

ssh -i "$KEY_PATH" "$EC2_USER@$EC2_IP" << 'EOF'
  # Stop any existing services
  echo "Stopping existing services..."
  sudo systemctl stop smartbuild smartmonitor job-queue-control ui-automation 2>/dev/null || true
  sudo systemctl stop job-queue-monitor 2>/dev/null || true

  # Remove any stale lock files
  rm -f /opt/smartbuild/sessions/.job_queue_monitor.lock

  # Start services in correct order
  echo "Starting services..."
  sudo systemctl start job-queue-monitor
  sleep 3
  sudo systemctl start smartbuild
  sleep 2
  sudo systemctl start smartmonitor
  sudo systemctl start job-queue-control
  sudo systemctl start ui-automation

  echo "✅ All services started"
EOF

echo -e "${GREEN}✅ Services started${NC}"

echo -e "\n${BLUE}✅ Step 9: Verification${NC}"
echo "------------------------------------------------"

# Verify services are running
ssh -i "$KEY_PATH" "$EC2_USER@$EC2_IP" << 'EOF'
  echo "Service Status:"
  echo "---------------"
  for service in smartbuild job-queue-monitor smartmonitor job-queue-control ui-automation; do
    status=$(systemctl is-active $service)
    if [ "$status" = "active" ]; then
      echo "✅ $service: $status"
    else
      echo "❌ $service: $status"
    fi
  done

  echo ""
  echo "Port Status:"
  echo "------------"
  sudo ss -tlnp | grep -E "8504|8505|8507|8512" | while read line; do
    port=$(echo $line | grep -oE ':[0-9]+' | head -1 | tr -d ':')
    echo "✅ Port $port is listening"
  done
EOF

echo -e "\n${GREEN}========================================${NC}"
echo -e "${GREEN}  ✅ DEPLOYMENT COMPLETE!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo -e "Access your applications at:"
echo -e "${BLUE}Main App:${NC}        http://$EC2_IP:8505  OR  https://d10z4f7h6vaz0k.cloudfront.net"
echo -e "${BLUE}Job Monitor:${NC}     http://$EC2_IP:8504  OR  https://d1b2mw2j81ms4x.cloudfront.net"
echo -e "${BLUE}Control Center:${NC}  http://$EC2_IP:8507  OR  https://d23i1hoblpve1z.cloudfront.net"
echo -e "${BLUE}UI Automation:${NC}   http://$EC2_IP:8512  OR  https://d2hvw4a6x4umux.cloudfront.net"
echo ""
echo -e "To view logs: ${YELLOW}ssh -i $KEY_PATH $EC2_USER@$EC2_IP 'sudo journalctl -u SERVICE_NAME -f'${NC}"
echo -e "Deployment completed at: $(date)"