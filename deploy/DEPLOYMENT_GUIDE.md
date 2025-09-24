# SmartBuild Deployment Guide & Prevention Strategies

**Last Updated**: September 7, 2025  
**Version**: 5.14.3  
**Author**: DevOps Team

## 🔍 Why These Issues Didn't Occur Locally

### Issue Analysis

| Issue | Local Environment | Production (EC2) | Root Cause |
|-------|------------------|------------------|------------|
| **Missing streamlit-autorefresh** | Installed in env_ccc venv | Not in production venv | Different virtual environments |
| **Missing SubAgent modules** | All files present locally | Files not deployed | Selective/manual deployment |
| **Type mismatch error** | Latest code with type checks | Old code without checks | Code not deployed after fix |
| **Missing tab_progress_bars** | File exists in utils/ | Not deployed to EC2 | Incomplete rsync command |

### Key Differences: Local vs Production

1. **Virtual Environment Drift**
   - **Local**: Uses `env_ccc/` with all development packages
   - **Production**: Uses `/opt/smartbuild/venv/` with only specified packages
   - **Problem**: No automatic sync of pip packages

2. **File System State**
   - **Local**: All 37 utils files always present
   - **Production**: Only files explicitly deployed via rsync
   - **Problem**: Manual, selective file deployment

3. **Code Updates**
   - **Local**: Changes tested immediately
   - **Production**: Requires manual deployment
   - **Problem**: Easy to forget deploying after fixes

4. **Import Resolution**
   - **Local**: Python finds all modules in working directory
   - **Production**: Only finds deployed modules
   - **Problem**: No deployment validation

## 🛡️ Prevention Strategies

### 1. **Use the Deployment Script ALWAYS**

```bash
# DON'T do manual deployments:
❌ rsync -avz utils/some_file.py ubuntu@server:/opt/

# DO use the deployment script:
✅ ./deploy_to_ec2.sh
```

### 2. **Pre-Deployment Checklist**

Before EVERY deployment, run:

```bash
# 1. Check Python syntax
python -m py_compile *.py utils/*.py

# 2. Update requirements
pip freeze > requirements.txt

# 3. Test imports locally
python -c "
from utils.tab_progress_bars import *
from utils.job_queue_manager_subagent import *
from utils.subagent_manager import *
print('✅ All imports successful')
"

# 4. Count files to deploy
echo "Local utils files: $(ls utils/*.py | wc -l)"

# 5. Run deployment script
./deploy_to_ec2.sh
```

### 3. **Post-Deployment Verification**

After deployment, ALWAYS verify:

```bash
# 1. Check services
ssh -i deploy/keys/smartbuild-*.pem ubuntu@98.83.207.85 "
  systemctl is-active smartbuild smartmonitor job-queue-control
"

# 2. Check for errors
ssh -i deploy/keys/smartbuild-*.pem ubuntu@98.83.207.85 "
  journalctl -u smartbuild.service -n 50 | grep -E 'ERROR|ModuleNotFoundError'
"

# 3. Test CloudFront URLs
curl -s -o /dev/null -w "%{http_code}\n" https://d10z4f7h6vaz0k.cloudfront.net/
```

## 📋 Complete Deployment Process

### Step 1: Prepare
```bash
# Update version if needed
vim version_config.py

# Ensure all files are saved
git status
```

### Step 2: Validate Locally
```bash
# Run the application locally
streamlit run smartbuild_spa_middleware_dynamic.py --server.port 8505

# Test all tabs work
# Stop with Ctrl+C when verified
```

### Step 3: Deploy
```bash
# Use the automated script
./deploy_to_ec2.sh

# This script handles:
# - All Python files
# - All utils modules  
# - Requirements installation
# - Service restarts
# - Health checks
```

### Step 4: Verify
```bash
# Check deployment succeeded
./verify_deployment.sh  # Create this script

# Manual verification
ssh -i deploy/keys/smartbuild-*.pem ubuntu@98.83.207.85 "
  cd /opt/smartbuild
  ls utils/*.py | wc -l  # Should be 37+
  /opt/smartbuild/venv/bin/pip list | grep streamlit
"
```

## 🚨 Common Pitfalls to Avoid

### ❌ DON'T
1. Deploy individual files manually
2. Forget to update requirements.txt
3. Deploy without testing locally first
4. Assume files are already on EC2
5. Skip post-deployment verification

### ✅ DO
1. Use deploy_to_ec2.sh for ALL deployments
2. Keep requirements.txt updated
3. Test thoroughly locally first
4. Deploy complete directories
5. Verify services after deployment

## 🔄 Rollback Procedure

If deployment fails:

```bash
# 1. Identify last working release
ls -la releases/

# 2. Restore from backup
BACKUP_DIR="releases/v5.14.3_20250907_055955"
rsync -avz "$BACKUP_DIR/" ubuntu@98.83.207.85:/opt/smartbuild/

# 3. Restart services
ssh ubuntu@98.83.207.85 "
  sudo systemctl restart smartbuild
  sudo systemctl restart smartmonitor
  sudo systemctl restart job-queue-control
"
```

## 📊 Deployment Metrics

Track these metrics for each deployment:

- **Files deployed**: Should be 40+ files total
- **Utils modules**: Should be 37+ files
- **Service restart time**: < 10 seconds each
- **Error count in logs**: Should be 0
- **CloudFront response**: All should be 200 OK

## 🔧 Automated Deployment Validation

Create this validation script:

```bash
#!/bin/bash
# verify_deployment.sh

echo "🔍 Verifying Deployment..."

# Check file counts
LOCAL_COUNT=$(ls utils/*.py | wc -l)
REMOTE_COUNT=$(ssh ubuntu@98.83.207.85 "ls /opt/smartbuild/utils/*.py | wc -l")

if [ "$LOCAL_COUNT" != "$REMOTE_COUNT" ]; then
  echo "❌ File count mismatch: Local=$LOCAL_COUNT, Remote=$REMOTE_COUNT"
  exit 1
fi

# Check services
for service in smartbuild smartmonitor job-queue-control; do
  STATUS=$(ssh ubuntu@98.83.207.85 "systemctl is-active $service")
  if [ "$STATUS" != "active" ]; then
    echo "❌ Service $service is not active"
    exit 1
  fi
done

# Check URLs
for url in "https://d10z4f7h6vaz0k.cloudfront.net/" \
           "https://d1b2mw2j81ms4x.cloudfront.net/" \
           "https://d23i1hoblpve1z.cloudfront.net/"; do
  STATUS=$(curl -s -o /dev/null -w "%{http_code}" $url)
  if [ "$STATUS" != "200" ]; then
    echo "❌ URL $url returned $STATUS"
    exit 1
  fi
done

echo "✅ Deployment verified successfully!"
```

## 📝 Lessons Learned

1. **Environment Parity**: Keep dev and prod environments as similar as possible
2. **Complete Deployments**: Always deploy entire directories, not individual files
3. **Automation**: Manual deployments are error-prone
4. **Validation**: Trust but verify - always check deployment succeeded
5. **Documentation**: Keep deployment guides updated

## 🎯 Golden Rules

1. **One Command Deployment**: `./deploy_to_ec2.sh`
2. **Always Verify**: Check services and URLs after deployment
3. **Keep Backups**: Create release folders for each stable version
4. **Document Issues**: Add new issues to this guide
5. **Test First**: Never deploy untested code

---

**Remember**: The 4 production issues we faced were ALL preventable with proper deployment practices. Use this guide to ensure they never happen again.

*For urgent help, check releases/ folder for last known good deployment*