#!/bin/bash
# Setup script for Job Queue Monitor on EC2

echo "Setting up Job Queue Monitor..."

# Create necessary directories
sudo mkdir -p /opt/smartbuild/logs
sudo mkdir -p /opt/smartbuild/utils

# Copy the job queue monitor script
sudo cp job_queue_monitor.py /opt/smartbuild/
sudo chmod +x /opt/smartbuild/job_queue_monitor.py

# Copy the job queue manager module
sudo cp utils/job_queue_manager_v2.py /opt/smartbuild/utils/

# Copy other necessary utility files
sudo cp -r utils/common_types.py /opt/smartbuild/utils/
sudo cp -r utils/__init__.py /opt/smartbuild/utils/

# Set proper permissions
sudo chown -R ubuntu:ubuntu /opt/smartbuild

# Copy and enable the systemd service
sudo cp deploy/job-queue-monitor.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable job-queue-monitor.service
sudo systemctl restart job-queue-monitor.service

# Check service status
sudo systemctl status job-queue-monitor.service

echo "Job Queue Monitor setup complete!"
echo "Check logs at: /opt/smartbuild/logs/job_queue_monitor.log"