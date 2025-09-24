# SmartBuild SPA - AWS Deployment Details

## 🌐 Live Application URLs

### Primary Access (CloudFront HTTPS):
- **URL**: https://d10z4f7h6vaz0k.cloudfront.net
- **Type**: CloudFront Distribution with automatic HTTPS
- **Status**: ✅ ACTIVE

### Direct EC2 Access (HTTP):
- **URL**: http://98.83.207.85
- **Type**: Direct EC2 access (not recommended for production)

## 🖥️ EC2 Instance Details

### Instance Information:
- **Instance ID**: `i-00d6684521b9d4c5d`
- **Public IP**: `98.83.207.85`
- **Public DNS**: `ec2-98.83.207.85.compute-1.amazonaws.com`
- **Instance Type**: `t3.large` (2 vCPU, 4GB RAM)
- **Region**: `us-east-1`
- **OS**: Ubuntu 22.04 LTS

## 🔑 SSH Access

### How to Login to EC2:

```bash
# From the deploy directory where the key is located
cd /home/development/python/aws/sunware-tech/devgenious/claude-code-chat/deploy

# SSH into the instance
ssh -i smartbuild-20250824180036.pem ubuntu@98.83.207.85
```

### Login Credentials:
- **Username**: `ubuntu` (default for Ubuntu AMI)
- **Password**: Not required (uses SSH key authentication)
- **SSH Key**: `smartbuild-20250824180036.pem` (located in deploy folder)
- **Key Permissions**: Must be 400 (`chmod 400 smartbuild-20250824180036.pem`)

## 📂 Application Location on EC2

Once logged in via SSH:

```bash
# Application directory
cd /opt/smartbuild

# View application files
ls -la

# Python virtual environment
source venv/bin/activate

# View running service
sudo systemctl status smartbuild
```

## 🛠️ Common Management Commands

### From Your Local Machine:

```bash
# Check service status
ssh -i smartbuild-20250824180036.pem ubuntu@98.83.207.85 "sudo systemctl status smartbuild"

# View application logs
ssh -i smartbuild-20250824180036.pem ubuntu@98.83.207.85 "sudo journalctl -u smartbuild -f"

# Restart application
ssh -i smartbuild-20250824180036.pem ubuntu@98.83.207.85 "sudo systemctl restart smartbuild"

# View Nginx status
ssh -i smartbuild-20250824180036.pem ubuntu@98.83.207.85 "sudo systemctl status nginx"
```

### After SSH Login to EC2:

```bash
# Navigate to app directory
cd /opt/smartbuild

# Check Python packages
source venv/bin/activate
pip list | grep streamlit

# Edit configuration
nano /etc/systemd/system/smartbuild.service

# View real-time logs
sudo journalctl -u smartbuild -f

# Check tmux sessions
tmux ls

# Attach to a tmux session
tmux attach -t session_name
```

## 📦 Re-deployment / Upload Changes

### To upload code changes:

```bash
# From deploy directory
cd /home/development/python/aws/sunware-tech/devgenious/claude-code-chat/deploy

# Upload single file
scp -i smartbuild-20250824180036.pem ../smartbuild_spa_middleware.py ubuntu@98.83.207.85:/opt/smartbuild/

# Upload all files (complete re-upload)
./complete-upload.sh 98.83.207.85 smartbuild-20250824180036

# Restart after upload
ssh -i smartbuild-20250824180036.pem ubuntu@98.83.207.85 "sudo systemctl restart smartbuild"
```

## 🏗️ AWS Infrastructure

### CloudFormation Stack:
- **Stack Name**: `smartbuild-minimal`
- **Region**: `us-east-1`
- **Resources Created**:
  - EC2 Instance (t3.large)
  - Security Group
  - CloudFront Distribution
  - No ALB, No S3 (minimal setup)

### Check Stack Status:
```bash
aws cloudformation describe-stacks --stack-name smartbuild-minimal --region us-east-1
```

### Delete Everything:
```bash
# This will remove all AWS resources
aws cloudformation delete-stack --stack-name smartbuild-minimal --region us-east-1

# Wait for deletion
aws cloudformation wait stack-delete-complete --stack-name smartbuild-minimal --region us-east-1
```

## 💰 Monthly Costs

- **EC2 t3.large**: ~$30/month
- **CloudFront**: ~$2-5/month (based on usage)
- **Total**: ~$35/month

## 🔧 Troubleshooting

### Cannot SSH:
1. Check you're in the correct directory with the .pem file
2. Verify key permissions: `chmod 400 smartbuild-20250824180036.pem`
3. Check security group allows SSH (port 22) from your IP

### Application Not Loading:
1. Check service status: `sudo systemctl status smartbuild`
2. Check Nginx: `sudo systemctl status nginx`
3. View logs: `sudo journalctl -u smartbuild -n 50`

### CloudFront Not Updating:
Clear CloudFront cache:
```bash
aws cloudfront create-invalidation \
  --distribution-id EY2D88MPRKCMZ \
  --paths "/*" \
  --region us-east-1
```

## 📝 Important Files on EC2

```
/opt/smartbuild/
├── smartbuild_spa_middleware.py   # Main application
├── sessions/                       # User sessions
├── utils/                          # Utility modules
├── venv/                          # Python virtual environment
└── requirements.txt               # Python dependencies

/etc/systemd/system/smartbuild.service  # Service configuration
/etc/nginx/sites-available/default      # Nginx configuration
```

## 🔄 Current Versions

- **Python**: 3.11.0rc1 (on EC2)
- **Streamlit**: 1.39.0 (downgraded to match local)
- **Application**: Version 5.10.2

---

*Last Updated: 2025-08-24 23:15 UTC*
*Deployment Date: 2025-08-24 22:00 UTC*