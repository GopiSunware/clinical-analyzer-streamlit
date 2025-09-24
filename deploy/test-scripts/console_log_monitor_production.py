#!/usr/bin/env python3
"""
Console Log Monitor for SmartBuild Applications - Version 3
Reads logs from systemd journal with proper scrolling
"""

import streamlit as st
import subprocess
import time
from pathlib import Path
from datetime import datetime
import json

# Page config
st.set_page_config(
    page_title="Console Log Monitor",
    page_icon="📜",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for scrollable containers
st.markdown("""
<style>
    /* Make the code blocks scrollable with fixed height */
    .stCodeBlock {
        max-height: 600px !important;
        overflow-y: auto !important;
    }
    
    /* Auto-scroll to bottom for elements with auto-scroll class */
    .auto-scroll {
        scroll-behavior: smooth;
    }
    
    /* Custom container for logs */
    .log-container {
        height: 600px;
        overflow-y: auto;
        background-color: #0e1117;
        padding: 10px;
        border-radius: 5px;
        border: 1px solid #262730;
        font-family: 'Courier New', monospace;
        font-size: 13px;
        color: #fafafa;
        white-space: pre-wrap;
        word-wrap: break-word;
    }
    
    /* Keep scroll at bottom for auto-scroll enabled containers */
    .log-container.auto-scroll {
        display: flex;
        flex-direction: column-reverse;
    }
</style>
""", unsafe_allow_html=True)

st.title("📜 Console Log Monitor")
st.caption("Real-time console output monitoring for SmartBuild applications (via systemd journal)")

# Initialize session state
if 'auto_scroll' not in st.session_state:
    st.session_state.auto_scroll = True
if 'last_log_update' not in st.session_state:
    st.session_state.last_log_update = {}

# Define log sources - using systemd services
LOG_SOURCES = {
    "main_app": {
        "name": "SmartBuild Main App",
        "service": "smartbuild",
        "icon": "🏗️"
    },
    "monitor_app": {
        "name": "SmartBuild Monitor",
        "service": "smartmonitor",
        "icon": "📊"
    },
    "console_monitor": {
        "name": "Console Monitor",
        "service": "console-monitor",
        "icon": "📜"
    }
}

def check_service_status(service_name):
    """Check if a systemd service is running"""
    try:
        cmd = f"systemctl is-active {service_name}"
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        return result.stdout.strip() == "active"
    except:
        return False

def get_journal_logs(service_name, lines=200):
    """Get logs from systemd journal"""
    try:
        cmd = f"/usr/bin/journalctl -u {service_name} -n {lines} --no-pager --no-hostname"
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        if result.returncode == 0:
            return result.stdout if result.stdout else "No logs available"
        else:
            return f"Error accessing logs (may need sudo permissions)"
    except Exception as e:
        return f"Error reading journal: {e}"

def parse_log_level(line):
    """Determine log level from line content"""
    line_lower = line.lower()
    if 'error' in line_lower or 'exception' in line_lower or 'failed' in line_lower:
        return 'error'
    elif 'warning' in line_lower or 'warn' in line_lower:
        return 'warning'
    elif '[info]' in line_lower or 'started' in line_lower:
        return 'info'
    elif '[debug]' in line_lower or 'debug:' in line_lower:
        return 'debug'
    elif '[job queue' in line_lower:
        return 'job'
    elif '✅' in line or '✓' in line:
        return 'success'
    elif '❌' in line or '✗' in line:
        return 'error'
    elif '⚠️' in line:
        return 'warning'
    return 'normal'

def format_log_line(line):
    """Format a log line with color coding"""
    level = parse_log_level(line)
    
    # Color mapping
    colors = {
        'error': 'red',
        'warning': 'orange',
        'info': 'blue',
        'debug': 'gray',
        'job': 'green',
        'success': 'green',
        'normal': None
    }
    
    color = colors.get(level)
    if color:
        return f':{color}[{line}]'
    return line

def display_logs_in_container(content, container_id, auto_scroll=True):
    """Display logs in a custom scrollable container"""
    if content and not content.startswith("Error"):
        # Create container with optional auto-scroll
        scroll_class = "auto-scroll" if auto_scroll else ""
        
        # For auto-scroll, reverse the content so newest is at bottom
        if auto_scroll:
            lines = content.split('\n')
            lines.reverse()
            content = '\n'.join(lines)
        
        # Use a container to hold the logs
        container = st.container()
        with container:
            st.code(content, language='log')
    else:
        st.warning(content if content else "No logs available")

def search_logs_for_pattern(pattern, lines=500):
    """Search all service logs for a specific pattern"""
    results = []
    for source_id, source in LOG_SOURCES.items():
        content = get_journal_logs(source['service'], lines)
        if content and not content.startswith("Error"):
            for line in content.split('\n'):
                if pattern.lower() in line.lower():
                    results.append({
                        'source': source['name'],
                        'line': line,
                        'icon': source['icon']
                    })
    return results

# Sidebar controls
with st.sidebar:
    st.header("🎛️ Controls")
    
    # Auto-refresh
    auto_refresh = st.checkbox("Auto-refresh", value=True)
    if auto_refresh:
        refresh_interval = st.slider("Refresh interval (seconds)", 1, 10, 5)
    
    # Lines to show
    num_lines = st.number_input("Lines to display", min_value=50, max_value=1000, value=200, step=50)
    
    # Auto-scroll
    st.session_state.auto_scroll = st.checkbox("Auto-scroll to bottom", value=st.session_state.auto_scroll)
    
    st.divider()
    
    # Search
    st.subheader("🔍 Search Logs")
    search_term = st.text_input("Search term")
    if st.button("Search") and search_term:
        results = search_logs_for_pattern(search_term, num_lines)
        if results:
            st.success(f"Found {len(results)} matches")
            for result in results[:10]:  # Show first 10
                st.caption(f"{result['icon']} {result['source']}")
                with st.expander("View", expanded=False):
                    st.code(result['line'])
        else:
            st.warning("No matches found")
    
    st.divider()
    
    # Service status
    st.subheader("📊 Service Status")
    for source_id, source in LOG_SOURCES.items():
        is_running = check_service_status(source['service'])
        status = "🟢 Running" if is_running else "🔴 Stopped"
        st.caption(f"{source['icon']} {source['name']}: {status}")

# Main content area
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📱 Split View", 
    "🏗️ Main App", 
    "📊 Monitor",
    "📜 Console Monitor",
    "🔍 Filtered View"
])

with tab1:
    st.subheader("Split View - All Applications")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### 🏗️ Main Application")
        content = get_journal_logs(LOG_SOURCES['main_app']['service'], num_lines)
        
        # Create a container with fixed height
        container1 = st.container(height=600)
        with container1:
            if content and not content.startswith("Error"):
                st.code(content, language='log')
            else:
                st.warning(content if content else "No logs available")
    
    with col2:
        st.markdown("### 📊 Monitor Application")
        content = get_journal_logs(LOG_SOURCES['monitor_app']['service'], num_lines)
        
        # Create a container with fixed height
        container2 = st.container(height=600)
        with container2:
            if content and not content.startswith("Error"):
                st.code(content, language='log')
            else:
                st.warning(content if content else "No logs available")
    
    # Stats
    st.divider()
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Last Refresh", datetime.now().strftime("%H:%M:%S"))
    with col2:
        st.metric("Display Lines", num_lines)
    with col3:
        refresh_text = f"Every {refresh_interval}s" if auto_refresh else "Manual"
        st.metric("Refresh Mode", refresh_text)

with tab2:
    st.subheader("🏗️ Main Application Log")
    
    # Controls
    col1, col2, col3 = st.columns([1, 1, 2])
    with col1:
        if st.button("🔄 Refresh", key="refresh_main"):
            st.rerun()
    with col2:
        if st.button("📋 Copy Command", key="copy_main"):
            st.code("sudo journalctl -u smartbuild -f")
    with col3:
        st.caption("Service: smartbuild")
    
    # Log content in fixed height container
    content = get_journal_logs(LOG_SOURCES['main_app']['service'], num_lines)
    container = st.container(height=600)
    with container:
        if content and not content.startswith("Error"):
            st.code(content, language='log')
        else:
            st.warning(content if content else "No log content available")

with tab3:
    st.subheader("📊 Monitor Application Log")
    
    # Controls
    col1, col2, col3 = st.columns([1, 1, 2])
    with col1:
        if st.button("🔄 Refresh", key="refresh_monitor"):
            st.rerun()
    with col2:
        if st.button("📋 Copy Command", key="copy_monitor"):
            st.code("sudo journalctl -u smartmonitor -f")
    with col3:
        st.caption("Service: smartmonitor")
    
    # Log content in fixed height container
    content = get_journal_logs(LOG_SOURCES['monitor_app']['service'], num_lines)
    container = st.container(height=600)
    with container:
        if content and not content.startswith("Error"):
            st.code(content, language='log')
        else:
            st.warning(content if content else "No log content available")

with tab4:
    st.subheader("📜 Console Monitor Log")
    
    # Controls
    col1, col2, col3 = st.columns([1, 1, 2])
    with col1:
        if st.button("🔄 Refresh", key="refresh_console"):
            st.rerun()
    with col2:
        if st.button("📋 Copy Command", key="copy_console"):
            st.code("sudo journalctl -u console-monitor -f")
    with col3:
        st.caption("Service: console-monitor")
    
    # Log content in fixed height container
    content = get_journal_logs(LOG_SOURCES['console_monitor']['service'], num_lines)
    container = st.container(height=600)
    with container:
        if content and not content.startswith("Error"):
            st.code(content, language='log')
        else:
            st.warning(content if content else "No log content available")

with tab5:
    st.subheader("🔍 Filtered View")
    
    # Filter controls
    col1, col2, col3 = st.columns(3)
    with col1:
        log_level = st.selectbox("Log Level", ["All", "Error", "Warning", "Info", "Debug", "Job Queue"])
    with col2:
        source_filter = st.selectbox("Source", ["All", "Main App", "Monitor", "Console Monitor"])
    with col3:
        keyword = st.text_input("Keyword Filter", key="filter_keyword")
    
    # Combine logs and filter
    all_logs = []
    
    for source_id, source in LOG_SOURCES.items():
        if source_filter != "All" and source['name'] != source_filter:
            continue
            
        content = get_journal_logs(source['service'], num_lines)
        if content and not content.startswith("Error"):
            for line in content.split('\n'):
                if not line.strip():
                    continue
                
                # Apply filters
                if log_level != "All":
                    level = parse_log_level(line)
                    if log_level.lower() not in level:
                        continue
                
                if keyword and keyword.lower() not in line.lower():
                    continue
                
                all_logs.append({
                    'source': source['name'],
                    'icon': source['icon'],
                    'line': line,
                    'level': parse_log_level(line)
                })
    
    # Display filtered logs in scrollable container
    if all_logs:
        st.caption(f"Showing {len(all_logs)} filtered entries")
        container = st.container(height=600)
        with container:
            log_text = ""
            for log in all_logs[-num_lines:]:  # Show last N lines
                log_text += f"{log['icon']} [{log['source']}] {log['line']}\n"
            st.code(log_text, language='log')
    else:
        st.info("No logs match the selected filters")

# Auto-refresh logic with JavaScript for auto-scroll
if auto_refresh:
    if st.session_state.auto_scroll:
        # Inject JavaScript to auto-scroll code blocks to bottom
        st.markdown("""
        <script>
        // Auto-scroll all code blocks to bottom
        const codeBlocks = document.querySelectorAll('.stCodeBlock');
        codeBlocks.forEach(block => {
            block.scrollTop = block.scrollHeight;
        });
        </script>
        """, unsafe_allow_html=True)
    
    time.sleep(refresh_interval)
    st.rerun()

# Footer
st.divider()
col1, col2, col3 = st.columns(3)
with col1:
    st.caption("Console Log Monitor v3.0")
with col2:
    st.caption(f"Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
with col3:
    st.caption("Reading from systemd journal")