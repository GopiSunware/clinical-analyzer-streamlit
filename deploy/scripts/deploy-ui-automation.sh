#!/bin/bash

# Deploy UI Automation to EC2
set -e

EC2_IP="98.83.207.85"
KEY_PATH="deploy/keys/smartbuild-20250824180036.pem"
EC2_USER="ubuntu"

echo "🚀 Deploying UI Automation to EC2..."

# Create deployment script
cat > /tmp/deploy_ui_automation.sh << 'DEPLOY_SCRIPT'
#!/bin/bash
set -e

echo "Starting UI Automation deployment on EC2..."

# Create directory
sudo mkdir -p /opt/ui-automation
cd /opt/ui-automation

# Create the Streamlit app
sudo tee ui_automation_runner_app.py > /dev/null << 'APP_EOF'
import streamlit as st
import subprocess
import os
import json
from pathlib import Path
import time
from datetime import datetime

st.set_page_config(
    page_title="SmartBuild UI Test Runner",
    page_icon="🧪",
    layout="wide"
)

st.title("🧪 SmartBuild UI Automation Test Runner")
st.markdown("---")

with st.sidebar:
    st.header("Test Configuration")

    sessions_dir = Path("/opt/smartbuild/sessions/active")
    if sessions_dir.exists():
        sessions = [d.name for d in sessions_dir.iterdir() if d.is_dir()]
        selected_session = st.selectbox("Select Session", ["Create New"] + sessions)
    else:
        selected_session = "Create New"
        st.warning("Sessions directory not found")

    test_prompt = st.text_area(
        "Requirements Prompt",
        value="Build a REST API with user authentication",
        height=100
    )

    test_phases = st.selectbox("Test Phases", ["both", "analyze", "arch"])
    headless_mode = st.checkbox("Headless Mode", value=True)

col1, col2 = st.columns([2, 1])

with col1:
    st.header("Test Execution")

    if st.button("▶️ Run Test", type="primary"):
        with st.spinner("Running test..."):
            st.success("✅ Test interface ready!")
            st.info("Test execution will be implemented after Playwright setup")

    if st.button("📊 View Status"):
        if selected_session != "Create New":
            st.json({"session": selected_session, "status": "ready"})

with col2:
    st.header("Test Artifacts")
    st.info("Screenshots and logs will appear here")

st.markdown("---")
st.caption("SmartBuild UI Automation v1.0 | Port 8511 | Ready for CloudFront")
APP_EOF

# Install dependencies
echo "Installing dependencies..."
sudo apt-get update -qq
sudo apt-get install -y python3-pip python3-venv nginx

# Create virtual environment if not exists
if [ ! -d "venv" ]; then
    sudo python3 -m venv venv
fi

sudo ./venv/bin/pip install --upgrade pip
sudo ./venv/bin/pip install streamlit

# Create systemd service
echo "Creating service..."
sudo tee /etc/systemd/system/ui-automation.service > /dev/null << 'SERVICE_EOF'
[Unit]
Description=SmartBuild UI Automation Test Runner
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/opt/ui-automation
Environment="PATH=/opt/ui-automation/venv/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
ExecStart=/opt/ui-automation/venv/bin/streamlit run ui_automation_runner_app.py --server.port 8511 --server.address 0.0.0.0 --server.headless true
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
SERVICE_EOF

# Configure nginx
echo "Configuring nginx..."
sudo tee /etc/nginx/sites-available/ui-automation > /dev/null << 'NGINX_EOF'
server {
    listen 8511;
    server_name _;

    location / {
        proxy_pass http://127.0.0.1:8511;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_buffering off;
    }

    location /_stcore/stream {
        proxy_pass http://127.0.0.1:8511/_stcore/stream;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_buffering off;
    }
}
NGINX_EOF

sudo ln -sf /etc/nginx/sites-available/ui-automation /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl restart nginx

# Set permissions
sudo chown -R ubuntu:ubuntu /opt/ui-automation

# Start service
echo "Starting service..."
sudo systemctl daemon-reload
sudo systemctl enable ui-automation
sudo systemctl restart ui-automation

# Open firewall port
sudo ufw allow 8511/tcp 2>/dev/null || true

# Wait and check
sleep 10
sudo systemctl status ui-automation --no-pager | head -20
sudo netstat -tlnp | grep 8511 || echo "Waiting for port..."

echo "✅ Deployment complete!"
echo "Access at: http://98.83.207.85:8511"
DEPLOY_SCRIPT

# Execute deployment on EC2
echo "📡 Connecting to EC2 and deploying..."
ssh -o StrictHostKeyChecking=no -i "$KEY_PATH" ${EC2_USER}@${EC2_IP} 'bash -s' < /tmp/deploy_ui_automation.sh

# Test the deployment
echo ""
echo "🔍 Testing deployment..."
sleep 5
if curl -s -o /dev/null -w "%{http_code}" http://${EC2_IP}:8511 | grep -q "200\|302"; then
    echo "✅ UI Automation is running at http://${EC2_IP}:8511"
else
    echo "⚠️  Service starting, please wait..."
fi

echo ""
echo "📋 Next: Create CloudFront distribution"