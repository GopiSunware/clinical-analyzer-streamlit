import streamlit as st
import os
import time
import uuid
import argparse
import sys
from datetime import datetime
from dotenv import load_dotenv
import pandas as pd

# Load environment variables (if .env file exists)
try:
    load_dotenv()
except Exception as e:
    # If .env file doesn't exist or has issues, continue without it
    print(f"Warning: Could not load .env file: {e}")
    pass

# Import our custom modules
from src.database_manager import DatabaseManager
from src.document_processor import DocumentProcessor
from src.ingestion_manager import IngestionManager
from src.chat_assistant import ChatAssistant

def parse_arguments():
    """Parse command line arguments"""
    import sys
    # Check for debug flag in sys.argv
    debug_mode = '--debug' in sys.argv
    return debug_mode

# Parse debug mode from command line
DEBUG_MODE = parse_arguments()



# Page configuration
st.set_page_config(
    page_title="Clinical Analyzer",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Detect theme for better UX
def get_theme_info():
    """Get current theme information with better detection"""
    # Try to detect system theme using JavaScript
    try:
        # Check if user has explicitly set a theme preference
        if hasattr(st.session_state, 'user_theme_preference') and st.session_state.user_theme_preference != "auto":
            is_dark = st.session_state.user_theme_preference == "dark"
        else:
            # Default to dark mode for better UX with the clinical analyzer
            # This can be changed by checking browser preferences or adding a toggle
            is_dark = True
            
        return {
            'is_dark': is_dark,
            'theme': 'dark' if is_dark else 'light'
        }
    except Exception as e:
        # Default to dark mode if detection fails
        return {'is_dark': True, 'theme': 'dark'}

# Get theme information for dynamic styling
theme_info = get_theme_info()

# Enhanced CSS with comprehensive dark mode fixes
st.markdown(f"""
<style>
    /* Force dark mode for the entire application */
    .stApp {{
        background-color: #0E1117 !important;
        color: #FFFFFF !important;
    }}
    
    /* Main content area - fix the white background issue */
    .main, .main .block-container, 
    [data-testid="stAppViewContainer"], 
    [data-testid="stMain"],
    [data-testid="stAppViewContainer"] > .main,
    .main > div,
    .main > div > div,
    .main > div > div > div {{
        background-color: #0E1117 !important;
        color: #FFFFFF !important;
    }}
    
    /* Fix all container backgrounds that could be white */
    [data-testid="stVerticalBlockBorderWrapper"],
    [data-testid="stVerticalBlock"],
    [data-testid="stHorizontalBlock"],
    [data-testid="stContainer"],
    [data-testid="column"],
    [data-testid="stColumn"],
    .element-container,
    .row-widget,
    .stMarkdown > div,
    .block-container {{
        background-color: transparent !important;
    }}
    
    /* Remove gray backgrounds from columns and containers */
    [data-testid="stColumns"],
    [data-testid="stColumns"] > div,
    [data-testid="stColumn"] > div,
    .stColumns,
    .stColumns > div,
    .stColumn > div,
    div[data-testid="column"],
    div[data-testid="column"] > div {{
        background-color: transparent !important;
        background: transparent !important;
    }}
    
    /* Remove gray backgrounds from button containers */
    .stButton,
    .stButton > div,
    [data-testid="stButton"],
    [data-testid="stButton"] > div {{
        background-color: transparent !important;
        background: transparent !important;
    }}
    
    /* Ensure main content area has no gray backgrounds */
    .main-content,
    .main-content > div,
    [data-testid="stContainer"] > div,
    [data-testid="stVerticalBlock"] > div {{
        background-color: transparent !important;
        background: transparent !important;
    }}
    
    /* Modern theme-aware styling */
    .main-header {{
        font-size: 2.5rem;
        font-weight: bold;
        color: #60A5FA;
        margin-bottom: 1rem;
        text-align: center;
        padding: 1rem 0;
        border-bottom: 2px solid #374151;
        background-color: transparent !important;
    }}
    
    /* Enhanced cards with dark theme */
    .stat-card {{
        background: linear-gradient(135deg, #374151 0%, #4B5563 100%);
        border-radius: 12px;
        padding: 1.2rem;
        margin: 0.8rem 0;
        border-left: 5px solid #60A5FA;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.3);
        transition: transform 0.2s ease;
        color: #FFFFFF !important;
    }}
    
    .stat-card:hover {{
        transform: translateY(-2px);
        box-shadow: 0 6px 12px rgba(0, 0, 0, 0.4);
    }}
    
    .patient-card {{
        background: linear-gradient(135deg, #374151 0%, #4B5563 100%);
        border-radius: 12px;
        padding: 1.2rem;
        margin: 0.8rem 0;
        border: 2px solid #4B5563;
        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.2);
        color: #FFFFFF !important;
    }}
    
    /* Modern chat messages with dark theme */
    .chat-message {{
        padding: 1.2rem;
        margin: 1rem 0;
        border-radius: 16px;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.2);
        transition: transform 0.2s ease;
        max-width: 85%;
    }}
    
    .chat-message:hover {{
        transform: translateY(-1px);
    }}
    
    .user-message {{
        background: linear-gradient(135deg, #1E40AF 0%, #3B82F6 100%);
        margin-left: auto;
        margin-right: 0;
        color: #FFFFFF !important;
        border-bottom-right-radius: 4px;
    }}
    
    /* Ensure all text content in user messages is visible */
    .user-message, 
    .user-message *, 
    .user-message strong, 
    .user-message span, 
    .user-message p, 
    .user-message div {{
        color: #FFFFFF !important;
    }}
    
    .assistant-message {{
        background: linear-gradient(135deg, #374151 0%, #4B5563 100%);
        margin-left: 0;
        margin-right: auto;
        color: #FFFFFF !important;
        border-bottom-left-radius: 4px;
    }}
    
    /* Ensure all text content in assistant messages is visible */
    .assistant-message, 
    .assistant-message *, 
    .assistant-message strong, 
    .assistant-message span, 
    .assistant-message p, 
    .assistant-message div {{
        color: #FFFFFF !important;
    }}
    
    /* Enhanced input styling with dark form containers */
    .stTextArea > div > div > textarea {{
        border-radius: 12px !important;
        border: 2px solid #4B5563 !important;
        background: #374151 !important;
        color: #FFFFFF !important;
        transition: all 0.3s ease !important;
        /* Hide scrollbar */
        scrollbar-width: none !important; /* Firefox */
        -ms-overflow-style: none !important; /* Internet Explorer 10+ */
        overflow-y: auto !important;
    }}
    
    /* Hide scrollbar for WebKit browsers */
    .stTextArea > div > div > textarea::-webkit-scrollbar {{
        display: none !important;
    }}
    
    .stTextArea > div > div > textarea:focus {{
        border-color: #60A5FA !important;
        box-shadow: 0 0 0 3px rgba(96, 165, 250, 0.1) !important;
    }}
    
    /* Enhanced chat input styling for st.chat_input */
    [data-testid="stChatInput"] {{
        background: transparent !important;
    }}
    
    [data-testid="stChatInput"] > div {{
        background: #374151 !important;
        border: 2px solid #4B5563 !important;
        border-radius: 12px !important;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.2) !important;
    }}
    
    [data-testid="stChatInput"] input {{
        background: transparent !important;
        color: #FFFFFF !important;
        border: none !important;
        font-size: 16px !important;
        padding: 12px 16px !important;
    }}
    
    [data-testid="stChatInput"] input::placeholder {{
        color: #9CA3AF !important;
    }}
    
    [data-testid="stChatInput"] input:focus {{
        outline: none !important;
        box-shadow: none !important;
    }}
    
    [data-testid="stChatInput"]:focus-within > div {{
        border-color: #60A5FA !important;
        box-shadow: 0 0 0 3px rgba(96, 165, 250, 0.1), 0 2px 8px rgba(0, 0, 0, 0.2) !important;
    }}
    
    /* Custom chat input styling fallback */
    .chat-input-container {{
        background: #374151 !important;
        border: 2px solid #4B5563 !important;
        border-radius: 12px !important;
        padding: 12px !important;
        margin: 8px 0 !important;
    }}
    
    .chat-input {{
        width: 100% !important;
        background: transparent !important;
        border: none !important;
        color: #FFFFFF !important;
        font-size: 16px !important;
        line-height: 1.5 !important;
        resize: none !important;
        outline: none !important;
        min-height: 60px !important;
        max-height: 200px !important;
        overflow-y: auto !important;
        /* Hide scrollbar */
        scrollbar-width: none !important;
        -ms-overflow-style: none !important;
    }}
    
    .chat-input::-webkit-scrollbar {{
        display: none !important;
    }}
    
    .chat-input::placeholder {{
        color: #9CA3AF !important;
    }}
    
    /* AGGRESSIVE GRAY BACKGROUND REMOVAL */
    /* Target all possible container elements that could have gray backgrounds */
    .main .block-container,
    .main .block-container > div,
    .main .block-container > div > div,
    .main .block-container > div > div > div,
    [data-testid="stAppViewContainer"] section,
    [data-testid="stAppViewContainer"] section > div,
    [data-testid="stAppViewContainer"] section > div > div,
    [data-testid="stMain"] > div,
    [data-testid="stMain"] > div > div,
    [data-testid="stMain"] > div > div > div {{
        background-color: transparent !important;
        background: none !important;
    }}
    
    /* Remove backgrounds from column containers specifically */
    .row-widget.stColumns,
    .row-widget.stColumns > div,
    [data-testid="stColumns"],
    [data-testid="stColumns"] > div,
    [data-testid="column"] {{
        background-color: transparent !important;
        background: none !important;
        border: none !important;
        box-shadow: none !important;
        padding: 0 !important;
    }}
    
    /* Remove backgrounds from any div with specific classes */
    div[class*="css-"],
    section[class*="css-"] {{
        background-color: transparent !important;
        background: none !important;
    }}
    
    /* Specific override for suggestion buttons area */
    .element-container:has(.stButton),
    .stButton:has(button),
    [data-testid="stButton"]:has(button) {{
        background-color: transparent !important;
        background: none !important;
    }}
    
    /* Fix form container backgrounds */
    .stTextArea > div, 
    .stTextArea, 
    .stTextArea > div > div,
    .stForm, 
    .stForm > div, 
    [data-testid="stForm"],
    .stForm > div > div, 
    .stForm [data-testid="stVerticalBlock"] {{
        background-color: transparent !important;
    }}
    
    /* Button enhancements */
    .stButton > button {{
        border-radius: 12px !important;
        background: linear-gradient(135deg, #3B82F6 0%, #1D4ED8 100%) !important;
        border: none !important;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15) !important;
        transition: all 0.3s ease !important;
        font-weight: 600 !important;
        color: #FFFFFF !important;
    }}
    
    .stButton > button:hover {{
        transform: translateY(-2px) !important;
        box-shadow: 0 6px 20px rgba(0, 0, 0, 0.2) !important;
    }}
    
    /* Remove white backgrounds from all text containers */
    [data-testid="stMarkdownContainer"], 
    .stMarkdown, 
    .main div, 
    .main span, 
    .main p,
    .main h1,
    .main h2,
    .main h3,
    .main h4,
    .main h5,
    .main h6 {{
        background-color: transparent !important;
        color: #FFFFFF !important;
    }}
    
    /* Fix Streamlit elements backgrounds */
    .stAlert, 
    .stInfo, 
    .stSuccess, 
    .stWarning, 
    .stError {{
        background-color: transparent !important;
    }}
    
    .stAlert > div, 
    .stInfo > div, 
    .stSuccess > div, 
    .stWarning > div, 
    .stError > div {{
        background-color: transparent !important;
        color: inherit !important;
    }}
    
    /* Fix form elements backgrounds */
    .stTextInput > div > div, 
    .stTextArea > div > div, 
    .stSelectbox > div > div {{
        background-color: #374151 !important;
        color: #FFFFFF !important;
        border: 1px solid #4B5563 !important;
    }}
    
    /* Fix separator backgrounds */
    hr, .stHorizontalBlock {{
        background-color: #4B5563 !important;
        border-color: #4B5563 !important;
    }}
    
    /* Enhanced sidebar styling with proper dark backgrounds */
    .css-1d391kg {{
        background: linear-gradient(180deg, #1F2937 0%, #374151 100%) !important;
        color: #FFFFFF !important;
    }}
    
    /* Remove white backgrounds from sidebar elements */
    [data-testid="stSidebar"], 
    [data-testid="stSidebar"] *, 
    .css-1d391kg, 
    .css-1d391kg * {{
        background-color: transparent !important;
        color: #FFFFFF !important;
    }}
    
    /* Ensure all sidebar text is visible with no white backgrounds */
    .css-1d391kg .markdown-text-container,
    .css-1d391kg .stMarkdown,
    .css-1d391kg h1,
    .css-1d391kg h2,
    .css-1d391kg h3,
    .css-1d391kg p,
    .css-1d391kg div {{
        color: #FFFFFF !important;
        background-color: transparent !important;
    }}
    
    /* Fix sidebar buttons and form elements */
    [data-testid="stSidebar"] .stButton > button {{
        background: linear-gradient(135deg, #374151 0%, #4B5563 100%) !important;
        color: #FFFFFF !important;
        border: 1px solid #4B5563 !important;
    }}
    
    [data-testid="stSidebar"] .stSelectbox > div > div, 
    [data-testid="stSidebar"] .stTextInput > div > div {{
        background-color: #374151 !important;
        color: #FFFFFF !important;
        border: 1px solid #4B5563 !important;
    }}
    
    /* Fix sidebar metric containers */
    [data-testid="stSidebar"] .metric-container, 
    [data-testid="stSidebar"] .metric-card {{
        background-color: #374151 !important;
    }}
    
    /* Enhanced metrics display */
    .metric-container {{
        display: flex;
        flex-wrap: wrap;
        gap: 1rem;
        justify-content: space-around;
        margin: 1rem 0;
    }}
    
    .metric-card {{
        background: linear-gradient(135deg, #374151 0%, #4B5563 100%);
        border-radius: 12px;
        padding: 1rem;
        text-align: center;
        min-width: 120px;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.2);
        color: #FFFFFF !important;
    }}
    
    /* Success/Error message styling */
    .success-message {{
        color: #10B981;
        font-weight: 600;
        padding: 0.5rem;
        border-radius: 8px;
        background: rgba(16, 185, 129, 0.1);
    }}
    
    .error-message {{
        color: #EF4444;
        font-weight: 600;
        padding: 0.5rem;
        border-radius: 8px;
        background: rgba(239, 68, 68, 0.1);
    }}
    
    .warning-message {{
        color: #F59E0B;
        font-weight: 600;
        padding: 0.5rem;
        border-radius: 8px;
        background: rgba(245, 158, 11, 0.1);
    }}
    
    /* Modern suggestions styling */
    .suggestion-grid {{
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
        gap: 1rem;
        margin: 1rem 0;
    }}
    
    /* Ensure form submit buttons have proper dark styling */
    .stForm [data-testid="stFormSubmitButton"] > button {{
        background: linear-gradient(135deg, #3B82F6 0%, #1D4ED8 100%) !important;
        color: #FFFFFF !important;
    }}
    
    /* Fix any remaining form-related white backgrounds */
    [data-testid="stFormSubmitButton"], 
    .stFormSubmitButton {{
        background-color: transparent !important;
    }}
    
    /* Global dark mode text fixes */
    [data-testid="stAppViewContainer"] {{
        color: #FFFFFF !important;
        background-color: #0E1117 !important;
    }}
    
    [data-testid="stMarkdownContainer"] {{
        color: inherit !important;
        background-color: transparent !important;
    }}
    
    /* Force all text to be white in dark mode */
    * {{
        color: #FFFFFF !important;
    }}
    
    /* Remove ALL gray/white backgrounds - comprehensive fix */
    div:not(.user-message):not(.assistant-message):not(.stat-card):not(.patient-card):not(.chat-message):not(.metric-card),
    section,
    [class*="block-container"],
    [class*="main"],
    [class*="appview"],
    [data-testid*="block"],
    [data-testid*="container"],
    [data-testid*="column"],
    [data-testid*="vertical"],
    [data-testid*="horizontal"] {{
        background-color: transparent !important;
        background: transparent !important;
    }}
    
    /* Specifically target suggestion button area */
    .suggestion-grid,
    .suggestion-grid > div,
    [data-testid="stColumns"],
    [data-testid="stColumn"] {{
        background-color: transparent !important;
        background: transparent !important;
        border: none !important;
        box-shadow: none !important;
    }}
    
    /* Override for specific colored elements that should maintain their colors */
    .user-message, .user-message * {{
        color: #FFFFFF !important;
    }}
    
    .assistant-message, .assistant-message * {{
        color: #FFFFFF !important;
    }}
    
    .success-message, .success-message * {{
        color: #10B981 !important;
    }}
    
    .error-message, .error-message * {{
        color: #EF4444 !important;
    }}
    
    .warning-message, .warning-message * {{
        color: #F59E0B !important;
    }}
    
    .main-header {{
        color: #60A5FA !important;
    }}
</style>
""", unsafe_allow_html=True)

# Initialize session state with new features
def initialize_session_state():
    """Initialize session state variables"""
    if 'system_initialized' not in st.session_state:
        st.session_state.system_initialized = False
    
    if 'session_id' not in st.session_state:
        st.session_state.session_id = str(uuid.uuid4())
    
    if 'chat_history' not in st.session_state:
        st.session_state.chat_history = []
    
    if 'current_patient' not in st.session_state:
        st.session_state.current_patient = None
    
    if 'debug_mode' not in st.session_state:
        st.session_state.debug_mode = DEBUG_MODE
    
    # Theme preference tracking
    if 'user_theme_preference' not in st.session_state:
        st.session_state.user_theme_preference = "auto"
    
    if 'ingestion_completed' not in st.session_state:
        st.session_state.ingestion_completed = False
    
    if 'query_input' not in st.session_state:
        st.session_state.query_input = ""
    
    if 'processing_in_progress' not in st.session_state:
        st.session_state.processing_in_progress = False

# Initialize components
def initialize_system():
    """Initialize all system components"""
    try:
        # Get AI provider configuration
        ai_provider = os.getenv('AI_PROVIDER', 'openai').lower()
        db_name = os.getenv('DATABASE_NAME', 'clinical_analyzer.db')
        temperature = float(os.getenv('TEMPERATURE', '0.3'))
        max_tokens = int(os.getenv('MAX_TOKENS', '2000'))
        
        # Get provider-specific configuration
        if ai_provider == 'gemini':
            model = os.getenv('GEMINI_MODEL', 'gemini-1.5-flash')
            # Check if key.json exists for Gemini
            if not os.path.exists('key.json'):
                st.error("⚠️ Google Cloud service account key file (key.json) not found. This is required for Gemini AI.")
                st.stop()
            api_key = None  # Gemini uses service account key file
        else:  # OpenAI
            model = os.getenv('OPENAI_MODEL', 'gpt-3.5-turbo')
            api_key = os.getenv('OPENAI_API_KEY')
            if not api_key:
                st.error("⚠️ OpenAI API key not found. Please set OPENAI_API_KEY in your .env file.")
                st.stop()
        
        # Display configuration for debugging
        provider_emoji = "🧠" if ai_provider == "gemini" else "🤖"
        st.info(f"{provider_emoji} Using {ai_provider.upper()}: {model} | Temperature: {temperature} | Max tokens: {max_tokens}")
        
        # Initialize components with unified AI client
        db_manager = DatabaseManager(db_name)
        document_processor = DocumentProcessor(
            ai_provider=ai_provider,
            api_key=api_key,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens
        )
        ingestion_manager = IngestionManager(db_manager, document_processor)
        chat_assistant = ChatAssistant(
            ai_provider=ai_provider,
            api_key=api_key,
            model=model,
            database_manager=db_manager,
            temperature=temperature,
            max_tokens=max_tokens
        )
        
        return db_manager, document_processor, ingestion_manager, chat_assistant
    
    except Exception as e:
        st.error(f"❌ Failed to initialize system: {str(e)}")
        st.stop()

def run_initial_ingestion(ingestion_manager):
    """Run initial data ingestion if needed"""
    if not st.session_state.ingestion_completed:
        with st.spinner("🔄 Checking for new files to ingest..."):
            summary = ingestion_manager.get_ingestion_summary()
            
            # Check if any files need processing
            needs_processing = summary['pending_processing']['needs_processing']
            
            if needs_processing:
                pending_files = summary['pending_processing']['total_files']
                pending_docs = summary['pending_processing']['documents']
                pending_images = summary['pending_processing']['images']
                
                st.info(f"📊 Found {pending_files} files to process ({pending_docs} documents, {pending_images} images)")
                
                with st.spinner("📊 Processing dataset... This may take a few minutes."):
                    result = ingestion_manager.full_ingestion(show_progress=False)
                
                if result['status'] == 'success' or result['status'] == 'partial_success':
                    patients = result.get('total_patients', 0)
                    images = result.get('total_images', 0)
                    st.success(f"✅ Successfully processed {patients} patients and {images} images!")
                    st.session_state.ingestion_completed = True
                else:
                    st.error(f"❌ Ingestion failed: {result.get('message', 'Unknown error')}")
            else:
                # All files are already processed
                st.session_state.ingestion_completed = True
                st.success("✅ All data is up to date - no processing needed!")

def render_sidebar(db_manager, ingestion_manager, chat_assistant):
    """Render the sidebar with statistics and controls"""
    
    # Get stats once for use in multiple sections
    stats = db_manager.get_stats()
    
    # Patient Context
    st.sidebar.markdown("## 👤 Patient Context")
    
    current_patient = st.session_state.current_patient
    if current_patient:
        st.sidebar.markdown(f"""
        <div class="patient-card">
            <strong>Current Patient:</strong><br>
            {current_patient}<br>
            <em>All queries will focus on this patient</em>
        </div>
        """, unsafe_allow_html=True)
        
        if st.sidebar.button("🔄 Clear Patient Context"):
            st.session_state.current_patient = None
            chat_assistant.clear_patient_context()
            st.rerun()
    else:
        st.sidebar.info("💡 No patient selected. Queries will search across all patients.")
    
    # Patient Selection
    st.sidebar.markdown("### 🔍 Select Patient")
    patients = db_manager.get_all_patients()
    
    if patients:
        patient_options = [""] + [f"{p['name']} ({p.get('patient_id', 'No ID')})" for p in patients]
        selected_patient = st.sidebar.selectbox(
            "Choose a patient:",
            patient_options,
            key="patient_selector"
        )
        
        if selected_patient and selected_patient != "":
            patient_name = selected_patient.split(" (")[0]
            if patient_name != st.session_state.current_patient:
                st.session_state.current_patient = patient_name
                chat_assistant.set_patient_context(patient_name=patient_name)
                st.rerun()
    
    # Quick Patient Search
    st.sidebar.markdown("### 🔎 Quick Search")
    search_query = st.sidebar.text_input("Search patients:", placeholder="Enter patient name or ID")
    
    if search_query:
        search_results = db_manager.search_patients(search_query)
        if search_results:
            st.sidebar.markdown("**Search Results:**")
            for result in search_results[:5]:
                if st.sidebar.button(f"📋 {result['name']}", key=f"search_{result['name']}"):
                    patient_name = result['name']
                    st.session_state.current_patient = patient_name
                    chat_assistant.set_patient_context(patient_name=patient_name)
                    st.rerun()
        else:
            st.sidebar.warning("No patients found matching your search.")
    
    # Chat Management
    st.sidebar.markdown("## 💬 Chat Management")
    
    if st.sidebar.button("🗑️ Clear Chat History"):
        st.session_state.chat_history = []
        st.rerun()
    
    # Data Management
    st.sidebar.markdown("## ⚙️ Data Management")
    
    # Disable refresh button if processing is in progress
    refresh_disabled = st.session_state.processing_in_progress
    refresh_label = "⏳ Processing..." if refresh_disabled else "🔄 Refresh Data"
    
    if st.sidebar.button(refresh_label, disabled=refresh_disabled):
        # Set processing flag to prevent duplicate operations
        st.session_state.processing_in_progress = True
        
        try:
            with st.spinner("Refreshing data..."):
                result = ingestion_manager.full_ingestion(show_progress=False)
                if result['status'] == 'success':
                    st.sidebar.success("✅ Data refreshed!")
                else:
                    st.sidebar.error("❌ Refresh failed!")
        finally:
            # Reset processing flag
            st.session_state.processing_in_progress = False
        
        st.rerun()
    
    # Special button for reprocessing with Vision API
    has_google_vision = os.path.exists('key.json')
    ai_provider = os.getenv('AI_PROVIDER', 'openai').lower()
    
    # Check if current AI provider supports vision
    has_ai_vision = False
    if ai_provider == 'gemini':
        has_ai_vision = True  # Most Gemini models support vision
    elif ai_provider == 'openai':
        current_model = os.getenv('OPENAI_MODEL', '')
        has_ai_vision = 'gpt-4' in current_model or 'gpt-4o' in current_model
    
    has_vision_capability = has_google_vision or has_ai_vision
    
    if has_vision_capability:
        # Disable button if processing is in progress
        button_disabled = st.session_state.processing_in_progress
        button_label = "⏳ Processing..." if button_disabled else "🔬 Reprocess Images with AI Vision"
        
        if st.sidebar.button(button_label, disabled=button_disabled):
            # Set processing flag to prevent duplicate operations
            st.session_state.processing_in_progress = True
            
            try:
                with st.spinner("🔬 Reprocessing all images with AI vision analysis..."):
                    # This will clear all data and reprocess everything with current vision settings
                    result = ingestion_manager.force_reprocess_all()
                    if result['status'] == 'success':
                        st.sidebar.success(f"✅ Reprocessed {result.get('total_images', 0)} images with AI vision analysis!")
                        st.sidebar.info("💡 Images now have detailed medical analysis. Try asking about scan results!")
                    else:
                        st.sidebar.error("❌ Reprocessing failed!")
            finally:
                # Reset processing flag
                st.session_state.processing_in_progress = False
            
            st.rerun()
        
        if not button_disabled:
            st.sidebar.caption("💡 Reprocess to enable AI vision analysis on medical images")
        else:
            st.sidebar.caption("⏳ Processing in progress... Please wait")
    
    if st.sidebar.button("📊 System Summary"):
        summary = ingestion_manager.get_ingestion_summary()
        st.sidebar.json(summary)
    
    if st.sidebar.button("📁 Folder Structure"):
        structure_info = ingestion_manager.get_folder_structure_info()
        st.sidebar.markdown("**📂 Dataset Structure:**")
        st.sidebar.write(f"Total folders: {structure_info['total_folders']}")
        if structure_info['patient_folders']:
            st.sidebar.markdown("**👤 Patient Folders Found:**")
            for folder in structure_info['patient_folders'][:5]:
                st.sidebar.write(f"• {folder}")
        st.sidebar.markdown("**📄 File Types:**")
        for ext, count in structure_info['file_types'].items():
            st.sidebar.write(f"• {ext}: {count} files")
    
    # Enhanced System Status with modern metrics
    st.sidebar.markdown("## 📊 System Status")
    
    # Create metric columns for better layout
    metric_cols = st.sidebar.columns(2, gap="small")
    
    with metric_cols[0]:
        st.metric(
            label="👥 Patients", 
            value=stats['total_patients'],
            delta=None
        )
        st.metric(
            label="📄 Documents", 
            value=stats['total_documents'],
            delta=None
        )
    
    with metric_cols[1]:
        st.metric(
            label="🖼️ Images", 
            value=stats['total_images'],
            delta=None
        )
        st.metric(
            label="✅ Processed", 
            value=stats['processed_files'],
            delta=None
        )
    
    # Enhanced status card
    st.sidebar.markdown(f"""
    <div class="stat-card">
        <strong>🚀 Performance:</strong><br>
        {'🟢 Optimal' if stats['total_patients'] > 0 else '🟡 Initializing'}<br>
        <strong>💾 Data Quality:</strong><br>
        {'🟢 Good' if stats['processed_files'] > 0 else '🔴 No Data'}
    </div>
    """, unsafe_allow_html=True)
    
    # Enhanced AI Models section
    st.sidebar.markdown("## 🤖 AI Models")
    
    # Use columns for AI model info
    ai_cols = st.sidebar.columns(1)
    with ai_cols[0]:
        # Get current AI provider configuration
        ai_provider = os.getenv('AI_PROVIDER', 'openai').lower()
        
        if ai_provider == 'gemini':
            model = os.getenv('GEMINI_MODEL', 'gemini-1.5-flash')
            provider_emoji = "🧠"
            provider_name = "Gemini"
        else:  # OpenAI
            model = os.getenv('OPENAI_MODEL', 'gpt-3.5-turbo')
            provider_emoji = "🤖"
            provider_name = "OpenAI"
        
        # Determine vision capabilities
        has_google_vision = os.path.exists('key.json')
        has_ai_vision = False
        
        if ai_provider == 'gemini':
            has_ai_vision = True  # Most Gemini models support vision
        elif ai_provider == 'openai':
            has_ai_vision = 'gpt-4' in model or 'gpt-4o' in model
        
        if has_google_vision and has_ai_vision:
            vision_status = f'🚀 Dual Vision (Google + {provider_name})'
        elif has_google_vision:
            vision_status = '✅ Google Vision API'
        elif has_ai_vision:
            vision_status = f'✅ {provider_name} Vision'
        else:
            vision_status = '❌ No Vision Analysis'
        
        st.sidebar.markdown(f"""
        <div class="stat-card">
            <strong>{provider_emoji} {provider_name}:</strong> {model}<br>
            <strong>👁️ Image Analysis:</strong> {vision_status}<br>
            <strong>⚡ Streamlit:</strong> v{st.__version__}
        </div>
        """, unsafe_allow_html=True)
        
        # Add helpful tips based on current configuration
        if not has_google_vision and not has_ai_vision:
            st.sidebar.warning(f"⚠️ **No image analysis available**\n\nTo enable medical image analysis:\n1. Add `key.json` for Google Vision\n2. Or use a vision-capable model with {provider_name}")
        elif not has_google_vision and has_ai_vision:
            st.sidebar.info(f"💡 **Using {provider_name} Vision**\n\nFor text extraction from medical reports, consider adding Google Vision API (`key.json`)")
        elif has_google_vision and has_ai_vision:
            st.sidebar.success(f"🎯 **Optimal Setup**\n\nBoth Google Vision (text) and {provider_name} Vision (analysis) are available")
    


def render_chat_interface(chat_assistant, db_manager):
    """Render the clean chat interface"""
    st.markdown('<div class="main-content">', unsafe_allow_html=True)
    
    # Display current context if available
    if st.session_state.current_patient:
        st.info(f"🔍 Currently focused on patient: **{st.session_state.current_patient}**")
    
    # Show debug mode status if enabled
    if st.session_state.debug_mode:
        st.warning("🐛 **Debug Mode Enabled** - API requests will be shown below responses")
    
    # Clear chat button at the top
#    col1, col2, col3 = st.columns([1, 1, 6])
#    with col1:
#        if st.button("🗑️ Clear Chat", use_container_width=True):
#            st.session_state.chat_history = []
#            st.rerun()
#    with col2:
#        if st.button("🔄 Refresh", use_container_width=True):
#            st.rerun()
    
    # Helper function to display debug info
    def display_debug_info(debug_info):
        """Display debug information in an accordion"""
        if not st.session_state.debug_mode or not debug_info:
            return
        
        with st.expander("🐛 API Request Details", expanded=False):
            st.json(debug_info)
    
    # Show suggestion buttons right below input when no history exists
    if not st.session_state.chat_history:
        st.markdown("#### 💡 Try asking questions like:")
        
        suggestions = [
            {"text": "What's the most common disease?", "icon": "🦠"},
            {"text": "How many patients are in the database?", "icon": "👥"}, 
            {"text": "What diseases are found in the majority of patients?", "icon": "📊"},
            {"text": "Show me patients with heart conditions", "icon": "❤️"},
            {"text": "What are the most frequent diagnoses?", "icon": "🏥"},
            {"text": "Analyze the patient demographics", "icon": "📈"}
        ]
        
        # Use improved grid layout with controlled gaps
        cols = st.columns(2, gap="medium")
        for i, suggestion in enumerate(suggestions):
            with cols[i % 2]:
                if st.button(
                    f"{suggestion['icon']} {suggestion['text']}", 
                    key=f"suggestion_{i}", 
                    use_container_width=True,
                    type="secondary"
                ):
                    process_query(suggestion['text'], chat_assistant)
                    st.rerun()
    
#    st.markdown("---")
#    st.markdown("### 📝 Conversation History")
    
    # Show older chat history if exists
    if len(st.session_state.chat_history) > 1:
        st.markdown("### 📜 Previous Conversations")
        # Show all conversations except the most recent one
        for i, history_item in enumerate(reversed(st.session_state.chat_history[:-1])):
            # Handle both old format (3 items) and new format (4 items)
            if len(history_item) == 4:
                query_item, response_item, timestamp_item, debug_info = history_item
            else:
                query_item, response_item, timestamp_item = history_item
                debug_info = {}
            
            # Add visual separator for conversations
            if i > 0:
                st.markdown("---")
            
            # Show the question first
            st.markdown(f"""
            <div class="chat-message user-message">
                <strong>👤 You ({timestamp_item}):</strong><br>
                {query_item}
            </div>
            """, unsafe_allow_html=True)
            
            # Show the response immediately below
            st.markdown(f"""
            <div class="chat-message assistant-message">
                <strong>🤖 Assistant:</strong><br>
                {response_item}
            </div>
            """, unsafe_allow_html=True)
            
            # Show debug info if available
            display_debug_info(debug_info)
        
        st.markdown("---")
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Show the latest conversation right above the input (if exists)
    if st.session_state.chat_history:
        # Handle both old format (3 items) and new format (4 items)
        latest_item = st.session_state.chat_history[-1]
        if len(latest_item) == 4:
            latest_query, latest_response, latest_timestamp, latest_debug_info = latest_item
        else:
            latest_query, latest_response, latest_timestamp = latest_item
            latest_debug_info = {}
        
#        st.markdown("### 💬 Latest Conversation")
        
        # Show the latest question
        st.markdown(f"""
        <div class="chat-message user-message">
            <strong>👤 You ({latest_timestamp}):</strong><br>
            {latest_query}
        </div>
        """, unsafe_allow_html=True)
        
        # Show the latest response
        st.markdown(f"""
        <div class="chat-message assistant-message">
            <strong>🤖 Assistant:</strong><br>
            {latest_response}
        </div>
        """, unsafe_allow_html=True)
        
        # Show debug info if available
        display_debug_info(latest_debug_info)
        
        st.markdown("---")
    
    # Add the chat input at the bottom (where it naturally goes)
    query = st.chat_input(
        placeholder="Ask about diseases, patients, diagnoses, or any medical patterns...",
        max_chars=2000
    )
    
    # Process query when submitted
    if query and query.strip():
        process_query(query.strip(), chat_assistant)
        st.rerun()

def process_query(query: str, chat_assistant: ChatAssistant):
    """Process user query and add to chat history"""
    with st.spinner("🤔 Analyzing patient data..."):
        result = chat_assistant.generate_response(
            query, 
            st.session_state.session_id, 
            debug_mode=st.session_state.debug_mode
        )
    
    if result['status'] == 'success':
        response = result['response']
        debug_info = result.get('debug_info', {})
        
        # Always sync the ChatAssistant's current context with the UI session state
        chat_context = chat_assistant.get_current_patient_context()
        if chat_context['has_context']:
            # Update session state to match ChatAssistant's internal context
            if st.session_state.current_patient != chat_context['patient_name']:
                st.session_state.current_patient = chat_context['patient_name']
                st.info(f"🔄 Context synchronized to patient: **{chat_context['patient_name']}**")
        else:
            # Clear session state if ChatAssistant has no context
            if st.session_state.current_patient:
                st.session_state.current_patient = None
                st.info("🔄 Patient context cleared")
        
        # Also check if patient context was automatically set (legacy check)
        if result.get('auto_context_set', False) and result.get('patient_context'):
            # Update session state to reflect the new patient context
            st.session_state.current_patient = result['patient_context']
            st.info(f"🔄 Automatically switched to patient: **{result['patient_context']}**")
        
        # Add to chat history (now including debug info)
        timestamp = datetime.now().strftime("%H:%M:%S")
        st.session_state.chat_history.append((query, response, timestamp, debug_info))
        
        # Show context info as a toast
        if result['has_context']:
            if result['patient_context']:
                st.success(f"✅ Response based on data for patient: {result['patient_context']}")
            else:
                st.success("✅ Response based on analysis of all patient records")
        else:
            st.warning("⚠️ Limited patient data available for this query")
    
    else:
        # Add error to chat history too
        timestamp = datetime.now().strftime("%H:%M:%S")
        error_response = f"❌ Error: {result['response']}"
        debug_info = result.get('debug_info', {})
        st.session_state.chat_history.append((query, error_response, timestamp, debug_info))
        st.error(error_response)

def main():
    """Main application function"""
    initialize_session_state()
    
    # Initialize system components
    if not st.session_state.system_initialized:
        try:
            db_manager, document_processor, ingestion_manager, chat_assistant = initialize_system()
            
            # Store components in session state
            st.session_state.db_manager = db_manager
            st.session_state.document_processor = document_processor
            st.session_state.ingestion_manager = ingestion_manager
            st.session_state.chat_assistant = chat_assistant
            st.session_state.system_initialized = True
            
            # Run initial ingestion
            run_initial_ingestion(ingestion_manager)
        except Exception as e:
            st.error(f"❌ Failed to initialize system: {str(e)}")
            st.stop()
    
    # Get components from session state
    db_manager = st.session_state.get('db_manager')
    document_processor = st.session_state.get('document_processor')
    ingestion_manager = st.session_state.get('ingestion_manager')
    chat_assistant = st.session_state.get('chat_assistant')
    
    if not all([db_manager, document_processor, ingestion_manager, chat_assistant]):
        st.error("❌ System components not properly initialized. Please refresh the page.")
        st.stop()
    
    # Layout
    render_sidebar(db_manager, ingestion_manager, chat_assistant)
    
    # Main content area
    render_chat_interface(chat_assistant, db_manager)
    


if __name__ == "__main__":
    main() 