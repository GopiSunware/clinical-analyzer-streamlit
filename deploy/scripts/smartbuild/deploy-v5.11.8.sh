#!/bin/bash

# SmartBuild v5.11.8 Deployment Script
# Includes: Progress Probing (V3), Task ID Correlation (V4), Agent Prompts
# Date: 2025-01-31

set -e  # Exit on error

# Configuration
EC2_IP="98.83.207.85"
PEM_FILE="smartbuild-20250824180036.pem"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
VERSION="5.11.8"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}🚀 SmartBuild v${VERSION} Deployment${NC}"
echo -e "${GREEN}========================================${NC}"
echo "Target: $EC2_IP"
echo "Time: $(date)"
echo ""

# Check PEM file exists
if [ ! -f "$PEM_FILE" ]; then
    echo -e "${RED}❌ PEM file not found: $PEM_FILE${NC}"
    exit 1
fi

# Function to execute SSH commands
ssh_exec() {
    ssh -o StrictHostKeyChecking=no -i "$PEM_FILE" ubuntu@"$EC2_IP" "$@"
}

# Function to copy files
scp_copy() {
    scp -o StrictHostKeyChecking=no -i "$PEM_FILE" "$@"
}

# Step 1: Create backup
echo -e "${YELLOW}📦 Step 1: Creating backup...${NC}"
ssh_exec << 'EOF'
    sudo mkdir -p /opt/backups
    BACKUP_FILE="/opt/backups/smartbuild_backup_$(date +%Y%m%d_%H%M%S).tar.gz"
    
    # Create backup of critical directories
    sudo tar -czf "$BACKUP_FILE" \
        /opt/smartbuild/utils \
        /opt/smartbuild/.claude \
        /opt/smartmonitor/utils \
        2>/dev/null || true
    
    echo "Backup created: $BACKUP_FILE"
    
    # Keep only last 5 backups
    cd /opt/backups
    ls -t smartbuild_backup_*.tar.gz | tail -n +6 | xargs -r sudo rm
EOF

# Step 2: Stop services
echo -e "${YELLOW}🛑 Step 2: Stopping services...${NC}"
ssh_exec "sudo systemctl stop smartbuild smartmonitor"
sleep 2

# Step 3: Deploy .claude directory (including agents)
echo -e "${YELLOW}📤 Step 3: Deploying agent prompts...${NC}"

# Check if .claude directory exists locally
if [ -d "../.claude" ]; then
    # Clean up Zone.Identifier files locally first
    find ../.claude -name "*:Zone.Identifier*" -delete 2>/dev/null || true
    
    # Copy .claude directory
    scp_copy -r ../.claude ubuntu@"$EC2_IP":/tmp/
    
    ssh_exec << 'EOF'
        # Create directory structure
        sudo mkdir -p /opt/smartbuild/.claude/agents
        sudo mkdir -p /opt/smartbuild/.claude/commands
        
        # Copy agent files
        if [ -d /tmp/.claude/agents ]; then
            sudo cp /tmp/.claude/agents/*.md /opt/smartbuild/.claude/agents/ 2>/dev/null || true
            sudo cp /tmp/.claude/agents/*.drawio /opt/smartbuild/.claude/agents/ 2>/dev/null || true
            echo "✅ Agent files deployed"
        fi
        
        # Copy settings if exists
        if [ -f /tmp/.claude/settings.local.json ]; then
            sudo cp /tmp/.claude/settings.local.json /opt/smartbuild/.claude/
            echo "✅ Settings deployed"
        fi
        
        # Set permissions
        sudo chown -R ubuntu:ubuntu /opt/smartbuild/.claude
        sudo chmod -R 755 /opt/smartbuild/.claude
        
        # List deployed agents
        echo "Deployed agents:"
        ls -la /opt/smartbuild/.claude/agents/*.md 2>/dev/null | wc -l
EOF
else
    echo -e "${YELLOW}⚠️  .claude directory not found locally, skipping...${NC}"
fi

# Step 4: Deploy utilities (CRITICAL - to both locations)
echo -e "${YELLOW}📤 Step 4: Deploying utilities...${NC}"

if [ -d "../utils" ]; then
    scp_copy -r ../utils ubuntu@"$EC2_IP":/tmp/
    
    ssh_exec << 'EOF'
        # Deploy to smartbuild
        sudo cp -r /tmp/utils/* /opt/smartbuild/utils/
        sudo chown -R ubuntu:ubuntu /opt/smartbuild/utils
        
        # Deploy to smartmonitor (CRITICAL for shared functionality)
        sudo cp -r /tmp/utils/* /opt/smartmonitor/utils/
        sudo chown -R ubuntu:ubuntu /opt/smartmonitor/utils
        
        # Verify V3/V4 files
        echo "Job queue versions deployed:"
        ls /opt/smartbuild/utils/job_queue_manager_v*.py
        
        # Check for new modules
        [ -f /opt/smartbuild/utils/claude_progress_prober.py ] && echo "✅ Progress prober deployed"
        [ -f /opt/smartbuild/utils/prompt_enhancer.py ] && echo "✅ Task ID enhancer deployed"
        [ -f /opt/smartbuild/utils/progress_display_components.py ] && echo "✅ Display components deployed"
EOF
else
    echo -e "${RED}❌ Utils directory not found!${NC}"
    exit 1
fi

# Step 5: Deploy main applications
echo -e "${YELLOW}📤 Step 5: Deploying applications...${NC}"

# Deploy enhanced monitor if exists
if [ -f "../smartbuild_monitor_enhanced.py" ]; then
    scp_copy ../smartbuild_monitor_enhanced.py ubuntu@"$EC2_IP":/tmp/
    ssh_exec "sudo cp /tmp/smartbuild_monitor_enhanced.py /opt/smartmonitor/ && sudo chown ubuntu:ubuntu /opt/smartmonitor/smartbuild_monitor_enhanced.py"
    echo "✅ Enhanced monitor deployed"
fi

# Deploy version config
if [ -f "../version_config.py" ]; then
    scp_copy ../version_config.py ubuntu@"$EC2_IP":/tmp/
    ssh_exec << 'EOF'
        sudo cp /tmp/version_config.py /opt/smartbuild/
        sudo cp /tmp/version_config.py /opt/smartmonitor/
        sudo chown ubuntu:ubuntu /opt/smartbuild/version_config.py
        sudo chown ubuntu:ubuntu /opt/smartmonitor/version_config.py
EOF
    echo "✅ Version config deployed"
fi

# Step 6: Clear any stale lock files
echo -e "${YELLOW}🧹 Step 6: Clearing lock files...${NC}"
ssh_exec << 'EOF'
    # Remove job queue monitor lock if exists
    sudo rm -f /opt/smartbuild/sessions/.job_queue_monitor.lock
    sudo rm -f /opt/smartbuild/sessions/active/.job_queue_monitor.lock
    
    # Kill any orphaned tmux sessions
    tmux ls 2>/dev/null | grep -E "^(sb_|smartbuild_)" | cut -d: -f1 | xargs -r -I {} tmux kill-session -t {} 2>/dev/null || true
    
    echo "✅ Lock files cleared"
EOF

# Step 7: Restart services
echo -e "${YELLOW}🔄 Step 7: Restarting services...${NC}"
ssh_exec << 'EOF'
    sudo systemctl restart smartbuild
    sleep 2
    sudo systemctl restart smartmonitor
    
    # Check status
    echo "Service status:"
    sudo systemctl is-active smartbuild smartmonitor
EOF

# Step 8: Verify deployment
echo -e "${YELLOW}✅ Step 8: Verifying deployment...${NC}"
ssh_exec << 'EOF'
    echo "=== Deployment Verification ==="
    
    # Check for V3/V4 initialization
    echo -n "Checking for V3/V4 in logs: "
    sudo journalctl -u smartbuild -n 100 | grep -E "JOB QUEUE V[34]" | head -1 || echo "Not yet initialized"
    
    # Check agent files
    echo -n "Agent files: "
    ls /opt/smartbuild/.claude/agents/*.md 2>/dev/null | wc -l
    
    # Check new utils
    echo "New modules:"
    [ -f /opt/smartbuild/utils/job_queue_manager_v3.py ] && echo "  ✓ V3 (Progress Probing)"
    [ -f /opt/smartbuild/utils/job_queue_manager_v4.py ] && echo "  ✓ V4 (Task ID Correlation)"
    [ -f /opt/smartbuild/utils/claude_progress_prober.py ] && echo "  ✓ Progress Prober"
    [ -f /opt/smartbuild/utils/prompt_enhancer.py ] && echo "  ✓ Task ID Enhancer"
    
    # Check which version is active
    echo -n "Active version: "
    grep -o "job_queue_manager_v[0-9]" /opt/smartbuild/utils/job_queue_manager.py | head -1 || echo "Unknown"
    
    # Recent errors
    echo "Recent errors (if any):"
    sudo journalctl -u smartbuild -p err -n 5 --no-pager
EOF

# Step 9: Test endpoints
echo -e "${YELLOW}🌐 Step 9: Testing endpoints...${NC}"
echo "Testing main app..."
curl -s -o /dev/null -w "HTTP Status: %{http_code}\n" http://$EC2_IP:80 || true

echo "Testing monitor..."
curl -s -o /dev/null -w "HTTP Status: %{http_code}\n" http://$EC2_IP:8504 || true

# Final summary
echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}🎉 Deployment Complete!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo "📊 Monitor: http://$EC2_IP:8504"
echo "🏗️ Main App: http://$EC2_IP:80"
echo "📡 CloudFront Main: https://d10z4f7h6vaz0k.cloudfront.net/"
echo "📡 CloudFront Monitor: https://d1b2mw2j81ms4x.cloudfront.net/"
echo ""
echo -e "${YELLOW}📝 Next Steps:${NC}"
echo "1. Check monitor for V3 progress probing"
echo "2. To activate V4 (Task ID), SSH and edit job_queue_manager.py"
echo "3. Monitor logs: ssh -i $PEM_FILE ubuntu@$EC2_IP 'sudo journalctl -u smartbuild -f'"
echo ""
echo "✅ Version $VERSION deployed successfully!"