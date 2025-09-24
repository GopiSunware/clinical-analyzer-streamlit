#!/bin/bash

# Verify SmartBuild Deployment
# Checks that main app is running with all features

set -e

# Configuration
EC2_IP="${1:-98.83.207.85}"
# Allow override; default to repo path
KEY_PATH="${KEY_PATH:-./deploy/keys/smartbuild-20250824180036.pem}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Verifying SmartBuild Deployment${NC}"
echo -e "${GREEN}========================================${NC}"

chmod 400 "$KEY_PATH"

echo -e "\n${BLUE}1. Service Status:${NC}"
ssh -i "$KEY_PATH" ubuntu@"$EC2_IP" 'sudo systemctl is-active smartbuild' && echo -e "${GREEN}✓ Service is active${NC}" || echo -e "${RED}✗ Service is not active${NC}"

echo -e "\n${BLUE}2. Port Check:${NC}"
ssh -i "$KEY_PATH" ubuntu@"$EC2_IP" 'sudo netstat -tlnp | grep :8505' && echo -e "${GREEN}✓ Port 8505 is listening${NC}" || echo -e "${RED}✗ Port 8505 not found${NC}"

echo -e "\n${BLUE}3. HTTP Response Test:${NC}"
response=$(curl -s -o /dev/null -w "%{http_code}" http://$EC2_IP:8505/ 2>/dev/null || echo "failed")
if [ "$response" = "200" ]; then
    echo -e "${GREEN}✓ HTTP 200 OK${NC}"
else
    echo -e "${YELLOW}⚠ HTTP response: $response${NC}"
fi

echo -e "\n${BLUE}4. CloudFront Tests (3 apps):${NC}"
main_url="https://d10z4f7h6vaz0k.cloudfront.net/"
mon_url="https://d1b2mw2j81ms4x.cloudfront.net/"
ctrl_url="https://d23i1hoblpve1z.cloudfront.net/"
for url in "$main_url" "$mon_url" "$ctrl_url"; do
  code=$(curl -s -o /dev/null -w "%{http_code}" "$url" 2>/dev/null || echo "failed")
  echo -e "  $url -> ${code}"
done

echo -e "\n${BLUE}5. Build Info and Tab Implementation File:${NC}"
ssh -i "$KEY_PATH" ubuntu@"$EC2_IP" << 'EOF'
if [ -f /opt/smartbuild/BUILD_INFO.json ]; then
    echo "✓ BUILD_INFO.json present" && cat /opt/smartbuild/BUILD_INFO.json
else
    echo "✗ BUILD_INFO.json missing"
fi

if [ -f /opt/smartbuild/utils/tab_implementations.py ]; then
    echo "✓ tab_implementations.py exists"
    echo "  Checking for tabs:"
    grep -q "show_cost_analysis_tab" /opt/smartbuild/utils/tab_implementations.py && echo "  ✓ Cost Analysis tab found" || echo "  ✗ Cost Analysis tab missing"
    grep -q "show_technical_documentation_tab" /opt/smartbuild/utils/tab_implementations.py && echo "  ✓ Technical Documentation tab found" || echo "  ✗ Technical Documentation tab missing"
    grep -q "show_terraform_tab" /opt/smartbuild/utils/tab_implementations.py && echo "  ✓ Terraform tab found" || echo "  ✗ Terraform tab missing"
    grep -q "show_cloudformation_tab" /opt/smartbuild/utils/tab_implementations.py && echo "  ✓ CloudFormation tab found" || echo "  ✗ CloudFormation tab missing"
else
    echo "✗ tab_implementations.py not found!"
fi
EOF

echo -e "\n${BLUE}6. Recent Logs Check:${NC}"
ssh -i "$KEY_PATH" ubuntu@"$EC2_IP" 'sudo journalctl -u smartbuild --since "5 minutes ago" | grep -i error | head -5' || echo "No recent errors"

echo -e "\n${GREEN}========================================${NC}"
echo -e "${YELLOW}Next Steps:${NC}"
echo "1. Visit https://d10z4f7h6vaz0k.cloudfront.net/"
echo "2. Create or select a session"
echo "3. Generate a solution"
echo "4. Verify all 5 tabs appear:"
echo "   - Requirements"
echo "   - Cost Analysis"
echo "   - Technical Documentation"
echo "   - Terraform"
echo "   - CloudFormation"
echo ""
echo -e "${YELLOW}If tabs are still missing:${NC}"
echo "- Clear browser cache (Ctrl+Shift+R)"
echo "- Invalidate CloudFront cache:"
echo "  aws cloudfront create-invalidation --distribution-id EY2D88MPRKCMZ --paths '/*'"
echo ""
echo -e "${YELLOW}Monitor deployment:${NC}"
echo "Ready to proceed with: ./setup-smartmonitor-separate.sh 98.83.207.85"
