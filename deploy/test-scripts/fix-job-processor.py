#!/usr/bin/env python3
"""
Fix job processor to properly handle job execution
Patches the job queue manager to use simpler execution that works
"""

import json
import subprocess
import time
from pathlib import Path
from datetime import datetime

def fix_job_processor():
    """Fix the job processor on EC2"""
    
    # Load current job queue
    queue_file = Path('/opt/smartbuild/sessions/active/session_20250829_084725_al2o/runs/run_001_084914/job_queue.json')
    
    if not queue_file.exists():
        print("Job queue file not found")
        return
    
    with open(queue_file) as f:
        jobs = json.load(f)
    
    print(f"Found {len(jobs)} jobs in queue")
    
    # Fix any stuck or failed jobs
    fixed_count = 0
    for job in jobs:
        # Reset failed jobs that failed due to tmux issues
        if job['status'] == 'failed' and 'Tmux session not found' in str(job.get('error', '')):
            job['status'] = 'queued'
            job['error'] = None
            job['started_at'] = None
            job['completed_at'] = None
            job['progress'] = 0
            fixed_count += 1
            print(f"  Reset failed job: {job['id']} ({job['type']})")
        
        # Fix stuck running job (cost_analysis at 10%)
        elif job['status'] == 'running' and job['progress'] == 10:
            # Check if its tmux session exists
            if 'tmux_session' in job:
                check_cmd = f"tmux has-session -t {job['tmux_session']} 2>/dev/null"
                result = subprocess.run(check_cmd, shell=True)
                if result.returncode != 0:
                    # Session doesn't exist, reset job
                    job['status'] = 'queued'
                    job['started_at'] = None
                    job['progress'] = 0
                    job['tmux_session'] = None
                    fixed_count += 1
                    print(f"  Reset stuck job: {job['id']} ({job['type']})")
    
    # Save fixed queue
    with open(queue_file, 'w') as f:
        json.dump(jobs, f, indent=2)
    
    print(f"\nFixed {fixed_count} jobs")
    
    # Now process each queued job manually
    session_id = 'session_20250829_084725_al2o'
    run_id = 'run_001_084914'
    
    for job in jobs:
        if job['status'] != 'queued':
            continue
        
        print(f"\nProcessing job: {job['id']} ({job['type']})")
        
        # Mark as running
        job['status'] = 'running'
        job['started_at'] = datetime.now().isoformat()
        job['progress'] = 5
        
        # Generate tmux session name
        session_short = session_id.replace('session_', '')[:10]
        job_type_map = {
            'cost_analysis': 'ca',
            'technical_documentation': 'td',
            'terraform_code': 'tf',
            'cloudformation_template': 'cf'
        }
        job_type_short = job_type_map.get(job['type'], 'unknown')
        tmux_session = f"sb_{job_type_short}_{session_short}_{run_id}"
        job['tmux_session'] = tmux_session
        
        # Check if session already exists
        check_cmd = f"tmux has-session -t {tmux_session} 2>/dev/null"
        session_exists = subprocess.run(check_cmd, shell=True).returncode == 0
        
        if not session_exists:
            print(f"  Creating tmux session: {tmux_session}")
            
            # Create the tmux session
            subprocess.run(f"tmux new-session -d -s {tmux_session}", shell=True)
            time.sleep(0.5)
            
            # Setup environment
            subprocess.run(f"tmux send-keys -t {tmux_session} 'cd /opt/smartbuild' Enter", shell=True)
            subprocess.run(f"tmux send-keys -t {tmux_session} 'source venv/bin/activate' Enter", shell=True)
            
            # Start SmartBuild CLI
            subprocess.run(f"tmux send-keys -t {tmux_session} 'claude --dangerously-skip-permissions --model claude-opus-4-1-20250805' Enter", shell=True)
            time.sleep(3)
            
            # Send Enter to confirm permissions
            subprocess.run(f"tmux send-keys -t {tmux_session} Enter", shell=True)
            time.sleep(2)
            
            print(f"  ✓ Created tmux session and started SmartBuild CLI")
        else:
            print(f"  Session already exists: {tmux_session}")
        
        # Update job progress
        job['progress'] = 10
        
        # Save updated queue after each job
        with open(queue_file, 'w') as f:
            json.dump(jobs, f, indent=2)
        
        # For now, we'll need to send the actual generation commands separately
        # The job monitor thread should pick up and complete these
        
        print(f"  Job {job['id']} is now ready for command execution")
    
    # Show final status
    print("\n" + "="*50)
    print("Final job status:")
    status_counts = {}
    for job in jobs:
        status = job['status']
        status_counts[status] = status_counts.get(status, 0) + 1
    
    for status, count in status_counts.items():
        print(f"  {status}: {count}")
    
    # List all tmux sessions
    print("\nActive tmux sessions:")
    result = subprocess.run(['tmux', 'ls'], capture_output=True, text=True)
    for line in result.stdout.strip().split('\n'):
        if line:
            print(f"  {line}")

if __name__ == "__main__":
    fix_job_processor()