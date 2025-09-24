#!/bin/bash

# Quick Redeployment Script
# Redeploys all SmartBuild applications with latest changes

set -e

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  SmartBuild Suite Redeployment${NC}"
echo -e "${BLUE}========================================${NC}"
echo -e "Time: $(date)"
echo ""

# Fix key permissions
echo -e "${YELLOW}Preparing SSH key...${NC}"
cp deploy/keys/smartbuild-20250824180036.pem ~/deploy-key.pem
chmod 400 ~/deploy-key.pem

KEY_PATH="$HOME/deploy-key.pem"
EC2_IP="98.83.207.85"

# Test connection
echo -e "${YELLOW}Testing connection to EC2...${NC}"
if ssh -o ConnectTimeout=5 -o StrictHostKeyChecking=no -i "$KEY_PATH" ubuntu@$EC2_IP "echo 'Connected'" > /dev/null 2>&1; then
    echo -e "${GREEN}✅ Connection successful${NC}"
else
    echo -e "${RED}❌ Connection failed${NC}"
    exit 1
fi

echo -e "\n${BLUE}📦 Redeploying Applications...${NC}"
echo "================================"

# 1. Main Application
echo -e "\n${YELLOW}[1/4] Main Application & Job Queue Monitor${NC}"
rsync -azP --delete \
  -e "ssh -o StrictHostKeyChecking=no -i $KEY_PATH" \
  --exclude='sessions/' \
  --exclude='__pycache__/' \
  --exclude='.git/' \
  --exclude='logs/' \
  --exclude='deploy/' \
  --exclude='tests/' \
  --exclude='env_*/' \
  --exclude='archive/' \
  --exclude='*.log' \
  smartbuild_spa_middleware_dynamic.py \
  job_queue_monitor.py \
  version_config.py \
  requirements.txt \
  utils \
  config \
  .claude \
  ubuntu@$EC2_IP:/opt/smartbuild/

echo -e "${GREEN}✅ Main app deployed${NC}"

# 2. Job Monitor
echo -e "\n${YELLOW}[2/4] Job Monitor UI${NC}"
rsync -azP \
  -e "ssh -o StrictHostKeyChecking=no -i $KEY_PATH" \
  smartbuild_monitor.py \
  ubuntu@$EC2_IP:/opt/smartmonitor/

# Also update utils for monitor
rsync -azP \
  -e "ssh -o StrictHostKeyChecking=no -i $KEY_PATH" \
  utils \
  ubuntu@$EC2_IP:/opt/smartmonitor/

echo -e "${GREEN}✅ Job Monitor deployed${NC}"

# 3. Control Center
echo -e "\n${YELLOW}[3/4] Control Center${NC}"
rsync -azP \
  -e "ssh -o StrictHostKeyChecking=no -i $KEY_PATH" \
  job_queue_control.py \
  ubuntu@$EC2_IP:/opt/job_queue_control/

# Update utils for control center
rsync -azP \
  -e "ssh -o StrictHostKeyChecking=no -i $KEY_PATH" \
  utils \
  ubuntu@$EC2_IP:/opt/job_queue_control/

echo -e "${GREEN}✅ Control Center deployed${NC}"

# 4. UI Automation (NEW VERSION)
echo -e "\n${YELLOW}[4/4] UI Automation with Proxy${NC}"
rsync -azP \
  -e "ssh -o StrictHostKeyChecking=no -i $KEY_PATH" \
  --exclude='__pycache__/' \
  --exclude='logs/' \
  --exclude='videos/' \
  --exclude='*.pyc' \
  ui-automation/ \
  ubuntu@$EC2_IP:/opt/ui-automation/

# Deploy proxy automation files
rsync -azP \
  -e "ssh -o StrictHostKeyChecking=no -i $KEY_PATH" \
  --exclude='__pycache__/' \
  --exclude='logs/' \
  --exclude='videos/' \
  --exclude='*.pyc' \
  ui-automation-proxy/ \
  ubuntu@$EC2_IP:/opt/ui-automation/ui-automation-proxy/

# Copy proxy file to root and set permissions
ssh -o StrictHostKeyChecking=no -i "$KEY_PATH" ubuntu@$EC2_IP << 'EOF'
  cp /opt/ui-automation/ui-automation-proxy/proxy_automation_complete.py /opt/ui-automation/
  chmod +x /opt/ui-automation/proxy_automation_complete.py

  # Ensure directories exist
  mkdir -p /opt/ui-automation/logs
  mkdir -p /opt/ui-automation/ui-automation-proxy/logs
  mkdir -p /opt/smartbuild/sessions/active
  mkdir -p /opt/smartbuild/sessions/deleted

  # Set permissions
  sudo chown -R ubuntu:ubuntu /opt/smartbuild
  sudo chown -R ubuntu:ubuntu /opt/smartmonitor
  sudo chown -R ubuntu:ubuntu /opt/job_queue_control
  sudo chown -R ubuntu:ubuntu /opt/ui-automation
EOF

echo -e "${GREEN}✅ UI Automation deployed${NC}"

echo -e "\n${BLUE}🔄 Restarting Services...${NC}"
echo "================================"

ssh -o StrictHostKeyChecking=no -i "$KEY_PATH" ubuntu@$EC2_IP << 'EOF'
  # Stop all services
  echo "Stopping services..."
  sudo systemctl stop smartbuild smartmonitor job-queue-control ui-automation 2>/dev/null || true
  sudo systemctl stop job-queue-monitor 2>/dev/null || true

  # Remove lock file
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

  echo "Services restarted"
EOF

echo -e "\n${BLUE}✅ Verification${NC}"
echo "================================"

# Verify services
ssh -o StrictHostKeyChecking=no -i "$KEY_PATH" ubuntu@$EC2_IP << 'EOF'
  echo "Service Status:"
  for service in smartbuild job-queue-monitor smartmonitor job-queue-control ui-automation; do
    status=$(systemctl is-active $service)
    if [ "$status" = "active" ]; then
      echo "✅ $service: active"
    else
      echo "❌ $service: $status"
      # Show error if service failed
      if [ "$status" != "active" ]; then
        echo "  Last error:"
        sudo journalctl -u $service -n 3 --no-pager | grep -E "ERROR|error" || echo "  No errors in recent logs"
      fi
    fi
  done

  echo ""
  echo "Port Status:"
  sudo ss -tlnp | grep -E "8504|8505|8507|8512" | while read line; do
    port=$(echo $line | grep -oE ':[0-9]+' | head -1 | tr -d ':')
    echo "✅ Port $port is listening"
  done

  echo ""
  echo "Disk Usage:"
  df -h /opt | tail -1
EOF

echo -e "\n${GREEN}========================================${NC}"
echo -e "${GREEN}  ✅ REDEPLOYMENT COMPLETE!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo "Access your applications:"
echo "  Main:     http://98.83.207.85:8505  (https://d10z4f7h6vaz0k.cloudfront.net)"
echo "  Monitor:  http://98.83.207.85:8504  (https://d1b2mw2j81ms4x.cloudfront.net)"
echo "  Control:  http://98.83.207.85:8507  (https://d23i1hoblpve1z.cloudfront.net)"
echo "  UI Auto:  http://98.83.207.85:8512  (https://d2hvw4a6x4umux.cloudfront.net)"
echo ""
echo "Redeployment completed at: $(date)"

# Clean up
rm -f ~/deploy-key.pem