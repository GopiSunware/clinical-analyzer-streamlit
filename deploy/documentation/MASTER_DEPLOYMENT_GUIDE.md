# 🚀 SmartBuild Master Deployment Guide

*Last Updated: 2025-08-31 | Version 5.11.7*

## 📚 Quick Links
- [Production URLs](#production-urls)
- [Quick Deploy](#quick-deploy)
- [Architecture](#architecture)
- [Troubleshooting](#troubleshooting)
- [Console Monitor](#console-monitor)

---

## 🌐 Production URLs

### CloudFront Applications (HTTPS)
- **Main App**: https://d10z4f7h6vaz0k.cloudfront.net/
- **Monitor**: https://d1b2mw2j81ms4x.cloudfront.net/
- **Unified Monitor Control**: https://d23i1hoblpve1z.cloudfront.net/ *(NEW - Combined UI)*

### Direct EC2 Access (HTTP)
- **Main App**: http://98.83.207.85:8505
- **Monitor**: http://98.83.207.85:8504
- **Unified Monitor Control**: http://98.83.207.85:8507 *(Job Queue + Console Logs)*

### EC2 Instance
- **IP**: 98.83.207.85
- **Hostname**: ec2-98.83.207.85.compute-1.amazonaws.com
- **Type**: t3.large
- **Region**: us-east-1 (N. Virginia)
- **SSH**: `ssh -i smartbuild-20250824180036.pem ubuntu@98.83.207.85`

---

## ⚡ Quick Deploy

### Method 1: Automated Script (RECOMMENDED)
```bash
cd deploy
chmod +x deploy-latest-fixes.sh
./deploy-latest-fixes.sh
```

### Method 2: Manual Deployment
```bash
# Stop all services
ssh -i *.pem ubuntu@98.83.207.85 "sudo systemctl stop smartbuild smartmonitor console-monitor"

# Copy files
scp -i *.pem -r utils ubuntu@98.83.207.85:/tmp/
scp -i *.pem *.py ubuntu@98.83.207.85:/tmp/
scp -i *.pem console_log_monitor.py ubuntu@98.83.207.85:/tmp/

# Deploy to ALL locations (CRITICAL!)
ssh -i *.pem ubuntu@98.83.207.85 << 'EOF'
    sudo cp -r /tmp/utils/* /opt/smartbuild/utils/
    sudo cp -r /tmp/utils/* /opt/smartmonitor/utils/
    sudo cp /tmp/*.py /opt/smartbuild/
    sudo cp /tmp/*.py /opt/smartmonitor/
    sudo cp /tmp/console_log_monitor.py /opt/console_monitor/
    sudo chown -R ubuntu:ubuntu /opt/smartbuild/
    sudo chown -R ubuntu:ubuntu /opt/smartmonitor/
    sudo chown -R ubuntu:ubuntu /opt/console_monitor/
    sudo systemctl restart smartbuild smartmonitor console-monitor
EOF
```

---

## 🏗️ Architecture

### Directory Structure
```
EC2 Instance:
/opt/
├── smartbuild/             # Main application
│   ├── smartbuild_spa_middleware.py
│   ├── utils/              # MUST be synchronized with monitor!
│   └── sessions/
│       ├── active/         # Active sessions
│       └── deleted/        # Soft-deleted sessions
│
└── smartmonitor/           # Monitor application
    ├── smartbuild_monitor.py
    └── utils/              # MUST be synchronized with main!
```

### Critical Shared Components
These files MUST be identical in both locations:
- `utils/job_queue_manager_v2.py` - Core job processing
- `utils/common_types.py` - Job type definitions
- `utils/prompt_preparers.py` - Prompt generation

### Service Configuration

**Active Services (3 total):**
1. **smartbuild.service** - Main Application (Port 8505)
2. **smartmonitor.service** - SmartBuild Monitor (Port 8504)  
3. **job-queue-control.service** - Job Queue Control UI (Port 8507)

```ini
# /etc/systemd/system/smartbuild.service
[Unit]
Description=SmartBuild SPA Application
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/opt/smartbuild
Environment="PATH=/usr/local/bin:/usr/bin:/bin"
ExecStart=/opt/smartbuild/venv/bin/streamlit run smartbuild_spa_middleware.py --server.port 8505 --server.address 0.0.0.0
Restart=always

[Install]
WantedBy=multi-user.target
```

---

## 🔧 Key Features & Fixes (v5.11.7)

### Latest Updates
1. **Tab Implementation Fixes** (v5.11.7)
   - Button state now correctly updates based on selected diagram
   - Progress bars added to all tabs with consistent UI matching R&S tab pattern
   - Job filtering is now diagram-specific to prevent cross-diagram interference
   - Progress displays show job status, percentage, elapsed time, and refresh controls
   - All tabs (Cost Analysis, Tech Doc, Terraform, CloudFormation) now have unified UX

2. **Job Queue Fixes** (v5.11.3)
   - Requirements/Architecture jobs use main tmux session
   - Session-level job scanning for run_id=None jobs
   - Proper tmux session naming with None handling

3. **Deletion Improvements**
   - Enhanced logging (before/during/after)
   - Kills ALL associated tmux sessions (including sb_ca_, sb_arch_, etc.)
   - Prevents tmux recreation after deletion

4. **Session Management**
   - Checks active folder before creating tmux
   - Proper cleanup on deletion
   - No zombie sessions

5. **Console Monitor v3.0**
   - Real-time log viewing via CloudFront
   - Fixed-height scrollable containers (600px)
   - Auto-scroll to bottom for new logs
   - Split view for multiple services
   - Accessible at https://d23i1hoblpve1z.cloudfront.net/

### Job Type Mappings (CRITICAL!)
```python
# From utils/common_types.py
'requirements_extraction' -> 'req' -> uses main session
'solution_generation' -> 'sol' -> uses main session  
'architecture_diagram' -> 'arch' -> uses main session
'cost_analysis' -> 'ca' (NOT 'co'!)
'technical_documentation' -> 'td'
'terraform_code' -> 'tf'
'cloudformation_template' -> 'cf'
```

---

## 🐛 Troubleshooting

### Common Issues

#### 1. Jobs Stuck in "Queued"
```bash
# Check job queue
ssh -i *.pem ubuntu@98.83.207.85
cat /opt/smartbuild/sessions/active/*/job_queue.json

# Remove lock file
rm -f /opt/smartbuild/sessions/.job_queue_monitor.lock

# Restart service
sudo systemctl restart smartbuild
```

#### 2. Orphaned Tmux Sessions
```bash
# List all tmux sessions
tmux ls

# Kill orphaned sessions
for s in $(tmux ls | grep '^sb_' | cut -d: -f1); do
    tmux kill-session -t "$s"
done
```

#### 3. Session Not Deleting
```bash
# Check logs for deletion process
sudo journalctl -u smartbuild | grep "DELETE"

# Manually clean up
tmux kill-session -t smartbuild_s_XXXXX
sudo rm -rf /opt/smartbuild/sessions/active/session_XXXXX
```

### Monitoring Commands
```bash
# Live logs
sudo journalctl -u smartbuild -f      # Main app
sudo journalctl -u smartmonitor -f    # Monitor

# Service status
sudo systemctl status smartbuild
sudo systemctl status smartmonitor

# Process check
ps aux | grep streamlit

# Tmux sessions
tmux ls

# Disk usage
df -h /opt/smartbuild/sessions
```

---

## 📋 Pre-Deployment Checklist

- [ ] Backup current deployment
- [ ] Test locally first
- [ ] Check EC2 instance health
- [ ] Verify CloudFront distributions active
- [ ] Have SSH key ready
- [ ] Stop services before deploying
- [ ] Deploy to BOTH /opt/smartbuild AND /opt/smartmonitor
- [ ] Clear lock files
- [ ] Kill orphaned tmux sessions
- [ ] Restart services
- [ ] Verify both apps accessible
- [ ] Check logs for errors

---

## 🔐 Security Notes

- Never commit .pem files to git
- Use IAM roles for AWS access (not keys)
- Keep security groups restrictive
- Regular security updates: `sudo apt update && sudo apt upgrade`
- Monitor CloudWatch logs for suspicious activity

---

## 📞 Support

### Quick Diagnostics
```bash
# Run this for quick system check
ssh -i *.pem ubuntu@98.83.207.85 << 'EOF'
    echo "=== SYSTEM STATUS ==="
    echo "Services:"
    systemctl is-active smartbuild smartmonitor
    echo -e "\nTmux Sessions:"
    tmux ls 2>/dev/null | wc -l
    echo -e "\nActive Sessions:"
    ls /opt/smartbuild/sessions/active/ | wc -l
    echo -e "\nDisk Usage:"
    df -h /opt/smartbuild
    echo -e "\nLast Errors:"
    sudo journalctl -u smartbuild -p err -n 5
EOF
```

### Recovery Script
If the system is unresponsive, run:
```bash
cd deploy
./emergency-recovery.sh
```

---

## 📈 Version History

- **v5.11.9** (2025-09-02): Unified Monitor Control Center
  - Created unified_monitor_control.py combining all monitoring features
  - Single UI for: Job Queue Control, Console Logs, Tmux Sessions, Session Logs
  - CloudFront d23i1hoblpve1z.cloudfront.net now serves Unified Monitor Control
  - Final ports: 8505 (Main), 8504 (Monitor), 8507 (Unified Control)
  - Features: Status Dashboard, Live Console, Job Queue Logs, Tmux Output, Session History
  - All services accessible via CloudFront and direct EC2
- **v5.11.8** (2025-01-31): Progress Probing (V3) & Task ID Correlation (V4) Systems
  - Added Claude progress probing every 30 seconds
  - Added task ID correlation for precise tracking
  - Enhanced monitor UI with real-time progress
  - Deployed .claude/agents directory
  - See [DEPLOYMENT_MANIFEST.md](DEPLOYMENT_MANIFEST.md) for details
- **v5.11.7** (2025-08-31): Tab Implementation Fixes - Button State & Progress Bar Enhancements
  - Fixed: Button state now correctly updates based on selected diagram
  - Fixed: Progress bars added to all tabs with consistent UI matching R&S tab pattern
  - Fixed: Job filtering is now diagram-specific to prevent cross-diagram interference
  - Enhancement: Progress displays show job status, percentage, elapsed time, and refresh controls
  - Impact: All tabs now have unified UX and real-time progress tracking
- **v5.11.6** (2025-08-31): EC2 Instance Upgrade & Region Migration
  - Upgraded EC2 instance from t3.medium to t3.large (8GB RAM)
  - Migrated from ap-southeast-1 to us-east-1 region
  - New IP: 98.83.207.85 (was 13.217.58.81)
- **v5.11.3** (2025-08-31): Fixed job queue, deletion, tmux management, console monitor
  - Added Console Monitor for real-time log viewing
  - Fixed requirements/architecture job handling
  - Fixed PATH issues in systemd services
- **v5.11.2**: Button logic fixes, enhanced logging
- **v5.11.1**: Job queue persistence, bulk generation
- **v5.11.0**: Added Cost Analysis tab
- **v5.10.x**: Session management improvements

---

*End of Master Deployment Guide*