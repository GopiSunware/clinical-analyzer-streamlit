# EC2 Instance Sizing for SmartBuild SPA

## For Maximum 4 Concurrent Users

### Recommended Instance: **t3.large**
- **vCPUs**: 2
- **Memory**: 4 GB RAM  
- **Network**: Up to 5 Gbps
- **Storage**: 30 GB gp3 EBS
- **Cost**: ~$30/month (on-demand)

### Resource Breakdown (4 concurrent users):
```
Base System:           1.0 GB RAM
Streamlit App:         0.5 GB RAM
Python Environment:    0.5 GB RAM
Per User Session:      0.5 GB RAM × 4 = 2.0 GB RAM
----------------------------------------
Total Required:        4.0 GB RAM
```

### CPU Usage:
- Each user session uses ~25-50% of 1 vCPU during active processing
- 2 vCPUs can handle 4 users with reasonable performance

## Alternative Options:

### 1. **t3a.medium** (AMD processors)
- Same specs as t3.large
- **Cost**: ~$27/month (10% cheaper)
- Good for cost optimization

### 2. **t3.small** (Bare minimum)
- **vCPUs**: 2
- **Memory**: 2 GB RAM
- **Cost**: ~$15/month
- ⚠️ **Warning**: May experience slowdowns with 4 concurrent users
- Only recommended for 1-2 concurrent users

### 3. **t3.large** (Better performance)
- **vCPUs**: 2
- **Memory**: 8 GB RAM
- **Cost**: ~$60/month
- Recommended if users run complex/long operations
- Can handle 6-8 concurrent users comfortably

## Instance Comparison Table:

| Instance Type | vCPUs | RAM  | Max Users | Monthly Cost | Use Case |
|--------------|-------|------|-----------|--------------|----------|
| t3.small     | 2     | 2 GB | 1-2       | ~$15        | Testing  |
| t3.large    | 2     | 4 GB | 3-4       | ~$30        | **Recommended** |
| t3.large     | 2     | 8 GB | 6-8       | ~$60        | Growth room |
| m5.large     | 2     | 8 GB | 6-8       | ~$70        | Production |

## Cost Optimization Tips:

1. **Use Spot Instances** (70% savings)
   ```bash
   aws ec2 run-instances --instance-type t3.large --spot-price 0.01
   ```

2. **Reserved Instances** (up to 40% savings)
   - 1-year term: ~$18/month
   - 3-year term: ~$12/month

3. **Auto-shutdown during off-hours**
   ```bash
   # Add to crontab
   0 19 * * * sudo shutdown -h now  # Shutdown at 7 PM
   ```

4. **Use AWS Savings Plans**
   - Commit to $20/month spend
   - Get ~25% discount

## Monitoring Commands:

```bash
# Check memory usage
free -h

# Monitor CPU usage
top -u ubuntu

# Count active tmux sessions (users)
tmux ls | wc -l

# Check Streamlit connections
netstat -an | grep :8501 | grep ESTABLISHED | wc -l
```

## Auto-scaling Script (optional):

```bash
#!/bin/bash
# Check if memory usage > 80%, alert to upgrade
MEMORY_USAGE=$(free | grep Mem | awk '{print int($3/$2 * 100)}')
if [ $MEMORY_USAGE -gt 80 ]; then
    echo "Warning: Memory usage is ${MEMORY_USAGE}%"
    echo "Consider upgrading to t3.large"
fi
```

## Launch EC2 Instance Command:

```bash
# Launch t3.large with Ubuntu 22.04 LTS
aws ec2 run-instances \
  --image-id ami-0c02fb55731490381 \
  --instance-type t3.large \
  --key-name your-key-pair \
  --security-group-ids sg-xxxxxx \
  --subnet-id subnet-xxxxxx \
  --block-device-mappings "DeviceName=/dev/sda1,Ebs={VolumeSize=30,VolumeType=gp3}" \
  --tag-specifications 'ResourceType=instance,Tags=[{Key=Name,Value=SmartBuild-SPA}]' \
  --user-data file://ec2-setup.sh
```

## Summary for 4 Users:
✅ **Go with t3.large** - Perfect balance of performance and cost at ~$30/month