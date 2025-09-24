#!/bin/bash
# ============================================================
# SmartBuild New Monitors Deployment Script
# Version: 5.11.9
# Deploys Console Log Monitor (8506) and Job Queue Control UI (8507)
# ============================================================

# Configuration
EC2_IP="98.83.207.85"
KEY_PATH="smartbuild-20250824180036.pem"
LOCAL_PATH="/home/development/python/aws/sunware-tech/devgenious/claude-code-chat"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${GREEN}==================================================${NC}"
echo -e "${GREEN}   SmartBuild New Monitors Deployment${NC}"
echo -e "${GREEN}   Version: 5.11.9 - $(date)${NC}"
echo -e "${GREEN}==================================================${NC}"

# Check if key file exists
if [ ! -f "$KEY_PATH" ]; then
    echo -e "${RED}Error: SSH key file not found at $KEY_PATH${NC}"
    exit 1
fi

# Set proper permissions for key
chmod 400 "$KEY_PATH"

echo -e "\n${YELLOW}📦 Deploying new monitoring tools to EC2: $EC2_IP${NC}"

# Step 1: Create directories on EC2
echo -e "\n${BLUE}📁 Creating directories on EC2...${NC}"
ssh -i "$KEY_PATH" ubuntu@"$EC2_IP" << 'EOF'
    # Create directories for new monitors if they don't exist
    sudo mkdir -p /opt/console_log_monitor
    sudo mkdir -p /opt/job_queue_control
    sudo chown -R ubuntu:ubuntu /opt/console_log_monitor
    sudo chown -R ubuntu:ubuntu /opt/job_queue_control
EOF

# Step 2: Deploy monitoring files
echo -e "\n${BLUE}📤 Uploading monitoring files...${NC}"

# Deploy Console Log Monitor (Development version)
echo "  Uploading: console_log_monitor_dev.py"
scp -i "$KEY_PATH" "$LOCAL_PATH/console_log_monitor_dev.py" ubuntu@"$EC2_IP":/tmp/
ssh -i "$KEY_PATH" ubuntu@"$EC2_IP" \
    "sudo cp /tmp/console_log_monitor_dev.py /opt/console_log_monitor/console_log_monitor.py"

# Deploy Job Queue Control UI
echo "  Uploading: job_queue_monitor_control_ui.py"
scp -i "$KEY_PATH" "$LOCAL_PATH/job_queue_monitor_control_ui.py" ubuntu@"$EC2_IP":/tmp/
ssh -i "$KEY_PATH" ubuntu@"$EC2_IP" \
    "sudo cp /tmp/job_queue_monitor_control_ui.py /opt/job_queue_control/job_queue_control.py"

# Deploy monitor control script
echo "  Uploading: monitor_control_dev.py"
scp -i "$KEY_PATH" "$LOCAL_PATH/monitor_control_dev.py" ubuntu@"$EC2_IP":/tmp/
ssh -i "$KEY_PATH" ubuntu@"$EC2_IP" \
    "sudo cp /tmp/monitor_control_dev.py /opt/smartbuild/monitor_control.py"

# Step 3: Copy utils directory to both new locations
echo -e "\n${BLUE}📁 Deploying utils directory...${NC}"
scp -i "$KEY_PATH" -r "$LOCAL_PATH/utils" ubuntu@"$EC2_IP":/tmp/
ssh -i "$KEY_PATH" ubuntu@"$EC2_IP" << 'EOF'
    # Copy utils to new monitor locations
    sudo cp -r /tmp/utils /opt/console_log_monitor/
    sudo cp -r /tmp/utils /opt/job_queue_control/
    
    # Set permissions
    sudo chown -R ubuntu:ubuntu /opt/console_log_monitor/
    sudo chown -R ubuntu:ubuntu /opt/job_queue_control/
EOF

# Step 4: Create systemd service files
echo -e "\n${BLUE}🔧 Creating systemd service files...${NC}"

# Create console-log-monitor service
ssh -i "$KEY_PATH" ubuntu@"$EC2_IP" << 'EOF'
cat << 'SERVICE' | sudo tee /etc/systemd/system/console-log-monitor.service
[Unit]
Description=SmartBuild Console Log Monitor
After=network.target smartbuild.service

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/opt/console_log_monitor
Environment="PATH=/usr/local/bin:/usr/bin:/bin"
ExecStart=/usr/local/bin/streamlit run console_log_monitor.py --server.port 8506 --server.headless true
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
SERVICE
EOF

# Create job-queue-control service
ssh -i "$KEY_PATH" ubuntu@"$EC2_IP" << 'EOF'
cat << 'SERVICE' | sudo tee /etc/systemd/system/job-queue-control.service
[Unit]
Description=SmartBuild Job Queue Control UI
After=network.target smartbuild.service

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/opt/job_queue_control
Environment="PATH=/usr/local/bin:/usr/bin:/bin"
ExecStart=/usr/local/bin/streamlit run job_queue_control.py --server.port 8507 --server.headless true
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
SERVICE
EOF

# Step 5: Update file paths in deployed scripts
echo -e "\n${BLUE}🔧 Updating file paths for production...${NC}"
ssh -i "$KEY_PATH" ubuntu@"$EC2_IP" << 'EOF'
    # Update paths in console_log_monitor.py
    sudo sed -i 's|sessions/active|/opt/smartbuild/sessions/active|g' /opt/console_log_monitor/console_log_monitor.py
    sudo sed -i 's|/tmp/streamlit.log|/var/log/smartbuild.log|g' /opt/console_log_monitor/console_log_monitor.py
    
    # Update paths in job_queue_control.py
    sudo sed -i 's|sessions/active|/opt/smartbuild/sessions/active|g' /opt/job_queue_control/job_queue_control.py
    sudo sed -i 's|sessions/.job_queue_monitor.lock|/opt/smartbuild/sessions/.job_queue_monitor.lock|g' /opt/job_queue_control/job_queue_control.py
    
    # Update paths in monitor_control.py
    sudo sed -i 's|sessions/.job_queue_monitor.lock|/opt/smartbuild/sessions/.job_queue_monitor.lock|g' /opt/smartbuild/monitor_control.py
EOF

# Step 6: Enable and start services
echo -e "\n${BLUE}🚀 Starting new monitoring services...${NC}"
ssh -i "$KEY_PATH" ubuntu@"$EC2_IP" << 'EOF'
    # Reload systemd daemon
    sudo systemctl daemon-reload
    
    # Enable services
    sudo systemctl enable console-log-monitor
    sudo systemctl enable job-queue-control
    
    # Stop existing services if running
    sudo systemctl stop console-log-monitor 2>/dev/null || true
    sudo systemctl stop job-queue-control 2>/dev/null || true
    
    # Start services
    sudo systemctl start console-log-monitor
    sudo systemctl start job-queue-control
    
    sleep 3
EOF

# Step 7: Verify deployment
echo -e "\n${YELLOW}✅ Verifying deployment...${NC}"
ssh -i "$KEY_PATH" ubuntu@"$EC2_IP" << 'EOF'
    echo -e "\n📊 Service Status:"
    echo "================================="
    
    echo -e "\n1. Main Application (Port 8505):"
    sudo systemctl is-active smartbuild || echo "Not running"
    
    echo -e "\n2. SmartBuild Monitor (Port 8504):"
    sudo systemctl is-active smartmonitor || echo "Not running"
    
    echo -e "\n3. Console Log Monitor (Port 8506):"
    sudo systemctl is-active console-log-monitor || echo "Not running"
    
    echo -e "\n4. Job Queue Control UI (Port 8507):"
    sudo systemctl is-active job-queue-control || echo "Not running"
    
    echo -e "\n📡 Port Status:"
    echo "================================="
    sudo netstat -tlnp | grep -E ':(8504|8505|8506|8507)' || echo "No ports listening"
    
    echo -e "\n📝 Recent Logs:"
    echo "================================="
    echo "Console Log Monitor:"
    sudo journalctl -u console-log-monitor --no-pager -n 5
    echo ""
    echo "Job Queue Control:"
    sudo journalctl -u job-queue-control --no-pager -n 5
EOF

echo -e "\n${GREEN}==================================================${NC}"
echo -e "${GREEN}✅ Deployment Complete!${NC}"
echo -e "${GREEN}==================================================${NC}"
echo -e "\n${YELLOW}📍 Access URLs:${NC}"
echo -e "  Main App (8505):          ${GREEN}https://d10z4f7h6vaz0k.cloudfront.net/${NC}"
echo -e "  Monitor (8504):           ${GREEN}https://d1b2mw2j81ms4x.cloudfront.net/${NC}"
echo -e "  Console Monitor (8506):   ${GREEN}http://$EC2_IP:8506${NC} (No CloudFront yet)"
echo -e "  Job Queue Control (8507): ${GREEN}http://$EC2_IP:8507${NC} (No CloudFront yet)"
echo -e "\n${YELLOW}📍 Direct EC2 Access:${NC}"
echo -e "  ${BLUE}http://$EC2_IP:8505${NC} - Main Application"
echo -e "  ${BLUE}http://$EC2_IP:8504${NC} - SmartBuild Monitor"
echo -e "  ${BLUE}http://$EC2_IP:8506${NC} - Console Log Monitor"
echo -e "  ${BLUE}http://$EC2_IP:8507${NC} - Job Queue Control UI"
echo -e "\n${YELLOW}🔧 Service Management:${NC}"
echo -e "  SSH: ${BLUE}ssh -i $KEY_PATH ubuntu@$EC2_IP${NC}"
echo -e "  Logs: ${BLUE}sudo journalctl -u console-log-monitor -f${NC}"
echo -e "        ${BLUE}sudo journalctl -u job-queue-control -f${NC}"
echo -e "  Restart: ${BLUE}sudo systemctl restart console-log-monitor${NC}"
echo -e "           ${BLUE}sudo systemctl restart job-queue-control${NC}"