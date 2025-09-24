# 📜 Console Monitor Complete Documentation

*Last Updated: 2025-08-31 | Version 3.0*

## 📋 Table of Contents
- [Overview](#overview)
- [Features](#features)
- [URLs and Access](#urls-and-access)
- [Architecture](#architecture)
- [Installation](#installation)
- [Deployment](#deployment)
- [Configuration](#configuration)
- [Usage Guide](#usage-guide)
- [Troubleshooting](#troubleshooting)
- [Version History](#version-history)

---

## 🎯 Overview

The Console Monitor is a real-time log monitoring application for SmartBuild applications. It provides a web-based interface to view system logs from both the main SmartBuild application and the SmartBuild Monitor, similar to viewing tmux sessions but for application console output.

### Key Benefits
- Real-time log monitoring via web interface
- No SSH access required for log viewing
- Color-coded log levels for quick issue identification
- Split-view for simultaneous monitoring of multiple services
- Search and filter capabilities
- Auto-refresh with configurable intervals

---

## ✨ Features

### Core Features
1. **Multi-Service Monitoring**
   - SmartBuild Main App logs
   - SmartBuild Monitor logs
   - Console Monitor self-logs

2. **View Modes**
   - **Split View**: Side-by-side display of main app and monitor
   - **Individual Tabs**: Dedicated view for each service
   - **Filtered View**: Combined logs with filtering options

3. **Log Management**
   - Real-time log streaming from systemd journal
   - Configurable line count (50-1000 lines)
   - Auto-scroll to latest entries
   - Manual refresh option

4. **Search & Filter**
   - Search across all logs
   - Filter by log level (Error, Warning, Info, Debug)
   - Filter by source application
   - Keyword filtering

5. **Visual Enhancements**
   - Color-coded log levels
   - Service status indicators (Running/Stopped)
   - Timestamp display
   - Icon indicators for each service

---

## 🌐 URLs and Access

### Production URLs

#### CloudFront (HTTPS - Recommended)
- **Console Monitor**: https://d23i1hoblpve1z.cloudfront.net/

#### Direct EC2 Access (HTTP - Backup)
- **Console Monitor**: http://98.83.207.85:8507

### Local Development
- **Default**: http://localhost:8507

---

## 🏗️ Architecture

### System Architecture
```
┌─────────────────────────────────────────────┐
│           CloudFront Distribution           │
│         (d23i1hoblpve1z.cloudfront.net)    │
└─────────────────┬───────────────────────────┘
                  │ HTTPS
                  ▼
┌─────────────────────────────────────────────┐
│              EC2 Instance                   │
│         (98.83.207.85:8507)                │
│                                             │
│  ┌─────────────────────────────────────┐   │
│  │    Console Monitor Service          │   │
│  │  (console_log_monitor_v2.py)       │   │
│  └──────────┬──────────────────────────┘   │
│             │ Reads logs via              │
│             ▼                             │
│  ┌─────────────────────────────────────┐   │
│  │     systemd journal (journalctl)    │   │
│  └──────────┬──────────────────────────┘   │
│             │                             │
│      ┌──────┴──────┬──────────────┐      │
│      ▼             ▼              ▼      │
│  SmartBuild   SmartMonitor   Console     │
│   Service      Service       Monitor     │
└─────────────────────────────────────────────┘
```

### Component Details

1. **Console Monitor Application**
   - Built with Streamlit
   - Runs on port 8507
   - Managed by systemd service

2. **Log Source**
   - Reads from systemd journal using `journalctl`
   - Requires sudo permissions (configured via sudoers)
   - No file-based logging required

3. **Service Integration**
   - Monitors: `smartbuild.service`
   - Monitors: `smartmonitor.service`
   - Monitors: `console-monitor.service`

---

## 📦 Installation

### Prerequisites
```bash
# System requirements
- Ubuntu 20.04 or later
- Python 3.8+
- systemd
- sudo access

# Python packages
pip install streamlit
```

### Local Installation
```bash
# 1. Clone or copy the console monitor script
cp console_log_monitor_v2.py /opt/console_monitor/

# 2. Install dependencies
pip install streamlit

# 3. Test locally
streamlit run console_log_monitor_v2.py --server.port 8507
```

### EC2 Installation
```bash
# 1. Create application directory
sudo mkdir -p /opt/console_monitor
sudo chown ubuntu:ubuntu /opt/console_monitor

# 2. Copy application file
sudo cp console_log_monitor_v2.py /opt/console_monitor/
sudo chown ubuntu:ubuntu /opt/console_monitor/console_log_monitor_v2.py

# 3. Create systemd service
sudo tee /etc/systemd/system/console-monitor.service > /dev/null << 'EOF'
[Unit]
Description=Console Log Monitor
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/opt/console_monitor
Environment="PATH=/usr/local/bin:/usr/bin:/bin"
ExecStart=/usr/local/bin/streamlit run console_log_monitor_v2.py --server.port 8507 --server.headless true
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# 4. Configure sudo permissions for journalctl
echo "ubuntu ALL=(ALL) NOPASSWD: /usr/bin/journalctl" | sudo tee /etc/sudoers.d/console-monitor

# 5. Start and enable service
sudo systemctl daemon-reload
sudo systemctl enable console-monitor
sudo systemctl start console-monitor
```

---

## 🚀 Deployment

### Deploy to EC2

#### Using Automated Script
```bash
cd deploy
# The production version is maintained in deploy/console_log_monitor_production.py
./deploy-console-monitor.sh
```

**Important**: The production version is kept in `deploy/console_log_monitor_production.py` to ensure consistency between deployments.

#### Manual Deployment
```bash
# 1. Copy file to EC2
scp -i smartbuild-*.pem console_log_monitor_v2.py ubuntu@98.83.207.85:/tmp/

# 2. Deploy on EC2
ssh -i smartbuild-*.pem ubuntu@98.83.207.85 << 'EOF'
    sudo cp /tmp/console_log_monitor_v2.py /opt/console_monitor/
    sudo chown ubuntu:ubuntu /opt/console_monitor/console_log_monitor_v2.py
    sudo systemctl restart console-monitor
EOF

# 3. Verify deployment
curl -I http://98.83.207.85:8507
```

### CloudFront Setup

#### Create Distribution
```bash
aws cloudfront create-distribution \
  --origin-domain-name ec2-98.83.207.85.compute-1.amazonaws.com \
  --origin-id console-monitor-origin \
  --default-root-object index.html \
  --origin-custom-config '{
    "HTTPPort": 8507,
    "HTTPSPort": 443,
    "OriginProtocolPolicy": "http-only"
  }' \
  --default-cache-behavior '{
    "TargetOriginId": "console-monitor-origin",
    "ViewerProtocolPolicy": "redirect-to-https",
    "AllowedMethods": ["GET", "HEAD", "OPTIONS", "PUT", "POST", "PATCH", "DELETE"],
    "CachedMethods": ["GET", "HEAD"],
    "Compress": true,
    "ForwardedValues": {
      "QueryString": true,
      "Headers": ["*"],
      "Cookies": {"Forward": "all"}
    },
    "MinTTL": 0,
    "DefaultTTL": 0,
    "MaxTTL": 0
  }' \
  --enabled \
  --comment "Console Monitor for SmartBuild"
```

#### Configure for WebSockets
- Set Origin Protocol Policy: HTTP only
- Configure cache behaviors to forward all headers
- Enable all HTTP methods
- Set TTL values to 0 for real-time updates

---

## ⚙️ Configuration

### Service Configuration
```ini
# /etc/systemd/system/console-monitor.service
[Unit]
Description=Console Log Monitor
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/opt/console_monitor
Environment="PATH=/usr/local/bin:/usr/bin:/bin"
ExecStart=/usr/local/bin/streamlit run console_log_monitor_v2.py --server.port 8507 --server.headless true
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

### Sudo Permissions
```bash
# /etc/sudoers.d/console-monitor
ubuntu ALL=(ALL) NOPASSWD: /usr/bin/journalctl
```

### Security Group Rules
```
Port 8507: Custom TCP from CloudFront IP ranges
Port 8507: Custom TCP from your IP (for testing)
```

### Nginx Configuration (Optional)
```nginx
server {
    listen 80;
    server_name console-monitor.yourdomain.com;

    location / {
        proxy_pass http://localhost:8507;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 86400;
    }
}
```

---

## 📖 Usage Guide

### Accessing the Console Monitor

1. **Via CloudFront (Recommended)**
   - Navigate to: https://d23i1hoblpve1z.cloudfront.net/
   - No VPN or SSH required
   - Accessible from anywhere

2. **Direct EC2 Access**
   - Navigate to: http://98.83.207.85:8507
   - Requires security group access
   - Useful for debugging

### Interface Overview

#### Main Components
1. **Header**
   - Application title and version
   - Current timestamp

2. **Sidebar Controls**
   - Auto-refresh toggle and interval
   - Lines to display (50-1000)
   - Auto-scroll toggle
   - Search functionality
   - Service status indicators

3. **Main Content Area**
   - Tab navigation
   - Log display area
   - Statistics and metrics

### Using Different Views

#### Split View
- Shows Main App and Monitor logs side-by-side
- Useful for correlating events between services
- Independent scrolling for each pane

#### Individual Service Tabs
- Dedicated view for each service
- Full-width log display
- Service-specific controls

#### Filtered View
- Combines logs from all services
- Apply filters by:
  - Log level (Error, Warning, Info, Debug)
  - Source service
  - Keywords
- Useful for tracking specific issues across services

### Search and Filter

1. **Quick Search**
   - Enter search term in sidebar
   - Click "Search" button
   - Results show first 10 matches

2. **Advanced Filtering**
   - Go to "Filtered View" tab
   - Select log level filter
   - Choose source service
   - Enter keyword filter
   - View filtered results in real-time

### Interpreting Log Colors

- 🔴 **Red**: Errors, Exceptions, Failures
- 🟠 **Orange**: Warnings
- 🔵 **Blue**: Info messages
- ⚫ **Gray**: Debug messages
- 🟢 **Green**: Success messages, Job queue events
- ⚪ **Default**: Normal log entries

---

## 🔧 Troubleshooting

### Common Issues

#### 1. "Error accessing logs (may need sudo permissions)"
**Root Causes & Solutions:**

**Issue 1: PATH not found**
- Symptom: `journalctl: not found` error
- Cause: systemd service doesn't have journalctl in PATH
- Solution: Use full path `/usr/bin/journalctl` in code

**Issue 2: Error detection logic**  
- Symptom: Shows error when logs contain word "Error"
- Cause: Code checking `if "Error" not in content`
- Solution: Change to `if not content.startswith("Error")`

**Issue 3: Permissions (rare)**
```bash
# If needed, add sudo permissions for journalctl
echo "ubuntu ALL=(ALL) NOPASSWD: /usr/bin/journalctl" | sudo tee /etc/sudoers.d/console-monitor
```

#### 2. CloudFront shows "Failed to contact the origin"
**Solution:**
```bash
# Check service is running
sudo systemctl status console-monitor

# Check port is open
sudo netstat -tlnp | grep 8507

# Add port to security group
aws ec2 authorize-security-group-ingress \
  --group-id sg-xxx \
  --protocol tcp \
  --port 8507 \
  --cidr 0.0.0.0/0
```

#### 3. Service won't start
**Solution:**
```bash
# Check logs
sudo journalctl -u console-monitor -n 50

# Verify file permissions
ls -la /opt/console_monitor/

# Test manually
cd /opt/console_monitor
streamlit run console_log_monitor_v2.py --server.port 8507
```

#### 4. Logs show "No logs available"
**Solution:**
```bash
# Check service names are correct
sudo systemctl list-units | grep -E "smartbuild|smartmonitor|console-monitor"

# Verify journalctl access
sudo journalctl -u smartbuild -n 10
```

### Monitoring Commands

```bash
# Service status
sudo systemctl status console-monitor

# View service logs
sudo journalctl -u console-monitor -f

# Check port binding
sudo netstat -tlnp | grep 8507

# Test CloudFront
curl -I https://d23i1hoblpve1z.cloudfront.net/

# Check disk space
df -h /opt/console_monitor

# Monitor CPU/Memory
htop
```

---

## 📈 Version History

### Version 3.0 (2025-08-31 - Latest)
- Fixed HTML escaping issues in log display
- Added native Streamlit containers with fixed height (600px)
- Implemented auto-scroll to bottom for new logs
- Improved UI with proper scrollable containers
- JavaScript injection for auto-scroll functionality

### Version 2.0 (2025-08-31)
- Changed from file-based to systemd journal log reading
- Fixed PATH issues (using /usr/bin/journalctl)
- Fixed error detection logic (checking startswith instead of contains)
- Added sudo permissions configuration
- Improved error handling and messages

### Version 1.0 (2025-08-30)
- Initial release
- File-based log reading from /tmp/
- Split view and filtering features
- Color-coded log levels
- Auto-refresh functionality

---

## 🔐 Security Considerations

1. **Access Control**
   - CloudFront provides public HTTPS access
   - Consider adding authentication if sensitive
   - Restrict EC2 security group to specific IPs

2. **Log Sanitization**
   - Logs may contain sensitive information
   - Consider filtering sensitive data
   - Implement log rotation policies

3. **Sudo Permissions**
   - Limited to journalctl command only
   - No password required for specific command
   - Regular audit of sudoers file

---

## 📞 Support

For issues or questions:
1. Check service status: `sudo systemctl status console-monitor`
2. Review logs: `sudo journalctl -u console-monitor -n 100`
3. Test locally: `streamlit run console_log_monitor_v2.py`
4. Verify CloudFront: https://d23i1hoblpve1z.cloudfront.net/

---

*End of Console Monitor Documentation*