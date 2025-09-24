# SmartBuild Dual Application Deployment Guide

## 🚀 Overview

This guide explains how to deploy both SmartBuild SPA and SmartBuild Monitor on a single EC2 instance with separate CloudFront URLs.

## 📋 Architecture

```
Single EC2 Instance (t3.large)
├── /opt/smartbuild/                    # Single folder for both apps
│   ├── smartbuild_spa_middleware.py    # Main app (port 8505)
│   ├── smartbuild_monitor.py           # Monitor app (port 8504)
│   ├── utils/                          # Shared utilities
│   ├── sessions/                       # Shared session data
│   └── venv/                           # Shared Python environment

Nginx (port 80)
├── / → localhost:8505                  # Main app
└── /monitor → localhost:8504           # Monitor app

CloudFront Distribution
├── https://d10z4f7h6vaz0k.cloudfront.net/         # Main app
└── https://d10z4f7h6vaz0k.cloudfront.net/monitor/ # Monitor app
```

## 🔧 Initial Deployment

### Prerequisites
- EC2 instance already running (t3.large recommended)
- SSH key file: `smartbuild-20250824180036.pem`
- Both apps tested locally:
  - Main: `streamlit run smartbuild_spa_middleware.py --server.port 8505`
  - Monitor: `streamlit run smartbuild_monitor.py --server.port 8504`

### Step 1: Deploy Both Applications

```bash
cd deploy
chmod +x deploy-dual-app.sh
./deploy-dual-app.sh 98.83.207.85
```

This script will:
1. Stop existing services
2. Upload both applications
3. Configure Nginx for dual routing
4. Set up systemd services
5. Start both services
6. Verify deployment

### Step 2: Verify Services

```bash
# Check main app service
ssh -i smartbuild-20250824180036.pem ubuntu@98.83.207.85 \
  'sudo systemctl status smartbuild'

# Check monitor service
ssh -i smartbuild-20250824180036.pem ubuntu@98.83.207.85 \
  'sudo systemctl status smartmonitor'

# Check Nginx
ssh -i smartbuild-20250824180036.pem ubuntu@98.83.207.85 \
  'sudo systemctl status nginx'
```

## 📝 Quick Updates

### Update Monitor Only
```bash
cd deploy
chmod +x quick-update-monitor.sh
./quick-update-monitor.sh 98.83.207.85
```

### Update Main App Only
```bash
cd deploy
chmod +x quick-update-main.sh
./quick-update-main.sh 98.83.207.85
```

### Update Both Apps
```bash
cd deploy
./deploy-dual-app.sh 98.83.207.85
```

## 🌐 Access URLs

### Direct EC2 Access (HTTP)
- Main App: http://98.83.207.85/
- Monitor: http://98.83.207.85/monitor/

### CloudFront Access (HTTPS)
- Main App: https://d10z4f7h6vaz0k.cloudfront.net/
- Monitor: https://d10z4f7h6vaz0k.cloudfront.net/monitor/

## 🛠️ Service Management

### View Logs
```bash
# Main app logs
ssh -i smartbuild-20250824180036.pem ubuntu@98.83.207.85 \
  'sudo journalctl -u smartbuild -f'

# Monitor logs
ssh -i smartbuild-20250824180036.pem ubuntu@98.83.207.85 \
  'sudo journalctl -u smartmonitor -f'

# Nginx logs
ssh -i smartbuild-20250824180036.pem ubuntu@98.83.207.85 \
  'sudo tail -f /var/log/nginx/access.log'
```

### Restart Services
```bash
# Restart main app
ssh -i smartbuild-20250824180036.pem ubuntu@98.83.207.85 \
  'sudo systemctl restart smartbuild'

# Restart monitor
ssh -i smartbuild-20250824180036.pem ubuntu@98.83.207.85 \
  'sudo systemctl restart smartmonitor'

# Restart both
ssh -i smartbuild-20250824180036.pem ubuntu@98.83.207.85 \
  'sudo systemctl restart smartbuild smartmonitor'
```

### Stop/Start Services
```bash
# Stop services
ssh -i smartbuild-20250824180036.pem ubuntu@98.83.207.85 \
  'sudo systemctl stop smartbuild smartmonitor'

# Start services
ssh -i smartbuild-20250824180036.pem ubuntu@98.83.207.85 \
  'sudo systemctl start smartbuild smartmonitor'
```

## 📊 Resource Usage

With both apps running on t3.large (2 vCPU, 4GB RAM):

```
Application          CPU    Memory
---------------------------------
SmartBuild SPA      ~20%    ~800MB
SmartBuild Monitor  ~10%    ~400MB
Nginx               ~5%     ~50MB
System/Other        ~15%    ~750MB
---------------------------------
Total Used          ~50%    ~2GB
Available           50%     2GB
```

## 🔍 Troubleshooting

### Port Conflicts
```bash
# Check if ports are in use
ssh -i smartbuild-20250824180036.pem ubuntu@98.83.207.85 \
  'sudo netstat -tlnp | grep -E ":(8504|8505|80)"'
```

### Service Won't Start
```bash
# Check for Python errors
ssh -i smartbuild-20250824180036.pem ubuntu@98.83.207.85 \
  'cd /opt/smartbuild && source venv/bin/activate && python -m py_compile smartbuild_monitor.py'

# Check systemd logs
ssh -i smartbuild-20250824180036.pem ubuntu@98.83.207.85 \
  'sudo journalctl -u smartmonitor --since "5 minutes ago"'
```

### Nginx Issues
```bash
# Test configuration
ssh -i smartbuild-20250824180036.pem ubuntu@98.83.207.85 \
  'sudo nginx -t'

# Reload Nginx
ssh -i smartbuild-20250824180036.pem ubuntu@98.83.207.85 \
  'sudo systemctl reload nginx'
```

### Monitor App 404 Error
If monitor app shows 404:
1. Check Nginx configuration includes `/monitor` location
2. Verify smartmonitor service is running
3. Check if `--server.baseUrlPath monitor` is in service file

## 📁 File Locations on EC2

```
/opt/smartbuild/
├── smartbuild_spa_middleware.py       # Main app
├── smartbuild_monitor.py              # Monitor app
├── version_config.py                  # Version info
├── utils/                             # Shared utilities
├── sessions/                          # Session data
│   ├── active/                        # Active sessions
│   └── deleted/                       # Deleted sessions
├── venv/                              # Python environment
└── logs/                              # Application logs

/etc/systemd/system/
├── smartbuild.service                 # Main app service
└── smartmonitor.service               # Monitor service

/etc/nginx/sites-available/
└── default                            # Nginx config
```

## 🔄 CloudFront Configuration

To update CloudFront for dual app support:

1. **Add Cache Behavior for /monitor***
   - Path Pattern: `/monitor*`
   - Origin: Same EC2 instance
   - Caching: Disabled (TTL = 0)
   - Forward all headers, query strings, cookies

2. **Clear CloudFront Cache**
```bash
aws cloudfront create-invalidation \
  --distribution-id EY2D88MPRKCMZ \
  --paths "/*" "/monitor/*" \
  --region us-east-1
```

## 💰 Cost Considerations

Running both apps on single t3.large:
- **EC2**: ~$30/month (same as before)
- **CloudFront**: ~$2-5/month (minimal increase)
- **Total**: ~$35/month (no change)

Compared to separate instances:
- Two t3.small instances: ~$30/month
- Single t3.large: ~$30/month
- **Savings**: Better performance, same cost

## 🚨 Important Notes

1. **Shared Sessions**: Both apps access same `sessions/` folder
2. **Shared Python Environment**: Uses single venv for both apps
3. **Port Allocation**:
   - 8505: Main SmartBuild SPA
   - 8504: SmartBuild Monitor
   - 80: Nginx (routes to both)
4. **Memory Usage**: Monitor uses ~400MB, main app ~800MB
5. **Restart Order**: Can restart independently or together

## 📝 Deployment Checklist

- [ ] Test both apps locally first
- [ ] Backup existing EC2 configuration
- [ ] Run deployment script
- [ ] Verify both services running
- [ ] Test direct EC2 URLs
- [ ] Test CloudFront URLs
- [ ] Check logs for errors
- [ ] Monitor resource usage

---

**Last Updated**: 2025-08-29
**Deployment Version**: Dual App v1.0
**EC2 Instance**: 98.83.207.85 (t3.large)