#!/bin/bash

# ==============================================================================
# SmartDeploy Deployment Script
# ==============================================================================
# Purpose: Deploy SmartDeploy application to EC2 instance
# Last Updated: 2025-09-03
# ==============================================================================

set -e

# Configuration
EC2_IP="${1:-98.83.207.85}"
KEY_PATH="../../keys/smartbuild-20250824180036.pem"
SMARTDEPLOY_SOURCE="../../../../CLAUDE/claude-code-cf-deploy/smartdeploy"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}SmartDeploy Deployment Script${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""

# Check if key file exists
if [ ! -f "$KEY_PATH" ]; then
    echo -e "${RED}Error: SSH key not found at $KEY_PATH${NC}"
    exit 1
fi

# Set correct permissions for key
chmod 400 "$KEY_PATH"

echo -e "${BLUE}Target EC2 Instance:${NC} $EC2_IP"
echo -e "${BLUE}Application Path:${NC} /opt/smartdeploy/"
echo ""

# Function to deploy files
deploy_files() {
    echo -e "${YELLOW}Deploying SmartDeploy application files...${NC}"
    
    # Main application files
    echo "  → Deploying smartdeploy_complete.py..."
    scp -i "$KEY_PATH" "$SMARTDEPLOY_SOURCE/smartdeploy_complete.py" ubuntu@"$EC2_IP":/opt/smartdeploy/
    
    echo "  → Deploying version_config.py..."
    scp -i "$KEY_PATH" "$SMARTDEPLOY_SOURCE/version_config.py" ubuntu@"$EC2_IP":/opt/smartdeploy/
    
    # Deployment pipeline files (required for second tab)
    echo "  → Deploying deployment_pipeline.py..."
    scp -i "$KEY_PATH" "$SMARTDEPLOY_SOURCE/deployment_pipeline.py" ubuntu@"$EC2_IP":/opt/smartdeploy/ 2>/dev/null || echo "    (File not found, skipping)"
    
    echo "  → Deploying deployment_pipeline_ui.py..."
    scp -i "$KEY_PATH" "$SMARTDEPLOY_SOURCE/deployment_pipeline_ui.py" ubuntu@"$EC2_IP":/opt/smartdeploy/ 2>/dev/null || echo "    (File not found, skipping)"
    
    # Deploy utils folder if exists
    if [ -d "$SMARTDEPLOY_SOURCE/utils" ]; then
        echo "  → Deploying utils/ directory..."
        scp -r -i "$KEY_PATH" "$SMARTDEPLOY_SOURCE/utils/" ubuntu@"$EC2_IP":/opt/smartdeploy/
    fi
    
    echo -e "${GREEN}✓ Files deployed successfully${NC}"
}

# Function to restart service
restart_service() {
    echo -e "${YELLOW}Restarting SmartDeploy service...${NC}"
    
    ssh -i "$KEY_PATH" ubuntu@"$EC2_IP" << 'EOF'
        sudo systemctl restart smartdeploy
        sleep 3
        
        # Check if service is running
        if sudo systemctl is-active --quiet smartdeploy; then
            echo "✓ SmartDeploy service restarted successfully"
            sudo systemctl status smartdeploy --no-pager | head -5
        else
            echo "✗ SmartDeploy service failed to start"
            sudo journalctl -u smartdeploy -n 20 --no-pager
            exit 1
        fi
EOF
}

# Function to verify deployment
verify_deployment() {
    echo -e "${YELLOW}Verifying deployment...${NC}"
    
    # Test direct EC2 access
    echo -n "  → Testing port 80 (nginx)... "
    if curl -s -f http://$EC2_IP/_stcore/health > /dev/null; then
        echo -e "${GREEN}✓${NC}"
    else
        echo -e "${RED}✗${NC}"
    fi
    
    echo -n "  → Testing port 8510... "
    if curl -s -f http://$EC2_IP:8510/_stcore/health > /dev/null; then
        echo -e "${GREEN}✓${NC}"
    else
        echo -e "${RED}✗${NC}"
    fi
    
    # Check files on server
    echo -e "${BLUE}Deployed files:${NC}"
    ssh -i "$KEY_PATH" ubuntu@"$EC2_IP" << 'EOF'
        echo "Main files:"
        ls -la /opt/smartdeploy/*.py | tail -5
        
        if [ -d /opt/smartdeploy/utils ]; then
            echo ""
            echo "Utils files:"
            ls -la /opt/smartdeploy/utils/*.py 2>/dev/null | head -3 || echo "  (No utils files)"
        fi
EOF
}

# Function to invalidate CloudFront cache
clear_cache() {
    echo -e "${YELLOW}Creating CloudFront cache invalidation...${NC}"
    
    # SmartDeploy CloudFront distribution ID
    DISTRIBUTION_ID="E1GX8Q0MZAUAZ1"
    
    if command -v aws &> /dev/null; then
        INVALIDATION_ID=$(aws cloudfront create-invalidation \
            --distribution-id $DISTRIBUTION_ID \
            --paths "/*" \
            --query 'Invalidation.Id' \
            --output text 2>/dev/null)
        
        if [ $? -eq 0 ]; then
            echo -e "${GREEN}✓ Cache invalidation created: $INVALIDATION_ID${NC}"
        else
            echo -e "${YELLOW}⚠ Could not create cache invalidation (AWS CLI not configured)${NC}"
        fi
    else
        echo -e "${YELLOW}⚠ AWS CLI not found, skipping cache invalidation${NC}"
    fi
}

# Main execution
echo -e "${BLUE}Starting deployment...${NC}"
echo ""

deploy_files
echo ""

restart_service
echo ""

verify_deployment
echo ""

clear_cache
echo ""

# Final summary
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Deployment Complete!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo -e "${BLUE}Access URLs:${NC}"
echo -e "  Direct EC2: http://$EC2_IP/"
echo -e "  Alt Port:   http://$EC2_IP:8510/"
echo -e "  CloudFront: https://d114jw1hzulx0n.cloudfront.net/"
echo ""
echo -e "${YELLOW}Note:${NC} CloudFront changes take 5-15 minutes to propagate"