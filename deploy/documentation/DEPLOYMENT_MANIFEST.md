# 📦 SmartBuild Deployment Manifest

**Version**: 5.11.8 (With V3/V4 Progress System)  
**Date**: 2025-01-31  
**Status**: Ready for Deployment

## 🎯 Deployment Overview

This deployment includes:
1. Claude agent prompts (`.claude/` directory)
2. Progress Probing System (V3)
3. Task ID Correlation System (V4 - optional activation)
4. Enhanced monitoring applications
5. Updated utilities and core files

## 📁 Files & Folders to Deploy

### 1️⃣ **Agent Prompts Directory** (CRITICAL - NEW)

```bash
# Source: .claude/agents/
# Target: /opt/smartbuild/.claude/agents/

Files to deploy:
├── aws-architect.md                 # Architecture diagram generation
├── aws-architect-complete-guide.md  # Detailed architecture guide
├── aws-architect-patterns.md        # Common AWS patterns
├── cloudformation-expert.md         # CloudFormation templates
├── cost-analyzer.md                 # Cost analysis (UPDATED)
├── security-auditor.md              # Security assessment
├── solution-designer.md             # Master orchestrator
├── technical-documentation.md       # Technical docs generation
└── terraform-specialist.md          # Terraform code generation

# Also copy the example diagram (reference)
├── aws-architect-example.drawio     # Example architecture diagram
```

### 2️⃣ **Core Application Files**

```bash
# Main Applications
smartbuild_spa_middleware.py         # Main application (if modified)
smartbuild_monitor.py                 # Monitor application
smartbuild_monitor_enhanced.py       # Enhanced monitor (NEW)
version_config.py                     # Version configuration
monitor_config.py                     # Monitor configuration
```

### 3️⃣ **Utilities Directory** (CRITICAL UPDATES)

```bash
# Source: utils/
# Target: /opt/smartbuild/utils/ AND /opt/smartmonitor/utils/

MUST DEPLOY TO BOTH LOCATIONS:
├── job_queue_manager.py             # Wrapper (imports V3 or V4)
├── job_queue_manager_v2.py          # Base job queue
├── job_queue_manager_v3.py          # + Progress probing (NEW)
├── job_queue_manager_v4.py          # + Task ID correlation (NEW)
├── claude_progress_prober.py        # Progress probe module (NEW)
├── prompt_enhancer.py                # Task ID enhancer (NEW)
├── progress_display_components.py   # Enhanced UI components (NEW)
├── common_types.py                  # Job type definitions
├── prompt_preparers.py               # Prompt generation
├── tab_implementations.py           # Tab logic
└── (other existing utils)
```

### 4️⃣ **Console Monitor Application**

```bash
# Console Log Monitor (if using latest version)
console_log_monitor.py               # or console_log_monitor_v3.py
# Deploy to: /opt/console_monitor/
```

### 5️⃣ **Configuration Files**

```bash
# Settings (if needed)
.claude/settings.local.json          # Claude settings
# Deploy to: /opt/smartbuild/.claude/
```

## 🚀 Deployment Script

```bash
#!/bin/bash
# deploy-v5.11.8.sh

# Configuration
EC2_IP="98.83.207.85"
PEM_FILE="deploy/smartbuild-20250824180036.pem"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

echo "🚀 SmartBuild v5.11.8 Deployment Starting..."

# Step 1: Backup existing deployment
echo "📦 Creating backup..."
ssh -i $PEM_FILE ubuntu@$EC2_IP << 'EOF'
    sudo mkdir -p /opt/backups
    sudo tar -czf /opt/backups/smartbuild_backup_$(date +%Y%m%d_%H%M%S).tar.gz \
        /opt/smartbuild/utils \
        /opt/smartbuild/.claude \
        /opt/smartmonitor/utils
EOF

# Step 2: Stop services
echo "🛑 Stopping services..."
ssh -i $PEM_FILE ubuntu@$EC2_IP "sudo systemctl stop smartbuild smartmonitor console-monitor"

# Step 3: Deploy .claude directory (NEW)
echo "📤 Deploying agent prompts..."
scp -i $PEM_FILE -r .claude ubuntu@$EC2_IP:/tmp/
ssh -i $PEM_FILE ubuntu@$EC2_IP << 'EOF'
    # Create .claude directory if it doesn't exist
    sudo mkdir -p /opt/smartbuild/.claude/agents
    
    # Copy agent files (remove Zone.Identifier files)
    sudo cp /tmp/.claude/agents/*.md /opt/smartbuild/.claude/agents/
    sudo cp /tmp/.claude/agents/*.drawio /opt/smartbuild/.claude/agents/ 2>/dev/null || true
    
    # Copy settings if exists
    [ -f /tmp/.claude/settings.local.json ] && sudo cp /tmp/.claude/settings.local.json /opt/smartbuild/.claude/
    
    # Set permissions
    sudo chown -R ubuntu:ubuntu /opt/smartbuild/.claude
    sudo chmod -R 755 /opt/smartbuild/.claude
EOF

# Step 4: Deploy utils to BOTH locations
echo "📤 Deploying utilities..."
scp -i $PEM_FILE -r utils ubuntu@$EC2_IP:/tmp/

ssh -i $PEM_FILE ubuntu@$EC2_IP << 'EOF'
    # Deploy to smartbuild
    sudo cp -r /tmp/utils/* /opt/smartbuild/utils/
    sudo chown -R ubuntu:ubuntu /opt/smartbuild/utils
    
    # Deploy to smartmonitor (CRITICAL)
    sudo cp -r /tmp/utils/* /opt/smartmonitor/utils/
    sudo chown -R ubuntu:ubuntu /opt/smartmonitor/utils
    
    echo "✅ Utils deployed to both locations"
EOF

# Step 5: Deploy main applications (if updated)
echo "📤 Deploying applications..."
scp -i $PEM_FILE smartbuild_monitor_enhanced.py ubuntu@$EC2_IP:/tmp/
scp -i $PEM_FILE version_config.py ubuntu@$EC2_IP:/tmp/

ssh -i $PEM_FILE ubuntu@$EC2_IP << 'EOF'
    # Deploy enhanced monitor
    sudo cp /tmp/smartbuild_monitor_enhanced.py /opt/smartmonitor/
    
    # Update version config in both locations
    sudo cp /tmp/version_config.py /opt/smartbuild/
    sudo cp /tmp/version_config.py /opt/smartmonitor/
    
    # Set permissions
    sudo chown ubuntu:ubuntu /opt/smartbuild/*.py
    sudo chown ubuntu:ubuntu /opt/smartmonitor/*.py
EOF

# Step 6: Restart services
echo "🔄 Restarting services..."
ssh -i $PEM_FILE ubuntu@$EC2_IP << 'EOF'
    sudo systemctl restart smartbuild
    sudo systemctl restart smartmonitor
    sudo systemctl restart console-monitor 2>/dev/null || true
    
    # Check status
    sudo systemctl status smartbuild --no-pager | head -10
    sudo systemctl status smartmonitor --no-pager | head -10
EOF

# Step 7: Verify deployment
echo "✅ Verifying deployment..."
ssh -i $PEM_FILE ubuntu@$EC2_IP << 'EOF'
    # Check for V3/V4 in logs
    sudo journalctl -u smartbuild -n 50 | grep -E "JOB QUEUE V[34]" || echo "No V3/V4 messages yet"
    
    # Check agent files
    echo "Agent files deployed:"
    ls -la /opt/smartbuild/.claude/agents/*.md | wc -l
    
    # Check utils
    echo "Utils files:"
    ls /opt/smartbuild/utils/job_queue_manager_v*.py
EOF

echo "🎉 Deployment complete!"
echo "📊 Monitor at: http://$EC2_IP:8504"
echo "🏗️ Main app at: http://$EC2_IP:80"
```

## ⚠️ Agent Prompt Updates Needed

### 1. **All Agents** - Add Task ID Support

Each agent prompt needs this addition at the end:

```markdown
## Task Completion Marker

When you have completed all tasks, you MUST end your response with:

TASK COMPLETED

This marker is required for the system to detect task completion.
```

### 2. **Cost Analyzer** - Already Updated
The cost-analyzer.md has been updated for dual cost calculation.

### 3. **Solution Designer** - Coordination Update

Add to solution-designer.md:

```markdown
## Progress Reporting

Throughout your task, report progress at key milestones:
- "Starting requirements analysis..." 
- "Designing architecture..."
- "Creating infrastructure code..."
- "Finalizing documentation..."

This helps track task progress in real-time.
```

## 📋 Pre-Deployment Checklist

- [ ] Backup current deployment
- [ ] Test V3 locally (Progress Probing)
- [ ] Decide on V4 activation (Task ID)
- [ ] Review agent prompts
- [ ] Prepare rollback script
- [ ] Schedule maintenance window
- [ ] Notify team

## 🔄 Rollback Procedure

```bash
#!/bin/bash
# rollback.sh

EC2_IP="98.83.207.85"
PEM_FILE="deploy/smartbuild-20250824180036.pem"

echo "🔄 Rolling back deployment..."

ssh -i $PEM_FILE ubuntu@$EC2_IP << 'EOF'
    # Stop services
    sudo systemctl stop smartbuild smartmonitor
    
    # Restore from backup
    LATEST_BACKUP=$(ls -t /opt/backups/smartbuild_backup_*.tar.gz | head -1)
    
    if [ -f "$LATEST_BACKUP" ]; then
        echo "Restoring from: $LATEST_BACKUP"
        cd /
        sudo tar -xzf "$LATEST_BACKUP"
        
        # Restart services
        sudo systemctl restart smartbuild smartmonitor
        
        echo "✅ Rollback complete"
    else
        echo "❌ No backup found!"
    fi
EOF
```

## 🎯 V3 vs V4 Decision

### Deploy V3 Only (Recommended First)
- Progress probing active
- No Task ID correlation
- Lower risk, immediate benefits

### Deploy V3 + Activate V4 (Later)
- Both features active
- Requires prompt updates
- Maximum tracking capability

To activate V4 after deployment:
```bash
ssh -i $PEM_FILE ubuntu@$EC2_IP
sudo nano /opt/smartbuild/utils/job_queue_manager.py
# Change: job_queue_manager_v3 → job_queue_manager_v4
sudo systemctl restart smartbuild smartmonitor
```

## 📊 Post-Deployment Validation

```bash
# Check V3 is active
curl -s http://98.83.207.85:8504 | grep "Progress"

# Check agent files
ssh -i $PEM_FILE ubuntu@$EC2_IP "ls /opt/smartbuild/.claude/agents/"

# Monitor logs
ssh -i $PEM_FILE ubuntu@$EC2_IP "sudo journalctl -u smartbuild -f | grep PROBE"
```

## 📈 Monitoring After Deployment

Watch for:
1. "JOB QUEUE V3" messages in logs
2. Progress updates in monitor UI
3. Agent prompt loading messages
4. No error spikes in logs

## 🔐 Security Notes

- All agent files are read-only
- No credentials in agent prompts
- Task IDs are non-sensitive
- Progress data is ephemeral

---

**Ready to deploy?** Run the deployment script above! 🚀