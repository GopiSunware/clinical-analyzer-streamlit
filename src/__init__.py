# Clinical Document Analyzer Package
# This package contains modules for processing medical documents and images

from .database_manager import DatabaseManager
from .document_processor import DocumentProcessor
from .ingestion_manager import IngestionManager
from .chat_assistant import ChatAssistant
from .ai_client import UnifiedAIClient

__version__ = "1.0.0"
__author__ = "Clinical Document Analyzer Team"

__all__ = [
    "DatabaseManager",
    "DocumentProcessor", 
    "IngestionManager",
    "ChatAssistant",
    "UnifiedAIClient"
] 