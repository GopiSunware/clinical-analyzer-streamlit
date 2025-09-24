# Master Deployment Guide - SmartBuild Complete Suite
**Last Updated**: December 2024
**Version**: 5.15.1
**Status**: PRODUCTION READY

## 🎯 Overview

This guide covers the complete deployment of all 4 SmartBuild applications to EC2 with comprehensive details.

## 📊 Application Suite

| Application | Port | Local URL | EC2 URL | CloudFront URL | Purpose |
|------------|------|-----------|---------|----------------|---------|
| **SmartBuild Main** | 8505 | http://localhost:8505 | http://98.83.207.85:8505 | https://d10z4f7h6vaz0k.cloudfront.net | Main application |
| **Job Monitor** | 8504 | http://localhost:8504 | http://98.83.207.85:8504 | https://d1b2mw2j81ms4x.cloudfront.net | Job queue viewer |
| **Control Center** | 8507 | http://localhost:8507 | http://98.83.207.85:8507 | https://d23i1hoblpve1z.cloudfront.net | Monitor control & logs |
| **UI Automation** | 8512 | http://localhost:8512 | http://98.83.207.85:8512 | https://d2hvw4a6x4umux.cloudfront.net | Test runner UI with iframe |
| **SmartDeploy** | 8511 (nginx alt 8510/80) | http://localhost:8511 | http://98.83.207.85 | https://d114jw1hzulx0n.cloudfront.net | Deployment pipeline & infra automation |

## 🖥️ EC2 Instance Details

| Property | Value |
|----------|-------|
| **Instance ID** | (Check AWS Console) |
| **Instance Type** | t3.large |
| **Public IP** | 98.83.207.85 |
| **Region** | us-east-1 (N. Virginia) |
| **OS** | Ubuntu 22.04.5 LTS |
| **SSH User** | ubuntu |
| **Key File** | `deploy/smartbuild-20250824180036.pem` |
| **Security Group** | Ports: 22, 80, 8504-8507, 8512 |

## 🔑 SSH Connection

```bash
# Set key permissions (first time only)
chmod 400 deploy/smartbuild-20250824180036.pem

# Connect to EC2
ssh -i deploy/smartbuild-20250824180036.pem ubuntu@98.83.207.85
```

## 📁 File Structure Mapping

### Local Directory Structure
```
/mnt/c/Shri Hari Hari/Ubuntu/sunware-tech/devgenious/claude-code-chat/
├── smartbuild_spa_middleware_dynamic.py    # Main app
├── smartbuild_monitor.py                   # Job Monitor
├── job_queue_control.py                    # Control Center
├── job_queue_monitor.py                    # Background monitor
├── ui-automation/
│   └── ui_automation_runner_app.py        # OLD UI Automation
├── ui-automation-proxy/
│   └── proxy_automation_complete.py       # NEW UI Automation (with iframe)
├── utils/                                  # Shared utilities
├── config/                                 # Configuration files
├── sessions/                               # Session data
├── .claude/agents/                         # Agent configurations
└── deploy/                                 # Deployment scripts
```

### EC2 Directory Structure
```
/opt/
├── smartbuild/                             # Main application
│   ├── smartbuild_spa_middleware_dynamic.py
│   ├── job_queue_monitor.py
│   ├── utils/
│   ├── config/
│   ├── sessions/
│   └── .claude/agents/
├── smartmonitor/                           # Job Monitor
│   └── smartbuild_monitor.py
├── job_queue_control/                      # Control Center
│   └── job_queue_control.py
└── ui-automation/                          # UI Automation
    ├── ui_automation_runner_app.py
    ├── proxy_automation_complete.py       # NEW
    └── ui-automation-proxy/
```

## 🚀 Deployment Process

### Step 1: Prepare Local Environment

```bash
# Navigate to project root
cd /mnt/c/Shri\ Hari\ Hari/Ubuntu/sunware-tech/devgenious/claude-code-chat

# Ensure latest code is committed
git status
git add -A
git commit -m "Pre-deployment commit"
git push origin smartbuild_monitor_automation
```

### Step 2: Deploy Main Application (Port 8505)

```bash
# Deploy main app and core files
rsync -avz --delete \
  -e "ssh -i deploy/smartbuild-20250824180036.pem" \
  --exclude='sessions/' \
  --exclude='__pycache__/' \
  --exclude='*.pyc' \
  --exclude='.git/' \
  --exclude='logs/' \
  --exclude='tests/' \
  --include='smartbuild_spa_middleware_dynamic.py' \
  --include='job_queue_monitor.py' \
  --include='utils/' \
  --include='config/' \
  --include='.claude/' \
  --include='requirements.txt' \
  --include='version_config.py' \
  ./ ubuntu@98.83.207.85:/opt/smartbuild/

# Create necessary directories
ssh -i deploy/smartbuild-20250824180036.pem ubuntu@98.83.207.85 << 'EOF'
  sudo mkdir -p /opt/smartbuild/sessions/active
  sudo mkdir -p /opt/smartbuild/sessions/deleted
  sudo chown -R ubuntu:ubuntu /opt/smartbuild
EOF
```

### Step 3: Deploy Job Monitor (Port 8504)

```bash
# Deploy Job Monitor
rsync -avz \
  -e "ssh -i deploy/smartbuild-20250824180036.pem" \
  smartbuild_monitor.py \
  ubuntu@98.83.207.85:/opt/smartmonitor/

# Copy utils if needed
rsync -avz \
  -e "ssh -i deploy/smartbuild-20250824180036.pem" \
  utils/ \
  ubuntu@98.83.207.85:/opt/smartmonitor/utils/
```

### Step 4: Deploy Control Center (Port 8507)

```bash
# Deploy Control Center
rsync -avz \
  -e "ssh -i deploy/smartbuild-20250824180036.pem" \
  job_queue_control.py \
  ubuntu@98.83.207.85:/opt/job_queue_control/

# Copy utils
rsync -avz \
  -e "ssh -i deploy/smartbuild-20250824180036.pem" \
  utils/ \
  ubuntu@98.83.207.85:/opt/job_queue_control/utils/
```

### Step 5: Deploy UI Automation (Port 8512) - NEW VERSION

```bash
# Deploy UI Automation with new proxy version
rsync -avz \
  -e "ssh -i deploy/smartbuild-20250824180036.pem" \
  --exclude='__pycache__/' \
  --exclude='*.pyc' \
  --exclude='logs/' \
  ui-automation/ \
  ubuntu@98.83.207.85:/opt/ui-automation/

# Deploy the new proxy automation files
rsync -avz \
  -e "ssh -i deploy/smartbuild-20250824180036.pem" \
  --exclude='__pycache__/' \
  --exclude='*.pyc' \
  --exclude='logs/' \
  ui-automation-proxy/ \
  ubuntu@98.83.207.85:/opt/ui-automation/ui-automation-proxy/

# Copy the main proxy file to ui-automation root for easier access
ssh -i deploy/smartbuild-20250824180036.pem ubuntu@98.83.207.85 << 'EOF'
  cp /opt/ui-automation/ui-automation-proxy/proxy_automation_complete.py /opt/ui-automation/
  chmod +x /opt/ui-automation/proxy_automation_complete.py
EOF
```

### Step 6: Install Dependencies on EC2

```bash
ssh -i deploy/smartbuild-20250824180036.pem ubuntu@98.83.207.85 << 'EOF'
  # Update system
  sudo apt-get update

  # Install Python dependencies for all apps
  cd /opt/smartbuild
  pip install streamlit pandas plotly streamlit-autorefresh playwright

  # Install Playwright browsers for UI automation
  cd /opt/ui-automation
  python -m playwright install chromium
  python -m playwright install-deps

  # Ensure all apps have required packages
  pip install websockets aiohttp
EOF
```

### Step 7: Create/Update Systemd Services

```bash
# Create service files
ssh -i deploy/smartbuild-20250824180036.pem ubuntu@98.83.207.85 << 'EOF'

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

# 5. UI Automation Service (NEW - Using proxy_automation_complete.py)
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

EOF
```

### Step 8: Start All Services

```bash
ssh -i deploy/smartbuild-20250824180036.pem ubuntu@98.83.207.85 << 'EOF'
  # Stop any existing services
  sudo systemctl stop smartbuild smartmonitor job-queue-control ui-automation
  sudo systemctl stop job-queue-monitor

  # Start in correct order
  sudo systemctl start job-queue-monitor    # Must start first (acquires lock)
  sleep 2
  sudo systemctl start smartbuild           # Main app
  sleep 2
  sudo systemctl start smartmonitor         # Job Monitor UI
  sudo systemctl start job-queue-control    # Control Center
  sudo systemctl start ui-automation        # UI Automation

  # Check status
  echo "=== Service Status ==="
  sudo systemctl status smartbuild --no-pager | head -10
  sudo systemctl status job-queue-monitor --no-pager | head -10
  sudo systemctl status smartmonitor --no-pager | head -10
  sudo systemctl status job-queue-control --no-pager | head -10
  sudo systemctl status ui-automation --no-pager | head -10
EOF
```

## ✅ Verification

### Check All Services

```bash
# Quick status check
ssh -i deploy/smartbuild-20250824180036.pem ubuntu@98.83.207.85 << 'EOF'
  echo "=== Active Services ==="
  systemctl is-active smartbuild job-queue-monitor smartmonitor job-queue-control ui-automation

  echo -e "\n=== Port Status ==="
  sudo ss -tlnp | grep -E "8504|8505|8507|8512"

  echo -e "\n=== Process Check ==="
  ps aux | grep -E "streamlit|job_queue" | grep -v grep
EOF
```

### Test URLs

```bash
# Test each application
curl -I http://98.83.207.85:8505  # Main App
curl -I http://98.83.207.85:8504  # Job Monitor
curl -I http://98.83.207.85:8507  # Control Center
curl -I http://98.83.207.85:8512  # UI Automation

# Or test CloudFront URLs
curl -I https://d10z4f7h6vaz0k.cloudfront.net   # Main App
curl -I https://d1b2mw2j81ms4x.cloudfront.net   # Job Monitor
curl -I https://d23i1hoblpve1z.cloudfront.net   # Control Center
curl -I https://d2hvw4a6x4umux.cloudfront.net   # UI Automation
```

## 🔧 Troubleshooting

### View Logs

```bash
# View service logs
ssh -i deploy/smartbuild-20250824180036.pem ubuntu@98.83.207.85 << 'EOF'
  # Main app logs
  sudo journalctl -u smartbuild -n 50 --no-pager

  # Job queue monitor logs
  sudo journalctl -u job-queue-monitor -n 50 --no-pager

  # Other service logs
  sudo journalctl -u smartmonitor -n 20 --no-pager
  sudo journalctl -u job-queue-control -n 20 --no-pager
  sudo journalctl -u ui-automation -n 20 --no-pager
EOF
```

### Restart Services

```bash
ssh -i deploy/smartbuild-20250824180036.pem ubuntu@98.83.207.85 << 'EOF'
  # Restart all services
  sudo systemctl restart job-queue-monitor
  sleep 2
  sudo systemctl restart smartbuild smartmonitor job-queue-control ui-automation
EOF
```

### Kill Stuck Processes

```bash
ssh -i deploy/smartbuild-20250824180036.pem ubuntu@98.83.207.85 << 'EOF'
  # Kill processes on specific ports
  sudo fuser -k 8505/tcp 8504/tcp 8507/tcp 8512/tcp

  # Kill all tmux sessions
  tmux kill-server

  # Remove lock file if stuck
  rm -f /opt/smartbuild/sessions/.job_queue_monitor.lock
EOF
```

## 📋 Quick Reference Commands

### One-Line Deployment (After initial setup)

```bash
# Deploy all apps at once
./deploy/scripts/deploy-all.sh
```

### Create deployment script

```bash
cat > deploy/scripts/deploy-all.sh << 'SCRIPT'
#!/bin/bash
# Complete deployment script for all SmartBuild applications

KEY_PATH="deploy/smartbuild-20250824180036.pem"
EC2_IP="98.83.207.85"

echo "🚀 Deploying SmartBuild Suite to EC2..."

# Deploy Main App
echo "📦 Deploying Main Application..."
rsync -avz --delete \
  -e "ssh -i $KEY_PATH" \
  --exclude='sessions/' \
  --exclude='__pycache__/' \
  --exclude='.git/' \
  --exclude='logs/' \
  smartbuild_spa_middleware_dynamic.py job_queue_monitor.py utils/ config/ .claude/ \
  ubuntu@$EC2_IP:/opt/smartbuild/

# Deploy Job Monitor
echo "📦 Deploying Job Monitor..."
rsync -avz -e "ssh -i $KEY_PATH" \
  smartbuild_monitor.py \
  ubuntu@$EC2_IP:/opt/smartmonitor/

# Deploy Control Center
echo "📦 Deploying Control Center..."
rsync -avz -e "ssh -i $KEY_PATH" \
  job_queue_control.py \
  ubuntu@$EC2_IP:/opt/job_queue_control/

# Deploy UI Automation
echo "📦 Deploying UI Automation..."
rsync -avz -e "ssh -i $KEY_PATH" \
  ui-automation/ ui-automation-proxy/ \
  ubuntu@$EC2_IP:/opt/ui-automation/

# Restart services
echo "🔄 Restarting services..."
ssh -i $KEY_PATH ubuntu@$EC2_IP << 'EOF'
  sudo systemctl restart job-queue-monitor
  sleep 2
  sudo systemctl restart smartbuild smartmonitor job-queue-control ui-automation
  echo "✅ All services restarted"
EOF

echo "✅ Deployment complete!"
SCRIPT

chmod +x deploy/scripts/deploy-all.sh
```

## 📊 Application Features

### 1. SmartBuild Main (Port 8505)
- **Purpose**: Main SmartBuild Solution Designer application
- **Features**:
  - Session management
  - Requirements extraction
  - Architecture diagram generation
  - 10 artifact generation tabs
  - TMUX and SubAgent execution modes

### 2. Job Monitor (Port 8504)
- **Purpose**: Real-time job queue monitoring
- **Features**:
  - View all queued, running, completed jobs
  - Session and run details
  - Job status tracking
  - No TMUX tab (simplified view)

### 3. Control Center (Port 8507)
- **Purpose**: System control and monitoring
- **Features**:
  - Service management
  - TMUX session viewer
  - Console log viewer
  - System health checks

### 4. UI Automation (Port 8512) - NEW VERSION
- **Purpose**: Automated UI testing with iframe support
- **Features**:
  - **NEW**: Iframe-based testing (proxy_automation_complete.py)
  - Session selection and management
  - Automated test execution
  - Progress tracking with sidebar display
  - Support for CloudFront URL testing
  - Real-time log viewing
  - Video recording of test runs

## 🔐 Security Notes

1. **SSH Key**: Keep `deploy/smartbuild-20250824180036.pem` secure
2. **Ports**: Only required ports are open in security group
3. **CloudFront**: Provides HTTPS access to all services
4. **Updates**: Regularly update system packages

## 📝 Maintenance

### Daily Tasks
- Check service status
- Monitor disk space
- Review error logs

### Weekly Tasks
- Clean old sessions: `find /opt/smartbuild/sessions/deleted -mtime +7 -delete`
- Compress logs: `find /opt/*/logs -name "*.log" -mtime +3 -exec gzip {} \;`
- Update code from git repository

### Monthly Tasks
- System updates: `sudo apt update && sudo apt upgrade`
- Review CloudFront usage and costs
- Backup important data

## 🆘 Support

### Quick Health Check
```bash
./deploy/scripts/verify-deployment.sh
```

### Emergency Restart
```bash
ssh -i deploy/smartbuild-20250824180036.pem ubuntu@98.83.207.85 << 'EOF'
  sudo systemctl restart job-queue-monitor
  sleep 2
  sudo systemctl restart smartbuild smartmonitor job-queue-control ui-automation
EOF
```

### Contact
- EC2 Console: https://console.aws.amazon.com/ec2
- CloudFront Console: https://console.aws.amazon.com/cloudfront

---

**Last Deployment**: December 2024
**Deployed By**: SmartBuild Team
**Documentation Version**: 1.0
