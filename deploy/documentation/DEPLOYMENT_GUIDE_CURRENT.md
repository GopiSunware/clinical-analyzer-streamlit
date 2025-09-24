# 🚀 SmartBuild Deployment Guide - Current Version

*Last Updated: 2025-09-10 | Version 5.15.1*

## 📚 Quick Links
- [Production URLs](#production-urls)
- [Quick Deploy](#quick-deploy)
- [Architecture](#architecture)
- [Troubleshooting](#troubleshooting)

---

## 🌐 Production URLs

### CloudFront Applications (HTTPS) - Recommended
- **Main App**: https://d10z4f7h6vaz0k.cloudfront.net/
- **Monitor**: https://d1b2mw2j81ms4x.cloudfront.net/
- **Control Center**: https://d23i1hoblpve1z.cloudfront.net/

### Direct EC2 Access (HTTP) - For Testing
- **Main App**: http://98.83.207.85:8505
- **Monitor**: http://98.83.207.85:8504
- **Control Center**: http://98.83.207.85:8507

### EC2 Instance Details
- **IP**: 98.83.207.85
- **Type**: t3.large (8GB RAM)
- **Region**: us-east-1 (N. Virginia)
- **SSH**: `ssh -i deploy/keys/smartbuild-20250824180036.pem ubuntu@98.83.207.85`

---

## ⚡ Quick Deploy

### Automated Deployment (Recommended)
```bash
# From project root
./deploy_to_ec2.sh
```

### What the Script Does:
1. Creates backup of current deployment
2. Syncs all Python files and utils/
3. Updates requirements on EC2
4. Restarts all services
5. Verifies deployment success

---

## 🏗️ Architecture

### Directory Structure on EC2
```
/opt/
├── smartbuild/                      # Main application
│   ├── smartbuild_spa_middleware.py # Main app entry point
│   ├── utils/                       # Shared utilities
│   ├── config/                      # Configuration files
│   ├── venv/                        # Python virtual environment
│   └── sessions/
│       ├── active/                  # Active sessions
│       └── deleted/                 # Archived sessions
│
├── smartmonitor/                    # Monitor application
│   ├── smartbuild_monitor.py       # Monitor UI
│   └── utils/                      # Must sync with main app
│
└── job_queue_control/               # Control Center
    └── job_queue_control.py        # Unified control panel
```

### Active Services
```bash
# Check all services
sudo systemctl status smartbuild smartmonitor job-queue-monitor

# Service ports:
# - 8505: Main SmartBuild application
# - 8504: SmartBuild Monitor
# - 8507: Job Queue Control Center
```

---

## 🔧 Key Components

### 1. Main Application (Port 8505)
- **File**: `/opt/smartbuild/smartbuild_spa_middleware_dynamic.py`
- **Service**: `smartbuild.service`
- **Features**: Dynamic TMUX/SubAgent modes, session management, all artifact generation tabs

### 2. Monitor Application (Port 8504)
- **File**: `/opt/smartmonitor/smartbuild_monitor.py`
- **Service**: `smartmonitor.service`
- **Features**: Job queue monitoring, progress tracking, session overview

### 3. Control Center (Port 8507)
- **File**: `/opt/job_queue_control/job_queue_control.py`
- **Service**: `job-queue-control.service`
- **Features**: Service control, log viewing, tmux session management

**Note**: For local startup commands, see CLAUDE.md. Do not run these directly on EC2 - use systemd services instead.

### 4. Background Job Monitor
- **File**: `/opt/smartbuild/job_queue_monitor.py`
- **Service**: `job-queue-monitor.service`
- **Features**: Processes job queue, manages tmux sessions, updates job status

---

## 🐛 Troubleshooting

### Common Issues & Solutions

#### 1. Services Not Starting
```bash
# Check service logs
sudo journalctl -u smartbuild -n 50
sudo journalctl -u smartmonitor -n 50

# Restart services
sudo systemctl restart smartbuild smartmonitor job-queue-monitor
```

#### 2. Jobs Stuck in Queue
```bash
# SSH to EC2
ssh -i deploy/keys/smartbuild-*.pem ubuntu@98.83.207.85

# Check job queue
cat /opt/smartbuild/sessions/active/*/job_queue.json

# Clear lock file if exists
rm -f /opt/smartbuild/sessions/.job_queue_monitor.lock

# Restart job monitor
sudo systemctl restart job-queue-monitor
```

#### 3. Tmux Sessions Issues
```bash
# List all tmux sessions
tmux ls

# Kill orphaned sessions
tmux kill-server

# Or selectively kill SmartBuild sessions
for s in $(tmux ls | grep '^smartbuild_' | cut -d: -f1); do
    tmux kill-session -t "$s"
done
```

#### 4. CloudFront Not Working
- Check EC2 instance is running
- Verify security groups allow traffic on ports 8504-8507
- CloudFront changes take 5-10 minutes to propagate
- Clear browser cache if seeing old content

---

## 📋 Deployment Checklist

### Before Deployment
- [ ] Test changes locally
- [ ] Commit code to git
- [ ] Check EC2 instance is healthy
- [ ] Verify SSH access works

### During Deployment
- [ ] Run `./deploy_to_ec2.sh`
- [ ] Watch for any error messages
- [ ] Wait for services to restart

### After Deployment
- [ ] Test main app: https://d10z4f7h6vaz0k.cloudfront.net/
- [ ] Test monitor: https://d1b2mw2j81ms4x.cloudfront.net/
- [ ] Test control: https://d23i1hoblpve1z.cloudfront.net/
- [ ] Check service logs for errors
- [ ] Verify job processing works

---

## 🔐 Security Notes

- **SSH Keys**: Keep `.pem` files secure, never commit to git
- **Security Groups**: Only required ports are open (8504-8507, 22)
- **IAM Roles**: EC2 uses roles for AWS access, not keys
- **Updates**: Run `sudo apt update && sudo apt upgrade` regularly

---

## 📞 Quick Diagnostics

### System Health Check
```bash
ssh -i deploy/keys/smartbuild-*.pem ubuntu@98.83.207.85 << 'EOF'
    echo "=== SYSTEM STATUS ==="
    echo "Services:"
    systemctl is-active smartbuild smartmonitor job-queue-monitor
    echo -e "\nTmux Sessions:"
    tmux ls 2>/dev/null | wc -l
    echo -e "\nActive Sessions:"
    ls /opt/smartbuild/sessions/active/ 2>/dev/null | wc -l
    echo -e "\nDisk Usage:"
    df -h /opt/smartbuild
    echo -e "\nRecent Errors:"
    sudo journalctl -p err -n 5 --no-pager
EOF
```

### Service Restart
```bash
# Restart all services
ssh -i deploy/keys/smartbuild-*.pem ubuntu@98.83.207.85 "
    sudo systemctl restart smartbuild smartmonitor job-queue-monitor
    echo 'Services restarted'
"
```

---

## 📈 Current Version: 5.15.1

### Recent Updates
- **5.15.1**: Fixed XML truncated tag issues in diagram generation
- **5.15.0**: Clean architecture separation, TMUX/SubAgent modes
- **5.14.x**: UI consistency, progress bars, job queue improvements

### Key Features
- 10 specialized tabs for AWS solution generation
- Real-time progress tracking with auto-refresh
- Job queue system with timeout protection
- TMUX and SubAgent execution modes
- Comprehensive monitoring suite

---

*For historical version information, see `.md/v5.11.7/README.md`*