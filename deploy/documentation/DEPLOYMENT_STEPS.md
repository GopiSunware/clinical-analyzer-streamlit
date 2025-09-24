# 🚀 SmartBuild Complete Deployment Steps

## Current Status & Issues
1. **Main App**: Missing new tabs (Cost Analysis, etc.)
2. **Monitor App**: /monitor path not working with CloudFront
3. **Solution**: Deploy apps separately with independent CloudFront distributions

## 📋 Deployment Plan

### Step 1: Redeploy Main SmartBuild App (Fix Missing Tabs)
```bash
cd deploy
./redeploy-smartbuild-latest.sh 98.83.207.85
```

This will:
- Deploy latest code with all 5 tabs
- Update utils/tab_implementations.py
- Ensure Cost Analysis tab is included
- Keep using existing CloudFront: https://d10z4f7h6vaz0k.cloudfront.net/

### Step 2: Deploy Monitor to Separate Folder
```bash
cd deploy
./setup-smartmonitor-separate.sh 98.83.207.85
```

This will:
- Create `/opt/smartmonitor` folder
- Set up separate Python environment
- Run on port 8504, proxied through Nginx port 8080
- Configure to read sessions from `/opt/smartbuild/sessions`

### Step 3: Update EC2 Security Group
Add inbound rule for port 8080:
```bash
# Get security group ID
aws ec2 describe-instances --instance-ids i-00d6684521b9d4c5d \
  --query 'Reservations[0].Instances[0].SecurityGroups[0].GroupId' \
  --output text --region us-east-1

# Add port 8080 rule (replace sg-XXXXX with your security group ID)
aws ec2 authorize-security-group-ingress \
  --group-id sg-XXXXX \
  --protocol tcp \
  --port 8080 \
  --cidr 0.0.0.0/0 \
  --region us-east-1
```

### Step 4: Create CloudFront for Monitor
```bash
cd deploy
./create-monitor-cloudfront.sh 98.83.207.85
```

This will:
- Create new CloudFront distribution
- Point to EC2:8080
- Return new CloudFront URL for monitor

### Step 5: Verify Everything Works

#### Check Main App:
1. Visit: https://d10z4f7h6vaz0k.cloudfront.net/
2. Create/select a session
3. Verify you see all 5 tabs:
   - Requirements
   - Cost Analysis
   - Technical Documentation  
   - Terraform
   - CloudFormation

#### Check Monitor App:
1. Visit new CloudFront URL (provided by script)
2. Verify monitor dashboard loads
3. Check it can see sessions from main app

## 🔧 Quick Commands Reference

### Service Status
```bash
# Main app
ssh -i smartbuild-20250824180036.pem ubuntu@98.83.207.85 \
  'sudo systemctl status smartbuild'

# Monitor app
ssh -i smartbuild-20250824180036.pem ubuntu@98.83.207.85 \
  'sudo systemctl status smartmonitor'
```

### View Logs
```bash
# Main app logs
ssh -i smartbuild-20250824180036.pem ubuntu@98.83.207.85 \
  'sudo journalctl -u smartbuild -f'

# Monitor logs
ssh -i smartbuild-20250824180036.pem ubuntu@98.83.207.85 \
  'sudo journalctl -u smartmonitor -f'
```

### Restart Services
```bash
# Main app
ssh -i smartbuild-20250824180036.pem ubuntu@98.83.207.85 \
  'sudo systemctl restart smartbuild'

# Monitor
ssh -i smartbuild-20250824180036.pem ubuntu@98.83.207.85 \
  'sudo systemctl restart smartmonitor'
```

## 📁 Final EC2 Structure

```
/opt/
├── smartbuild/              # Main application
│   ├── smartbuild_spa_middleware.py
│   ├── utils/               # Including tab_implementations.py
│   ├── sessions/            # Session data
│   └── venv/               # Python environment
│
└── smartmonitor/            # Monitor application
    ├── smartbuild_monitor.py
    ├── utils/               # Copy of utils
    └── venv/               # Separate Python environment
```

## 🌐 Final URLs

- **Main App**: https://d10z4f7h6vaz0k.cloudfront.net/
- **Monitor**: https://[new-cloudfront-id].cloudfront.net/

## ⚠️ Important Notes

1. **Session Path**: Monitor reads from `/opt/smartbuild/sessions` via environment variable
2. **Ports**: 
   - Main app: 8505 (internal)
   - Monitor: 8504 (internal), 8080 (Nginx proxy)
3. **Security Group**: Must allow port 8080 for monitor CloudFront
4. **CloudFront**: Two separate distributions, cleaner and simpler

## 🎯 Expected Results

After deployment:
1. ✅ Main app shows all 5 tabs including Cost Analysis
2. ✅ Monitor has its own CloudFront URL
3. ✅ Both apps run independently
4. ✅ Monitor can read main app sessions
5. ✅ No URL path conflicts

---

**Deployment Date**: 2025-08-29
**EC2 Instance**: 98.83.207.85 (t3.large)


 Deployment Setup Complete!

  I've created a clean separation approach with two folders and two CloudFront distributions. Here's what's ready:

  📂 Created Scripts:

  1. redeploy-smartbuild-latest.sh - Redeploys main app with all new tabs
  2. setup-smartmonitor-separate.sh - Sets up monitor in /opt/smartmonitor
  3. create-monitor-cloudfront.sh - Creates separate CloudFront for monitor
  4. DEPLOYMENT_STEPS.md - Complete step-by-step guide

  🚀 Quick Deployment Commands:

  # 1. Fix missing tabs in main app
  cd deploy
  ./redeploy-smartbuild-latest.sh 98.83.207.85

  # 2. Deploy monitor to separate folder
  ./setup-smartmonitor-separate.sh 98.83.207.85

  # 3. Open port 8080 in security group (needed for monitor)
  # Check AWS console or use AWS CLI

  # 4. Create CloudFront for monitor
  ./create-monitor-cloudfront.sh 98.83.207.85

  🎯 This Approach Solves:

  1. Missing tabs issue - Redeploys with latest code including Cost Analysis tab
  2. Monitor routing issue - Separate CloudFront, no path conflicts
  3. Clean separation - Each app has its own folder and environment
  4. Shared sessions - Monitor can still read main app sessions

  📋 After Deployment:

  - Main App: https://d10z4f7h6vaz0k.cloudfront.net/ (existing URL)
  
 3. Test monitor at https://d1b2mw2j81ms4x.cloudfront.net/
  Both apps will run independently with their own CloudFront distributions. Much simpler and cleaner than trying to route through subpaths!
