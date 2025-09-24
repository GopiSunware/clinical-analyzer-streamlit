#!/bin/bash

# Deploy to BOTH smartbuild and smartmonitor folders
# This ensures both the main app and monitor have the same code
set -e

# Configuration
EC2_IP="${1:-98.83.207.85}"
KEY_PATH="./smartbuild-20250824180036.pem"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Deploy to BOTH SmartBuild & SmartMonitor${NC}"
echo -e "${GREEN}========================================${NC}"

# Check if key file exists
if [ ! -f "$KEY_PATH" ]; then
    echo -e "${RED}Error: SSH key not found at $KEY_PATH${NC}"
    exit 1
fi

# Set correct permissions for key
chmod 400 "$KEY_PATH"

echo -e "\n${BLUE}Deployment Strategy:${NC}"
echo -e "  • Deploy to /opt/smartbuild/ (main app)"
echo -e "  • Deploy to /opt/smartmonitor/utils/ (monitor)"
echo -e "  • Ensure both have identical utils code"

# Files to deploy to BOTH locations
FILES_TO_DEPLOY=(
    "utils/common_types.py"
    "utils/job_queue_manager_v2.py"
    "utils/prompt_preparers.py"
    "utils/claude_session_manager.py"
)

# Deploy to smartbuild
echo -e "\n${YELLOW}Deploying to /opt/smartbuild/...${NC}"
for file in "${FILES_TO_DEPLOY[@]}"; do
    echo -e "  Uploading $file..."
    scp -i "$KEY_PATH" "../$file" ubuntu@"$EC2_IP":/opt/smartbuild/$file
done

# Deploy middleware
echo -e "  Uploading smartbuild_spa_middleware.py..."
scp -i "$KEY_PATH" ../smartbuild_spa_middleware.py ubuntu@"$EC2_IP":/opt/smartbuild/

# Deploy documentation
echo -e "  Uploading documentation..."
scp -i "$KEY_PATH" ../.md/PROMPT_PREPARATION_DOCUMENTATION.md ubuntu@"$EC2_IP":/opt/smartbuild/.md/

# Deploy to smartmonitor
echo -e "\n${YELLOW}Deploying to /opt/smartmonitor/...${NC}"
for file in "${FILES_TO_DEPLOY[@]}"; do
    # Extract just the filename for monitor (no subdirectory)
    filename=$(basename "$file")
    echo -e "  Uploading $filename to monitor utils..."
    scp -i "$KEY_PATH" "../$file" ubuntu@"$EC2_IP":/opt/smartmonitor/utils/$filename
done

# Verify the deployment
echo -e "\n${YELLOW}Verifying deployment...${NC}"
ssh -i "$KEY_PATH" ubuntu@"$EC2_IP" << 'EOF'
    echo "Checking /opt/smartbuild/utils/:"
    ls -la /opt/smartbuild/utils/ | grep -E "common_types|job_queue_manager_v2|prompt_preparers" | head -3
    
    echo ""
    echo "Checking /opt/smartmonitor/utils/:"
    ls -la /opt/smartmonitor/utils/ | grep -E "common_types|job_queue_manager_v2|prompt_preparers" | head -3
    
    # Test imports in smartbuild
    echo ""
    echo "Testing imports in smartbuild:"
    cd /opt/smartbuild
    python3 -c "
from utils.common_types import JobType
from utils.job_queue_manager_v2 import JobQueueManagerV2
from utils.prompt_preparers import prepare_requirements_prompt
print('✓ SmartBuild imports successful')
" 2>/dev/null || echo "✗ SmartBuild import failed"
    
    # Test imports in smartmonitor
    echo ""
    echo "Testing imports in smartmonitor:"
    cd /opt/smartmonitor
    python3 -c "
import sys
sys.path.insert(0, '/opt/smartmonitor')
from utils.common_types import JobType
from utils.job_queue_manager_v2 import JobQueueManagerV2
print('✓ SmartMonitor imports successful')
" 2>/dev/null || echo "✗ SmartMonitor import failed"
EOF

# Restart services
echo -e "\n${YELLOW}Restarting services...${NC}"
ssh -i "$KEY_PATH" ubuntu@"$EC2_IP" << 'EOF'
    echo "Restarting SmartBuild..."
    sudo systemctl restart smartbuild
    sleep 3
    
    echo "Restarting SmartMonitor..."
    sudo systemctl restart smartmonitor
    sleep 3
    
    echo ""
    echo "Service status:"
    sudo systemctl status smartbuild --no-pager | head -5
    sudo systemctl status smartmonitor --no-pager | head -5
EOF

echo -e "\n${GREEN}========================================${NC}"
echo -e "${GREEN}Deployment Complete!${NC}"
echo -e "${GREEN}========================================${NC}"

echo -e "\n${BLUE}What was deployed:${NC}"
echo -e "  ✅ common_types.py - To BOTH locations"
echo -e "  ✅ job_queue_manager_v2.py - To BOTH locations"
echo -e "  ✅ prompt_preparers.py - To BOTH locations"
echo -e "  ✅ claude_session_manager.py - To BOTH locations"
echo -e "  ✅ smartbuild_spa_middleware.py - To main app"
echo -e "  ✅ Documentation - To main app"

echo -e "\n${YELLOW}Important Notes:${NC}"
echo -e "  • Monitor now has job_queue_manager_v2.py"
echo -e "  • Monitor now has common_types.py for job type mappings"
echo -e "  • Both sites use identical utils code"
echo -e "  • Only job queue manager interacts with Claude"

echo -e "\n${GREEN}URLs:${NC}"
echo -e "  Main App: https://d10z4f7h6vaz0k.cloudfront.net/"
echo -e "  Monitor:  https://d10z4f7h6vaz0k.cloudfront.net/monitor/"