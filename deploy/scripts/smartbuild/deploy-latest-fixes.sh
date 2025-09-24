#!/bin/bash
# ============================================================
# SmartBuild Deployment Script - Latest Fixes (2025-08-30)
# Version: 5.11.3
# ============================================================
# This script deploys the latest fixes including:
# - Requirements/Architecture jobs using main tmux session
# - Enhanced deletion logging
# - Prevention of tmux recreation after deletion
# - Job queue persistence fixes
# ============================================================

# Configuration
EC2_IP="98.83.207.85"
KEY_PATH="smartbuild-20250824180036.pem"
LOCAL_PATH="/home/development/python/aws/sunware-tech/devgenious/claude-code-chat"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}==================================================${NC}"
echo -e "${GREEN}   SmartBuild Latest Fixes Deployment${NC}"
echo -e "${GREEN}   Version: 5.11.3 - $(date)${NC}"
echo -e "${GREEN}==================================================${NC}"

# Check if key file exists
if [ ! -f "$KEY_PATH" ]; then
    echo -e "${RED}Error: SSH key file not found at $KEY_PATH${NC}"
    exit 1
fi

# Set proper permissions for key
chmod 400 "$KEY_PATH"

echo -e "\n${YELLOW}📦 Deploying to EC2 instance: $EC2_IP${NC}"

# Create deployment package with critical files
echo -e "${YELLOW}Creating deployment package...${NC}"
cat > /tmp/deploy_files.txt << 'EOF'
smartbuild_spa_middleware.py
smartbuild_monitor.py
utils/job_queue_manager_v2.py
utils/job_queue_manager.py
utils/common_types.py
utils/claude_session_manager.py
utils/prompt_preparers.py
utils/tab_implementations.py
utils/env_status_tracker.py
utils/supervisor_state.py
utils/session_logger.py
utils/simple_progress.py
utils/comprehensive_xml_cleaner.py
utils/tmux_recovery.py
version_config.py
requirements.txt
EOF

# Deploy to EC2
echo -e "\n${YELLOW}🚀 Deploying files to EC2...${NC}"

# Stop services first
ssh -i "$KEY_PATH" ubuntu@"$EC2_IP" << 'EOF'
    echo "Stopping services..."
    sudo systemctl stop smartbuild || true
    sudo systemctl stop smartmonitor || true
    sleep 2
EOF

# Deploy files to BOTH locations
while read file; do
    if [ -f "$LOCAL_PATH/$file" ]; then
        echo "  Uploading: $file"
        # Deploy to main app location
        scp -i "$KEY_PATH" "$LOCAL_PATH/$file" ubuntu@"$EC2_IP":/tmp/
        ssh -i "$KEY_PATH" ubuntu@"$EC2_IP" sudo cp "/tmp/$(basename $file)" "/opt/smartbuild/$file"
        # Deploy to monitor location
        ssh -i "$KEY_PATH" ubuntu@"$EC2_IP" sudo cp "/tmp/$(basename $file)" "/opt/smartmonitor/$file"
    fi
done < /tmp/deploy_files.txt

# Deploy utils directory
echo -e "\n${YELLOW}📁 Deploying utils directory...${NC}"
scp -i "$KEY_PATH" -r "$LOCAL_PATH/utils" ubuntu@"$EC2_IP":/tmp/
ssh -i "$KEY_PATH" ubuntu@"$EC2_IP" << 'EOF'
    sudo cp -r /tmp/utils/* /opt/smartbuild/utils/
    sudo cp -r /tmp/utils/* /opt/smartmonitor/utils/
    sudo chown -R ubuntu:ubuntu /opt/smartbuild/
    sudo chown -R ubuntu:ubuntu /opt/smartmonitor/
EOF

# Update version and restart services
echo -e "\n${YELLOW}🔄 Restarting services...${NC}"
ssh -i "$KEY_PATH" ubuntu@"$EC2_IP" << 'EOF'
    # Copy the full version_config.py file (already uploaded)
    sudo cp /tmp/version_config.py /opt/smartbuild/version_config.py
    sudo cp /tmp/version_config.py /opt/smartmonitor/version_config.py
    
    # Clear any stale lock files
    rm -f /opt/smartbuild/sessions/.job_queue_monitor.lock 2>/dev/null || true
    
    # Kill any orphaned tmux sessions from deleted sessions
    echo "Cleaning up orphaned tmux sessions..."
    for session in $(tmux ls 2>/dev/null | cut -d: -f1); do
        session_id=${session#smartbuild_s_}
        if [[ "$session" == "smartbuild_s_"* ]]; then
            if [ ! -d "/opt/smartbuild/sessions/active/session_${session_id}"* ]; then
                tmux kill-session -t "$session" 2>/dev/null || true
                echo "  Killed orphaned session: $session"
            fi
        fi
    done
    
    # Restart services
    sudo systemctl start smartbuild
    sudo systemctl start smartmonitor
    sleep 3
    
    # Check status
    echo -e "\n✅ Service Status:"
    sudo systemctl status smartbuild --no-pager | head -10
    sudo systemctl status smartmonitor --no-pager | head -10
EOF

# Verify deployment
echo -e "\n${YELLOW}✅ Verifying deployment...${NC}"
ssh -i "$KEY_PATH" ubuntu@"$EC2_IP" << 'EOF'
    echo "Main App Version:"
    grep VERSION /opt/smartbuild/version_config.py
    
    echo -e "\nMonitor App Version:"
    grep VERSION /opt/smartmonitor/version_config.py
    
    echo -e "\nRunning processes:"
    ps aux | grep streamlit | grep -v grep
    
    echo -e "\nActive tmux sessions:"
    tmux ls 2>/dev/null || echo "No tmux sessions running"
EOF

echo -e "\n${GREEN}==================================================${NC}"
echo -e "${GREEN}✅ Deployment Complete!${NC}"
echo -e "${GREEN}==================================================${NC}"
echo -e "\nAccess the applications at:"
echo -e "  Main App: ${GREEN}https://d10z4f7h6vaz0k.cloudfront.net/${NC}"
echo -e "  Monitor:  ${GREEN}https://d1b2mw2j81ms4x.cloudfront.net/${NC}"
echo -e "\nSSH Access:"
echo -e "  ${YELLOW}ssh -i $KEY_PATH ubuntu@$EC2_IP${NC}"
echo -e "\nLogs:"
echo -e "  Main: ${YELLOW}sudo journalctl -u smartbuild -f${NC}"
echo -e "  Monitor: ${YELLOW}sudo journalctl -u smartmonitor -f${NC}"