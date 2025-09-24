# EC2 Deployment Guide for SmartBuild SPA

## CRITICAL: Always Deploy to BOTH Sites

**As of 2025-08-30, deployments MUST go to both locations:**
- `/opt/smartbuild/` - Main application
- `/opt/smartmonitor/` - Monitor application

Both sites must have identical utils code to ensure consistency.

## Quick Deploy Script

The recommended way to deploy is using the dual-site deployment script:

```bash
cd deploy
./deploy-to-both-sites.sh
```

## Manual Deployment Steps

If you need to deploy manually, follow these steps:

### 1. Set Environment Variables

```bash
EC2_IP="98.83.207.85"
KEY_PATH="./smartbuild-20250824180036.pem"
```

### 2. Files That MUST Go to BOTH Sites

These files must be deployed to both `/opt/smartbuild/utils/` AND `/opt/smartmonitor/utils/`:

```bash
# Core shared utilities
utils/common_types.py           # Job type definitions
utils/job_queue_manager_v2.py   # ONLY component that talks to Claude
utils/prompt_preparers.py       # Prompt preparation functions
utils/claude_session_manager.py # Session management
```

### 3. Files for Main App Only

These files go only to `/opt/smartbuild/`:

```bash
smartbuild_spa_middleware.py    # Main application logic
.md/*.md                        # Documentation files
```

### 4. Deployment Commands

```bash
# Deploy to SmartBuild (main app)
scp -i $KEY_PATH utils/common_types.py ubuntu@$EC2_IP:/opt/smartbuild/utils/
scp -i $KEY_PATH utils/job_queue_manager_v2.py ubuntu@$EC2_IP:/opt/smartbuild/utils/
scp -i $KEY_PATH utils/prompt_preparers.py ubuntu@$EC2_IP:/opt/smartbuild/utils/
scp -i $KEY_PATH utils/claude_session_manager.py ubuntu@$EC2_IP:/opt/smartbuild/utils/
scp -i $KEY_PATH smartbuild_spa_middleware.py ubuntu@$EC2_IP:/opt/smartbuild/

# Deploy to SmartMonitor
scp -i $KEY_PATH utils/common_types.py ubuntu@$EC2_IP:/opt/smartmonitor/utils/
scp -i $KEY_PATH utils/job_queue_manager_v2.py ubuntu@$EC2_IP:/opt/smartmonitor/utils/
scp -i $KEY_PATH utils/prompt_preparers.py ubuntu@$EC2_IP:/opt/smartmonitor/utils/
scp -i $KEY_PATH utils/claude_session_manager.py ubuntu@$EC2_IP:/opt/smartmonitor/utils/
```

### 5. Restart Services

```bash
ssh -i $KEY_PATH ubuntu@$EC2_IP << 'EOF'
    sudo systemctl restart smartbuild
    sudo systemctl restart smartmonitor
EOF
```

## Architecture Notes

### Critical Design Decision (2025-08-30)

**ONLY `job_queue_manager_v2.py` interacts with Claude/tmux**

This centralized architecture ensures:
- No duplicate tmux sessions
- Consistent prompt handling with `-l` flag
- Single point of control for debugging
- Better error handling

All other components queue jobs via the job queue manager.

### Job Types

The system supports these job types (defined in `common_types.py`):

1. `REQUIREMENTS` - Extract project requirements
2. `SOLUTION` - Generate initial solution
3. `ARCHITECTURE` - Create architecture diagrams
4. `COST_ANALYSIS` - Analyze costs
5. `TECH_DOC` - Generate documentation
6. `TERRAFORM` - Generate Terraform code
7. `CLOUDFORMATION` - Generate CloudFormation

## Troubleshooting

### Common Issues

1. **Import Errors After Deployment**
   - Ensure files were deployed to BOTH sites
   - Check file permissions: `ls -la /opt/smartbuild/utils/`
   - Verify Python can import: `python3 -c "from utils.common_types import JobType"`

2. **Monitor Not Showing Jobs**
   - Monitor must have `job_queue_manager_v2.py`
   - Monitor must have `common_types.py`
   - Restart monitor: `sudo systemctl restart smartmonitor`

3. **Syntax Errors**
   - Always test locally first: `python3 -m py_compile filename.py`
   - Check for missing newlines between functions
   - Verify proper indentation

### Verification Commands

```bash
# Check both sites have the files
ssh -i $KEY_PATH ubuntu@$EC2_IP << 'EOF'
    echo "SmartBuild utils:"
    ls -la /opt/smartbuild/utils/ | grep -E "common_types|job_queue_manager_v2"
    
    echo "SmartMonitor utils:"
    ls -la /opt/smartmonitor/utils/ | grep -E "common_types|job_queue_manager_v2"
EOF
```

## Service URLs

- **Main App**: https://d10z4f7h6vaz0k.cloudfront.net/
- **Monitor**: https://d10z4f7h6vaz0k.cloudfront.net/monitor/

## Best Practices

1. **Always Deploy to Both Sites**
   - Use `deploy-to-both-sites.sh` script
   - Never deploy to just one location

2. **Test Before Deploying**
   - Run syntax checks locally
   - Test imports work
   - Verify no blocking operations

3. **Clean Up tmux Sessions**
   - Kill orphaned sessions before deploying
   - Use pattern: `tmux ls | grep '^sb_' | cut -d: -f1 | xargs -I {} tmux kill-session -t {}`

4. **Monitor After Deployment**
   - Check service status
   - Watch logs for errors
   - Test functionality immediately

## Deployment Scripts

### Available Scripts

- `deploy-to-both-sites.sh` - **RECOMMENDED** - Deploys to both sites
- `deploy-centralized-claude.sh` - Deploys centralized Claude management
- `deploy-literal-flag-fix.sh` - Deploys tmux literal flag fix
- `deploy-handshake-fix.sh` - Deploys handshake protocol fix

### Creating New Deployment Scripts

Always include deployment to BOTH sites:

```bash
#!/bin/bash
# Template for new deployment scripts

FILES_TO_DEPLOY=(
    "utils/common_types.py"
    "utils/job_queue_manager_v2.py"
    "utils/prompt_preparers.py"
    "utils/claude_session_manager.py"
)

# Deploy to both locations
for file in "${FILES_TO_DEPLOY[@]}"; do
    scp -i "$KEY_PATH" "../$file" ubuntu@"$EC2_IP":/opt/smartbuild/$file
    filename=$(basename "$file")
    scp -i "$KEY_PATH" "../$file" ubuntu@"$EC2_IP":/opt/smartmonitor/utils/$filename
done
```

---

**Remember**: The monitor and main app share utils code. Any changes to utils MUST be deployed to both locations!