#!/usr/bin/env python3
"""
Send actual generation commands to tmux sessions for jobs
"""

import subprocess
import time
import json
from pathlib import Path

def send_generation_command(tmux_session, job_type, session_id, run_id):
    """Send the appropriate generation command to a tmux session"""
    
    session_path = Path(f'/opt/smartbuild/sessions/active/{session_id}')
    run_path = session_path / 'runs' / run_id
    
    print(f"Sending {job_type} command to {tmux_session}")
    
    if job_type == 'cost_analysis':
        # Find the diagram file
        diagrams_path = run_path / 'diagrams'
        xml_files = list(diagrams_path.glob('*.xml')) + list(diagrams_path.glob('*.drawio'))
        if not xml_files:
            print("  No diagram files found")
            return False
        
        diagram_file = xml_files[0]
        agent_path = Path('/opt/smartbuild/.claude/agents/cost-analyzer.md')
        
        if not agent_path.exists():
            print("  Cost analyzer agent not found")
            return False
        
        # Read the agent prompt
        with open(agent_path) as f:
            agent_prompt = f.read()
        
        # Read the diagram
        with open(diagram_file) as f:
            diagram_content = f.read()
        
        # Create the full prompt
        prompt = f'''
Task: Cost Analysis with SmartBuild AWS Cost Calculator Integration

Agent Configuration:
{agent_prompt}

Here is the architecture diagram to analyze:

{diagram_content}

Please analyze this architecture and provide:
1. BASELINE cost calculation (all on-demand pricing)
2. OPTIMIZED cost calculation (with Reserved Instances, Spot, Savings Plans, etc.)
3. Show the savings percentage between baseline and optimized
4. Provide detailed recommendations for cost optimization

Save the complete analysis to: artifacts/latest/cost_analysis/cost_analysis.md

IMPORTANT: When complete, write "TASK COMPLETED" as confirmation.
'''
        
        # Send the prompt line by line
        for line in prompt.split('\n'):
            # Escape special characters
            line = line.replace('"', '\\"').replace('$', '\\$').replace('`', '\\`')
            if line.strip():
                cmd = f'tmux send-keys -t {tmux_session} "{line}" Enter'
                subprocess.run(cmd, shell=True)
                time.sleep(0.05)  # Small delay between lines
        
        print("  ✓ Cost analysis prompt sent")
        return True
    
    else:
        print(f"  Job type {job_type} not implemented yet")
        return False

def main():
    """Check running jobs and send commands"""
    
    # Load job queue
    queue_file = Path('/opt/smartbuild/sessions/active/session_20250829_084725_al2o/runs/run_001_084914/job_queue.json')
    
    if not queue_file.exists():
        print("Job queue not found")
        return
    
    with open(queue_file) as f:
        jobs = json.load(f)
    
    print(f"Found {len(jobs)} jobs")
    
    for job in jobs:
        if job['status'] == 'running' and job.get('tmux_session'):
            tmux_session = job['tmux_session']
            
            # Check if session exists
            check_cmd = f"tmux has-session -t {tmux_session} 2>/dev/null"
            if subprocess.run(check_cmd, shell=True).returncode != 0:
                print(f"Session {tmux_session} doesn't exist")
                continue
            
            # Check if SmartBuild CLI is ready (not already processing)
            capture_cmd = f"tmux capture-pane -t {tmux_session} -p | tail -3"
            result = subprocess.run(capture_cmd, shell=True, capture_output=True, text=True)
            output = result.stdout.lower()
            
            # Look for SmartBuild CLI prompt
            if '⏵' in output or '> ' in result.stdout:
                print(f"\nJob {job['id']} - SmartBuild CLI is ready in {tmux_session}")
                
                # Send the generation command
                success = send_generation_command(
                    tmux_session,
                    job['type'],
                    job['session_id'],
                    job['run_id']
                )
                
                if success:
                    # Update job progress
                    job['progress'] = 20
                    with open(queue_file, 'w') as f:
                        json.dump(jobs, f, indent=2)
                    print(f"  Job {job['id']} command sent successfully")
            else:
                print(f"\nJob {job['id']} - SmartBuild CLI is busy or not ready in {tmux_session}")
                print(f"  Last output: {output[:100]}")

if __name__ == "__main__":
    main()