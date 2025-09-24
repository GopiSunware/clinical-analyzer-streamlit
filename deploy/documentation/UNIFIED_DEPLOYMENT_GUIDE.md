# 🚀 Unified Deployment Guide - SmartBuild & SmartDeploy

*Last Updated: 2025-09-03 | Version 5.11.10*

## 📋 Table of Contents
1. [Overview](#overview)
2. [Current Production Status](#current-production-status)
3. [Prerequisites](#prerequisites)
4. [Architecture](#architecture)
5. [Local Development](#local-development)
6. [Deployment Methods](#deployment-methods)
7. [Post-Deployment Verification](#post-deployment-verification)
8. [Troubleshooting](#troubleshooting)
9. [Maintenance](#maintenance)
10. [Recent Changes](#recent-changes)

---

## 🎯 Overview

This EC2 instance hosts multiple Streamlit applications:

### Applications Deployed

1. **SmartBuild SPA** - AI-powered AWS architecture generator with 5 tabs
2. **SmartBuild Monitor** - Real-time job monitoring dashboard  
3. **SmartDeploy Solution Designer** - New AWS solution deployment tool (v5.10.14)
4. **Console Control Center** - System monitoring and control

### EC2 Instance Details
- **IP**: 98.83.207.85
- **Type**: t3.large (8GB RAM)
- **Region**: us-east-1
- **Key File**: smartbuild-20250824180036.pem
- **OS**: Ubuntu 22.04.5 LTS

---

## 📊 Current Production Status

| Application | CloudFront URL | EC2 Port | Service Port | Status | Version |
|-------------|---------------|----------|--------------|---------|---------|
| **SmartBuild SPA** | https://d10z4f7h6vaz0k.cloudfront.net | 8080 | 8505 | ✅ Running | 5.11.10 |
| **SmartBuild Monitor** | https://d1b2mw2j81ms4x.cloudfront.net | 8504 | 8504 | ✅ Running | - |
| **SmartDeploy** | https://d114jw1hzulx0n.cloudfront.net | 80 | 8511 | ✅ Running | 5.10.14 |
| **Control Center** | https://d23i1hoblpve1z.cloudfront.net | 8507 | 8507 | ✅ Running | - |

### Direct EC2 Access URLs
- SmartDeploy: http://98.83.207.85/ (port 80)
- SmartDeploy Alt: http://98.83.207.85:8510/
- SmartBuild: http://98.83.207.85:8080/
- SmartBuild Monitor: http://98.83.207.85:8504/
- Control Center: http://98.83.207.85:8507/

---

## 📋 Prerequisites

### Local Requirements
- AWS CLI configured (`aws configure`)
- SSH key file with proper permissions (`chmod 400 *.pem`)
- Python 3.11+ for local testing
- Git for version control

### AWS Permissions Required
- EC2 (instances, security groups)
- CloudFront distributions
- S3 buckets (for session storage)
- IAM roles and policies

### Project Structure
```
# SmartBuild/SmartMonitor
/opt/
├── smartbuild/                      # Main SmartBuild application
│   ├── smartbuild_spa_middleware.py # v5.11.10 
│   ├── utils/                       # Shared utilities
│   │   ├── common_types.py         # Job type definitions
│   │   ├── job_queue_manager_v2.py # Claude interaction
│   │   └── prompt_preparers.py     # Prompt preparation
│   ├── sessions/                    # Session data storage
│   └── venv/                        # Python virtual environment
│
├── smartmonitor/                    # Monitor application
│   ├── smartbuild_monitor.py       # Monitor UI
│   └── utils/                       # Copy of utils from smartbuild
│
├── smartdeploy/                     # SmartDeploy application
│   ├── smartdeploy_complete.py     # Main application
│   ├── version_config.py           # Version configuration
│   └── utils/                       # SmartDeploy utilities
│
├── console_monitor/                 # Console log viewer
└── job_queue_control/              # Control center
```

---

## 🏗️ Architecture

### Network Architecture (Updated 2025-09-03)
```
CloudFront (HTTPS) → EC2 → Nginx → Localhost Services

Current Configuration:
├── d114jw1hzulx0n.cloudfront.net → EC2:80    → nginx → localhost:8511 (SmartDeploy)
├── d10z4f7h6vaz0k.cloudfront.net → EC2:8080  → nginx → localhost:8505 (SmartBuild)
├── d1b2mw2j81ms4x.cloudfront.net → EC2:8504  → direct → localhost:8504 (Monitor)
└── d23i1hoblpve1z.cloudfront.net → EC2:8507  → direct → localhost:8507 (Control)
```

### Nginx Configuration
```nginx
# Port 80 - SmartDeploy (default)
server {
    listen 80 default_server;
    location / {
        proxy_pass http://127.0.0.1:8511;
    }
}

# Port 8080 - SmartBuild
server {
    listen 8080;
    location / {
        proxy_pass http://127.0.0.1:8505;
    }
}

# Port 8510 - SmartDeploy (alternative)
server {
    listen 8510;
    location / {
        proxy_pass http://127.0.0.1:8511;
    }
}
```

---

## 💻 Local Development

### Running Applications Locally

All applications can be run locally using Streamlit for development and testing before deployment:

#### 1. SmartBuild SPA
```bash
# From claude-code-chat directory
cd /path/to/claude-code-chat
streamlit run smartbuild_spa_middleware.py --server.port 8505

# Access at: http://localhost:8505
```

#### 2. SmartBuild Monitor  
```bash
# From claude-code-chat directory
cd /path/to/claude-code-chat
streamlit run smartbuild_monitor.py --server.port 8504

# Access at: http://localhost:8504
```

#### 3. SmartDeploy Solution Designer
```bash
# From smartdeploy directory
cd /path/to/CLAUDE/claude-code-cf-deploy/smartdeploy
streamlit run smartdeploy_complete.py --server.port 8510

# Access at: http://localhost:8510
```

#### 4. Console Control Center
```bash
# From claude-code-chat directory
cd /path/to/claude-code-chat
streamlit run job_queue_control.py --server.port 8507

# Access at: http://localhost:8507
```

### Development Environment Setup

1. **Install Dependencies**
```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install required packages
pip install streamlit boto3 anthropic pandas plotly
```

2. **Configure Environment Variables**
```bash
# Create .env file (not tracked in git)
export ANTHROPIC_API_KEY="your-api-key"
export AWS_ACCESS_KEY_ID="your-access-key"
export AWS_SECRET_ACCESS_KEY="your-secret-key"
export AWS_DEFAULT_REGION="us-east-1"
```

3. **Running Multiple Apps Simultaneously**
```bash
# Use different terminal sessions or tmux
# Terminal 1:
streamlit run smartbuild_spa_middleware.py --server.port 8505

# Terminal 2:
streamlit run smartdeploy_complete.py --server.port 8510

# Terminal 3:
streamlit run smartbuild_monitor.py --server.port 8504
```

### Local Development Tips

- **Port Conflicts**: Ensure each app uses a unique port
- **Session Data**: Local sessions stored in `sessions/` directory
- **Hot Reload**: Streamlit auto-reloads on file changes
- **Debug Mode**: Set `STREAMLIT_DEBUG=1` for verbose logging
- **Network Access**: Use `--server.address 0.0.0.0` to allow network access

---

## 📦 Deployment Methods

### Method 1: Deploy SmartBuild/SmartMonitor Updates
```bash
# From deploy/ directory
cd deploy
chmod +x deploy-to-both-sites.sh
./deploy-to-both-sites.sh

# This deploys shared utils to BOTH:
# - /opt/smartbuild/
# - /opt/smartmonitor/
```

### Method 2: Deploy SmartDeploy
```bash
# Deploy SmartDeploy application
KEY_PATH="./smartbuild-20250824180036.pem"
EC2_IP="98.83.207.85"

# Copy main application
scp -i $KEY_PATH smartdeploy_complete.py ubuntu@$EC2_IP:/opt/smartdeploy/
scp -i $KEY_PATH version_config.py ubuntu@$EC2_IP:/opt/smartdeploy/

# Copy utilities
scp -r -i $KEY_PATH utils/ ubuntu@$EC2_IP:/opt/smartdeploy/

# Restart service
ssh -i $KEY_PATH ubuntu@$EC2_IP 'sudo systemctl restart smartdeploy'
```

### Method 3: Quick Updates
```bash
# Update SmartBuild only
./quick-update-main.sh 98.83.207.85

# Update SmartMonitor only  
./quick-update-monitor.sh 98.83.207.85

# Update SmartDeploy only (use dedicated script)
cd scripts/smartdeploy/
./deploy-smartdeploy.sh 98.83.207.85
```

### Method 4: Full System Update Script
```bash
#!/bin/bash
# deploy-all-apps.sh

EC2_IP="98.83.207.85"
KEY_PATH="./smartbuild-20250824180036.pem"

echo "Deploying all applications..."

# Deploy SmartBuild & Monitor
./deploy-to-both-sites.sh

# Deploy SmartDeploy
scp -i $KEY_PATH ../smartdeploy/smartdeploy_complete.py ubuntu@$EC2_IP:/opt/smartdeploy/
scp -i $KEY_PATH ../smartdeploy/version_config.py ubuntu@$EC2_IP:/opt/smartdeploy/

# Restart all services
ssh -i $KEY_PATH ubuntu@$EC2_IP << 'EOF'
    sudo systemctl restart smartbuild
    sudo systemctl restart smartmonitor
    sudo systemctl restart smartdeploy
    sudo systemctl restart console-monitor
    sudo systemctl restart job-queue-control
    
    echo "All services restarted"
    sudo systemctl status smartbuild smartmonitor smartdeploy --no-pager | grep Active
EOF
```

---

## 🔍 Post-Deployment Verification

### 1. Check All Services Status
```bash
ssh -i smartbuild-*.pem ubuntu@98.83.207.85 << 'EOF'
    echo "=== Service Status ==="
    echo "SmartBuild:" && sudo systemctl is-active smartbuild
    echo "SmartMonitor:" && sudo systemctl is-active smartmonitor
    echo "SmartDeploy:" && sudo systemctl is-active smartdeploy
    echo "Console Monitor:" && sudo systemctl is-active console-monitor
    echo "Control Center:" && sudo systemctl is-active job-queue-control
EOF
```

### 2. Test All Endpoints
```bash
# Test direct EC2 access
curl -s http://98.83.207.85/_stcore/health          # SmartDeploy (port 80)
curl -s http://98.83.207.85:8080/_stcore/health     # SmartBuild  
curl -s http://98.83.207.85:8504/_stcore/health     # Monitor
curl -s http://98.83.207.85:8507/_stcore/health     # Control Center

# Test CloudFront (wait for propagation)
curl -s https://d114jw1hzulx0n.cloudfront.net/_stcore/health  # SmartDeploy
curl -s https://d10z4f7h6vaz0k.cloudfront.net/_stcore/health  # SmartBuild
curl -s https://d1b2mw2j81ms4x.cloudfront.net/_stcore/health  # Monitor
```

### 3. Application Feature Checklist

**SmartDeploy** (https://d114jw1hzulx0n.cloudfront.net):
- [ ] Application loads
- [ ] Can create pipeline
- [ ] Version shows 5.10.14

**SmartBuild** (https://d10z4f7h6vaz0k.cloudfront.net):
- [ ] Create new session
- [ ] All 5 tabs visible
- [ ] Generate Architecture works
- [ ] Version shows 5.11.10

**SmartBuild Monitor** (https://d1b2mw2j81ms4x.cloudfront.net):
- [ ] Dashboard loads
- [ ] Shows active sessions
- [ ] Job queue updates

---

## 🔧 Troubleshooting

### Common Issues and Solutions

#### CloudFront Shows Wrong Application
```bash
# Check CloudFront origin configuration
aws cloudfront get-distribution-config --id DISTRIBUTION_ID \
  --query 'DistributionConfig.Origins.Items[0].{Domain:DomainName,Port:CustomOriginConfig.HTTPPort}'

# Invalidate cache
aws cloudfront create-invalidation --distribution-id DISTRIBUTION_ID --paths "/*"
```

#### Port Conflicts
```bash
# Check what's running on each port
ssh -i smartbuild-*.pem ubuntu@98.83.207.85 \
  'ss -tlpn | grep -E "8505|8504|8511|8507|8080|80"'

# Check nginx configuration
ssh -i smartbuild-*.pem ubuntu@98.83.207.85 \
  'cat /etc/nginx/sites-enabled/default'
```

#### Service Won't Start
```bash
# Check logs
ssh -i smartbuild-*.pem ubuntu@98.83.207.85 \
  'sudo journalctl -u SERVICE_NAME -n 100 --no-pager'

# Check for port already in use
ssh -i smartbuild-*.pem ubuntu@98.83.207.85 \
  'sudo lsof -i :PORT_NUMBER'
```

#### Import Errors
```bash
# SmartBuild/Monitor: Files must be in BOTH locations
./deploy-to-both-sites.sh

# SmartDeploy: Check utils folder
scp -r -i smartbuild-*.pem utils/ ubuntu@98.83.207.85:/opt/smartdeploy/
```

---

## 🛠️ Maintenance

### Daily Tasks
1. Check service status (all 5 apps)
2. Monitor disk space
3. Review error logs

### Weekly Tasks
```bash
# Clean old sessions
ssh -i smartbuild-*.pem ubuntu@98.83.207.85 << 'EOF'
    find /opt/smartbuild/sessions/deleted -type d -mtime +7 -exec rm -rf {} \;
    find /opt/smartdeploy/sessions/deleted -type d -mtime +7 -exec rm -rf {} \; 2>/dev/null
EOF

# Kill orphaned tmux sessions
ssh -i smartbuild-*.pem ubuntu@98.83.207.85 << 'EOF'
    tmux ls | grep -E '^(smartbuild|smartdeploy)_' | cut -d: -f1 | xargs -I {} tmux kill-session -t {} 2>/dev/null
EOF

# Compress old logs
ssh -i smartbuild-*.pem ubuntu@98.83.207.85 << 'EOF'
    find /opt/*/sessions/*/logs -name "*.log" -mtime +3 -exec gzip {} \; 2>/dev/null
EOF
```

### Backup Procedures
```bash
# Backup all applications
ssh -i smartbuild-*.pem ubuntu@98.83.207.85 << 'EOF'
    timestamp=$(date +%Y%m%d_%H%M%S)
    for app in smartbuild smartmonitor smartdeploy; do
        tar -czf /opt/backups/${app}_$timestamp.tar.gz \
            --exclude='sessions' --exclude='venv' --exclude='__pycache__' \
            /opt/$app/ 2>/dev/null
    done
    echo "Backups created in /opt/backups/"
EOF
```

---

## 📊 Cost Optimization

### Current Monthly Costs
- **EC2 t3.large**: ~$60/month (with Reserved Instance discount)
- **CloudFront (4 distributions)**: ~$15/month
- **S3 Storage**: <$1/month
- **Data Transfer**: ~$10/month
- **Total**: ~$85/month

### Cost Saving Tips
1. Use Reserved Instances (save 30-50%)
2. Consider t3a.large (AMD, 10% cheaper)
3. Stop instance during non-business hours
4. Clean up old sessions regularly

---

## 🆕 Recent Changes (2025-09-03)

### Critical Fixes Applied Today

1. **nginx Configuration Fixed**
   - Port 80 now correctly routes to SmartDeploy (8511) instead of SmartBuild
   - Port 8080 added for SmartBuild access
   - Port 8510 configured as alternative SmartDeploy access

2. **CloudFront Origins Updated**
   - SmartBuild CloudFront: Changed from port 80 → 8080
   - SmartMonitor CloudFront: Changed from port 8080 → 8504
   - SmartDeploy CloudFront: Remains on port 80

3. **Root Cause Analysis**
   - Issue: All CloudFront distributions were hitting port 80
   - Solution: Separated each app to unique port
   - Result: All applications now accessible via their respective CloudFront URLs

4. **SmartDeploy Deployment Pipeline Tab Fixed (Session 2)**
   - Deployed missing `claude_error_fixer.py` dependency

5. **Job Queue Completion Detection Fixed (Critical)**
   - **Issue**: Jobs stuck at 50% even when requirements.json existed
   - **Root Cause**: Hardcoded 2-minute wait before checking completion
   - **Solution**: Reduced wait to 5 seconds for requirements, 10-30s for others
   - **Result**: Jobs now marked complete in 2-5 seconds (was 2+ minutes)
   - **Files Modified**: `utils/job_queue_manager_v2.py`
   - **Additional Features**:
     - File modification time validation prevents false positives
     - Force check mechanism for stuck jobs
     - Enhanced logging for debugging
   - Fixed import errors in deployment_pipeline.py
   - Deployment Pipeline tab now visible and functional

5. **SmartMonitor 504 Gateway Timeout Resolved (Session 2)**
   - Added missing security group rule for port 8504
   - Fixed EC2 security group sg-04faa46620df113da
   - Service now accessible via CloudFront

### Version Updates
- SmartBuild: v5.11.7 → v5.11.10 (Monitor fixes & logging)
- SmartDeploy: v5.10.14 (newly deployed, with deployment pipeline fixes)

---

## 📞 Support Information

### Quick SSH Access
```bash
# From deploy/ directory
./ssh-to-ec2.sh

# Or directly
ssh -i smartbuild-20250824180036.pem ubuntu@98.83.207.85
```

### Service Restart Commands
```bash
sudo systemctl restart smartbuild      # Main SmartBuild app
sudo systemctl restart smartmonitor    # Monitor app
sudo systemctl restart smartdeploy     # SmartDeploy app
sudo systemctl restart console-monitor # Console viewer
sudo systemctl restart job-queue-control # Control center
sudo systemctl restart nginx           # Web server
```

### Log Viewing
```bash
# Follow logs in real-time
sudo journalctl -u smartbuild -f
sudo journalctl -u smartmonitor -f
sudo journalctl -u smartdeploy -f

# View last 100 lines
sudo journalctl -u SERVICE_NAME -n 100 --no-pager
```

### Critical Notes
1. **ALWAYS deploy SmartBuild utils to BOTH** `/opt/smartbuild/` and `/opt/smartmonitor/`
2. **NEVER modify job_queue_manager_v2.py** without thorough testing
3. **ALWAYS backup before major updates**
4. **Monitor tmux sessions** after deployment
5. **CloudFront changes take 5-15 minutes** to propagate globally

---

## ✅ Deployment Validation Summary

| Component | Status | Test Command |
|-----------|--------|--------------|
| SmartDeploy | ✅ Running | `curl http://98.83.207.85/_stcore/health` |
| SmartBuild | ✅ Running | `curl http://98.83.207.85:8080/_stcore/health` |
| SmartMonitor | ✅ Running | `curl http://98.83.207.85:8504/_stcore/health` |
| Control Center | ✅ Running | `curl http://98.83.207.85:8507/_stcore/health` |
| nginx | ✅ Configured | `sudo nginx -t` |
| CloudFront | ✅ Updated | Cache invalidations created |

---

*Last deployed: 2025-09-03 | All systems operational*
*Deployed by: Claude Code Assistant*