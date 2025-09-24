#!/bin/bash
# Fix streamlit path in monitor services

EC2_IP="98.83.207.85"
KEY_PATH="smartbuild-20250824180036.pem"

echo "Fixing streamlit path in systemd services..."

ssh -i "$KEY_PATH" ubuntu@"$EC2_IP" << 'EOF'
    # First, check if venv exists in monitor directories, if not create it
    echo "Setting up Python virtual environments..."
    
    # For console log monitor
    if [ ! -d "/opt/console_log_monitor/venv" ]; then
        cd /opt/console_log_monitor
        python3 -m venv venv
        ./venv/bin/pip install streamlit pandas
    fi
    
    # For job queue control
    if [ ! -d "/opt/job_queue_control/venv" ]; then
        cd /opt/job_queue_control
        python3 -m venv venv
        ./venv/bin/pip install streamlit pandas psutil
    fi
    
    # Update service files with correct streamlit path
    echo "Updating service files..."
    
    # Update console-log-monitor service
    sudo sed -i 's|/usr/local/bin/streamlit|/opt/console_log_monitor/venv/bin/streamlit|g' /etc/systemd/system/console-log-monitor.service
    
    # Update job-queue-control service  
    sudo sed -i 's|/usr/local/bin/streamlit|/opt/job_queue_control/venv/bin/streamlit|g' /etc/systemd/system/job-queue-control.service
    
    # Alternative: Use the main app's venv (simpler approach)
    echo "Using main app's venv for monitors..."
    sudo sed -i 's|/opt/console_log_monitor/venv/bin/streamlit|/opt/smartbuild/venv/bin/streamlit|g' /etc/systemd/system/console-log-monitor.service
    sudo sed -i 's|/opt/job_queue_control/venv/bin/streamlit|/opt/smartbuild/venv/bin/streamlit|g' /etc/systemd/system/job-queue-control.service
    
    # Reload systemd and restart services
    echo "Restarting services..."
    sudo systemctl daemon-reload
    sudo systemctl restart console-log-monitor
    sudo systemctl restart job-queue-control
    
    sleep 3
    
    # Check status
    echo -e "\n=== Service Status ==="
    echo "Console Log Monitor:"
    sudo systemctl is-active console-log-monitor
    
    echo "Job Queue Control:"
    sudo systemctl is-active job-queue-control
    
    echo -e "\n=== Port Check ==="
    ss -tlnp | grep -E ':(8506|8507)' 2>/dev/null || echo "Ports not yet listening"
    
    echo -e "\n=== Recent Logs ==="
    echo "Console Log Monitor:"
    sudo journalctl -u console-log-monitor --no-pager -n 3
    echo ""
    echo "Job Queue Control:"
    sudo journalctl -u job-queue-control --no-pager -n 3
EOF

echo -e "\n✅ Service fix complete!"