# EC2 Server Console Access Guide

## 1. First, SSH into EC2

```bash
cd /home/development/python/aws/sunware-tech/devgenious/claude-code-chat/deploy
ssh -i smartbuild-20250824180036.pem ubuntu@98.83.207.85
```

## 2. Access Different Consoles

### A. Streamlit Application Logs (Real-time)

```bash
# View live application logs
sudo journalctl -u smartbuild -f

# View last 100 lines
sudo journalctl -u smartbuild -n 100

# View logs with timestamps
sudo journalctl -u smartbuild --since "1 hour ago"
```

### B. Python Console (Interactive)

```bash
# Navigate to app directory
cd /opt/smartbuild

# Activate Python virtual environment
source venv/bin/activate

# Start Python console with app context
python

# In Python console, you can:
>>> import streamlit as st
>>> from smartbuild_spa_middleware import *
>>> from session_manager import SessionManager
>>> sm = SessionManager()
>>> sm.list_sessions()  # List all sessions
```

### C. Tmux Sessions (Active Claude/SmartBuild Sessions)

```bash
# List all tmux sessions
tmux ls

# You'll see sessions like:
# smartbuild_s_20250824_105332: 1 windows
# supervisor_session_20250824_105332: 1 windows

# Attach to a working session
tmux attach -t smartbuild_s_20250824_105332

# Attach to supervisor session
tmux attach -t supervisor_session_20250824_105332

# To detach from tmux: Press Ctrl+B, then D
# To scroll in tmux: Press Ctrl+B, then [ (then use arrow keys/Page Up/Down)
# To exit scroll mode: Press Q
```

### D. Application Console (Direct Streamlit)

```bash
# Stop the service first
sudo systemctl stop smartbuild

# Run Streamlit manually (for debugging)
cd /opt/smartbuild
source venv/bin/activate
streamlit run smartbuild_spa_middleware.py --server.port 8501 --server.address 0.0.0.0

# You'll see console output directly
# Press Ctrl+C to stop
```

### E. System Console Commands

```bash
# Check service status
sudo systemctl status smartbuild

# Restart service
sudo systemctl restart smartbuild

# Stop service
sudo systemctl stop smartbuild

# Start service
sudo systemctl start smartbuild

# Check all running Python processes
ps aux | grep python

# Check memory usage
free -h

# Check disk usage
df -h

# Monitor system resources
htop  # or top
```

### F. Database/Session Management

```bash
cd /opt/smartbuild

# List all sessions
ls -la sessions/

# View session details
cat sessions/session_*/requirements.json | jq '.'

# Check run status
ls -la sessions/*/runs/

# View logs
tail -f sessions/*/logs/*.log
```

### G. Nginx Web Server Console

```bash
# Check Nginx status
sudo systemctl status nginx

# View Nginx access logs
sudo tail -f /var/log/nginx/access.log

# View Nginx error logs
sudo tail -f /var/log/nginx/error.log

# Test Nginx configuration
sudo nginx -t

# Reload Nginx
sudo systemctl reload nginx
```

## 3. Common Debugging Commands

### Check if Streamlit is Running
```bash
# Check process
ps aux | grep streamlit

# Check port
sudo netstat -tlnp | grep 8501

# Test locally
curl http://localhost:8501
```

### View Application Errors
```bash
# Check Python errors
sudo journalctl -u smartbuild --since "10 minutes ago" | grep -i error

# Check tmux sessions for errors
tmux capture-pane -t smartbuild_s_[session_id] -p | tail -50
```

### Monitor Real-time Activity
```bash
# Watch all logs simultaneously
sudo journalctl -u smartbuild -u nginx -f

# Monitor file changes
watch -n 1 'ls -la sessions/*/runs/ | tail -10'
```

## 4. Interactive Session Management

### Start New Claude Session Manually
```bash
# Create new tmux session
tmux new-session -d -s test_claude -x 200 -y 50

# Send claude command
tmux send-keys -t test_claude 'claude --model claude-opus-4-1-20250805' Enter

# Attach to see it
tmux attach -t test_claude
```

### Clean Up Old Sessions
```bash
# Kill specific tmux session
tmux kill-session -t session_name

# Kill all tmux sessions
tmux kill-server

# Clean old session files
find /opt/smartbuild/sessions -type d -mtime +7 -exec rm -rf {} \;
```

## 5. Quick Connect Script

Create this helper script on EC2:
```bash
# Create connect.sh on EC2
cat > ~/connect.sh << 'EOF'
#!/bin/bash
echo "SmartBuild Console Options:"
echo "1. Application logs (live)"
echo "2. Python console"
echo "3. List tmux sessions"
echo "4. System status"
echo "5. Session management"
read -p "Choose [1-5]: " choice

case $choice in
    1) sudo journalctl -u smartbuild -f ;;
    2) cd /opt/smartbuild && source venv/bin/activate && python ;;
    3) tmux ls ;;
    4) sudo systemctl status smartbuild ;;
    5) ls -la /opt/smartbuild/sessions/ ;;
    *) echo "Invalid choice" ;;
esac
EOF

chmod +x ~/connect.sh

# Run it
./connect.sh
```

## 6. Exit and Disconnect

```bash
# Exit from any console
exit

# Or Ctrl+D

# Detach from tmux without killing it
Ctrl+B, then D

# Logout from EC2
exit
```

## Tips:

1. **Always use tmux** for long-running operations
2. **Monitor logs** with `journalctl -f` for real-time debugging
3. **Check service status** before making changes
4. **Use virtual environment** when running Python commands
5. **Detach properly** from tmux sessions (don't just close terminal)

---
*Remember: The application runs as a systemd service, so you usually don't need console access unless debugging.*