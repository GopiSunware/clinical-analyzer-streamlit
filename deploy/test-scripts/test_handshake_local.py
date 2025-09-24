#!/usr/bin/env python3
"""
Test the new handshake protocol locally
Tests the redesigned flow:
1. Kill existing session if found
2. Create fresh tmux with SmartBuild CLI
3. Wait 2-3 seconds
4. Probe with timestamp
5. Verify exact response
"""

import subprocess
import time
import uuid
from datetime import datetime

def test_handshake():
    """Test the new handshake protocol"""
    
    # Create a test session name
    test_session = f"sb_test_{uuid.uuid4().hex[:8]}"
    print(f"Testing handshake with session: {test_session}")
    print("=" * 60)
    
    # Step 1: Check if session exists and kill it
    print("\n[STEP 1] Checking for existing session...")
    check_cmd = f"tmux has-session -t {test_session} 2>/dev/null"
    result = subprocess.run(check_cmd, shell=True, capture_output=True)
    
    if result.returncode == 0:
        print(f"  Found existing session {test_session}, killing it...")
        kill_cmd = f"tmux kill-session -t {test_session}"
        subprocess.run(kill_cmd, shell=True)
        print("  ✓ Existing session killed")
    else:
        print("  ✓ No existing session found")
    
    # Step 2: Create fresh tmux session with SmartBuild CLI
    print("\n[STEP 2] Creating fresh tmux session with SmartBuild CLI...")
    claude_cmd = "claude --dangerously-skip-permissions --model claude-opus-4-1-20250805"
    create_cmd = f"tmux new-session -d -s {test_session} '{claude_cmd}'"
    
    result = subprocess.run(create_cmd, shell=True, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"  ✗ Failed to create tmux session: {result.stderr}")
        return False
    
    print("  ✓ Tmux session created with SmartBuild CLI command")
    
    # Step 3: Wait for SmartBuild CLI to initialize
    print("\n[STEP 3] Waiting for SmartBuild CLI to initialize...")
    time.sleep(3)
    print("  ✓ Waited 3 seconds")
    
    # Step 4: Probe SmartBuild CLI with timestamp
    print("\n[STEP 4] Probing SmartBuild CLI with timestamp...")
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    probe_msg = f"Please reply with this exact timestamp only: {timestamp}"
    
    print(f"  Sending probe: {probe_msg}")
    # Use -l flag for literal text
    subprocess.run(f"tmux send-keys -t {test_session} -l '{probe_msg}'", shell=True)
    time.sleep(1)
    subprocess.run(f"tmux send-keys -t {test_session} Enter", shell=True)
    
    # Wait for response
    time.sleep(2)
    
    # Step 5: Capture and verify response
    print("\n[STEP 5] Capturing and verifying response...")
    capture_cmd = f"tmux capture-pane -t {test_session} -p -S -100"
    result = subprocess.run(capture_cmd, shell=True, capture_output=True, text=True)
    
    if result.returncode != 0:
        print(f"  ✗ Failed to capture output: {result.stderr}")
        # Cleanup
        subprocess.run(f"tmux kill-session -t {test_session}", shell=True)
        return False
    
    output = result.stdout
    print("\n  Captured output (last 10 lines):")
    output_lines = output.split('\n')
    for line in output_lines[-10:]:
        print(f"    > {line}")
    
    # Check if timestamp is in output
    if timestamp in output:
        # Check if it's just bash echo or actual SmartBuild CLI response
        if "command not found" in output.lower() or probe_msg in output_lines[-5:]:
            print(f"\n  ✗ FAIL: Timestamp found but appears to be bash echo, not SmartBuild CLI")
            print("  SmartBuild CLI is NOT running properly!")
        else:
            print(f"\n  ✓ SUCCESS: SmartBuild CLI responded with correct timestamp!")
            print("  Handshake protocol is working correctly")
            
            # Test sending an actual prompt
            print("\n[BONUS] Testing actual prompt...")
            test_prompt = "What is 2+2? Reply with just the number."
            subprocess.run(f"tmux send-keys -t {test_session} -l '{test_prompt}'", shell=True)
            time.sleep(0.5)
            subprocess.run(f"tmux send-keys -t {test_session} Enter", shell=True)
            time.sleep(2)
            
            # Capture response
            result = subprocess.run(capture_cmd, shell=True, capture_output=True, text=True)
            if "4" in result.stdout:
                print("  ✓ SmartBuild CLI successfully processed a test prompt!")
    else:
        print(f"\n  ✗ FAIL: Timestamp {timestamp} not found in output")
        print("  SmartBuild CLI is not responding properly")
    
    # Cleanup
    print("\n[CLEANUP] Killing test session...")
    subprocess.run(f"tmux kill-session -t {test_session}", shell=True)
    print("  ✓ Test session cleaned up")
    
    print("\n" + "=" * 60)
    print("Handshake test complete!")

if __name__ == "__main__":
    test_handshake()