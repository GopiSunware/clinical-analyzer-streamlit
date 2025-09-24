# 📁 SmartBuild Deploy Directory

This directory contains all deployment-related files for SmartBuild SPA.

## 📚 Documentation Structure

### Primary Guides (Use These!)
1. **[MASTER_DEPLOYMENT_GUIDE.md](MASTER_DEPLOYMENT_GUIDE.md)** - Complete deployment documentation (v5.11.7)
2. **[CONSOLE_MONITOR_DOCUMENTATION.md](CONSOLE_MONITOR_DOCUMENTATION.md)** - Console log monitoring system
3. **[COMPLETE_DEPLOYMENT_GUIDE.md](COMPLETE_DEPLOYMENT_GUIDE.md)** - Original comprehensive guide (v5.11.7)
4. **[EC2_CONSOLE_ACCESS.md](EC2_CONSOLE_ACCESS.md)** - SSH and console access instructions

### Deployment Scripts
- **deploy-latest-fixes.sh** - Latest deployment script (v5.11.3) - RECOMMENDED
- **deploy-console-monitor.sh** - Deploy console monitor updates (NEW)
- **deploy-to-both-sites.sh** - Deploy to both main and monitor
- **emergency-recovery.sh** - System recovery script
- **fix-stuck-jobs.sh** - Fix stuck job queues

### Production Files
- **console_log_monitor_production.py** - Production version of console monitor (v3.0)

### Legacy Documentation (For Reference)
- DEPLOYMENT_COMPLETE.md
- DEPLOYMENT_DETAILS.md
- DEPLOYMENT_FILES.md
- DEPLOYMENT_STEPS.md
- DUAL_APP_DEPLOYMENT.md
- EC2_DEPLOYMENT_GUIDE.md
- STREAMLIT_CONSOLE_ACCESS.md
- ec2-sizing-guide.md

## ⚡ Quick Start

```bash
# Deploy latest code (v5.11.3)
./deploy-latest-fixes.sh

# Emergency recovery
./emergency-recovery.sh

# Fix stuck jobs
./fix-stuck-jobs.sh
```

## 🌐 Production URLs
- **Main App**: https://d10z4f7h6vaz0k.cloudfront.net/
- **Monitor**: https://d1b2mw2j81ms4x.cloudfront.net/
- **Console Monitor**: https://d23i1hoblpve1z.cloudfront.net/ (NEW)

## 🔑 SSH Access
```bash
ssh -i smartbuild-20250824180036.pem ubuntu@98.83.207.85
```

## 📋 Latest Updates (v5.11.7)
- Fixed: Button state now correctly updates based on selected diagram
- Fixed: Progress bars added to all tabs with consistent UI matching R&S tab pattern
- Fixed: Job filtering is now diagram-specific to prevent cross-diagram interference
- Enhancement: Progress displays show job status, percentage, elapsed time, and refresh controls
- Impact: All tabs now have unified UX and real-time progress tracking

---
*For complete deployment instructions, see [MASTER_DEPLOYMENT_GUIDE.md](MASTER_DEPLOYMENT_GUIDE.md)*