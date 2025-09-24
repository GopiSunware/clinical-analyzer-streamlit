# Streamlit Server Console Access Guide

## Quick Access Commands

### 1. Connect to EC2
```bash
cd /home/development/python/aws/sunware-tech/devgenious/claude-code-chat/deploy
ssh -i smartbuild-20250824180036.pem ubuntu@98.83.207.85
```

### 2. Access Streamlit Console (Choose One)

#### A. Live Application Logs (Recommended)
```bash
# View real-time Streamlit logs
sudo journalctl -u smartbuild -f

# Press Ctrl+C to exit
```

#### B. Interactive Debug Mode
```bash
# Stop the service first
sudo systemctl stop smartbuild

# Run Streamlit manually to see console output directly
cd /opt/smartbuild
source venv/bin/activate
streamlit run smartbuild_spa_middleware.py --server.port 8501 --server.address 127.0.0.1

# Press Ctrl+C to stop
# Then restart service:
sudo systemctl start smartbuild
```

#### C. Check Service Status
```bash
# Quick status check
sudo systemctl status smartbuild

# View last 50 lines of logs
sudo journalctl -u smartbuild -n 50

# View errors only
sudo journalctl -u smartbuild --since "10 minutes ago" | grep -i error
```

## Common Streamlit Console Commands

### Monitor Session Activity
```bash
# Watch live logs with filtering
sudo journalctl -u smartbuild -f | grep -E "(Session|Run|ERROR)"

# Monitor specific session
sudo journalctl -u smartbuild -f | grep "session_20250824"
```

### Debug Issues
```bash
# Check for import errors
sudo journalctl -u smartbuild --since "5 minutes ago" | grep -i "ModuleNotFoundError"

# Check for Streamlit errors
sudo journalctl -u smartbuild --since "5 minutes ago" | grep -i "StreamlitAPIException"

# View startup issues
sudo journalctl -u smartbuild --since "system boot" | head -100
```

### Service Management
```bash
# Restart Streamlit
sudo systemctl restart smartbuild

# Stop Streamlit
sudo systemctl stop smartbuild

# Start Streamlit
sudo systemctl start smartbuild

# Enable auto-start on boot
sudo systemctl enable smartbuild
```

## Access URLs

- **CloudFront URL**: https://d10z4f7h6vaz0k.cloudfront.net
- **Direct EC2**: http://98.83.207.85:8501 (if security group allows)
- **Local test**: http://localhost:8501 (when SSH tunneling)

## SSH Tunnel for Local Access
If you want to access Streamlit console from your local browser:
```bash
# Create SSH tunnel (run from local machine)
ssh -i smartbuild-20250824180036.pem -L 8501:localhost:8501 ubuntu@98.83.207.85

# Then open browser to: http://localhost:8501
```

## Files Deployed
All files have been successfully deployed to `/opt/smartbuild/`:
- ✅ Core Python files (smartbuild_spa_middleware.py, etc.)
- ✅ utils/ directory (including supervisor_state.py)
- ✅ assets/ directory
- ✅ .claude/ folder
- ✅ CLAUDE.md
- ✅ docs/ folder
- ✅ .tmux.conf
- ✅ sessions/ folder

## Quick Troubleshooting

### If ModuleNotFoundError occurs:
```bash
# Verify file exists
ls -la /opt/smartbuild/utils/supervisor_state.py

# Check Python path
cd /opt/smartbuild
source venv/bin/activate
python -c "import sys; print(sys.path)"

# Reinstall dependencies
pip install -r requirements.txt
```

### If service won't start:
```bash
# Check for syntax errors
cd /opt/smartbuild
source venv/bin/activate
python -m py_compile smartbuild_spa_middleware.py

# Check permissions
ls -la /opt/smartbuild/
chown -R ubuntu:ubuntu /opt/smartbuild
```

### Clean up old sessions:
```bash
# List tmux sessions
tmux ls

# Kill old sessions
tmux kill-server

# Remove old session files
rm -rf /opt/smartbuild/sessions/session_*/
```

## Exit Instructions
```bash
# Exit from SSH session
exit
# or Ctrl+D
```