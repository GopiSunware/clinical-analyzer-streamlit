import json
import os
from fuzzywuzzy import fuzz
from typing import List, Dict, Any, Optional
from .database_manager import DatabaseManager
from .ai_client import UnifiedAIClient
from .claude_subagent import ClaudeSubagentClient, SubagentResult

class ChatAssistant:
    def __init__(self, ai_provider: str = "openai", api_key: str = None, model: str = None, 
                 database_manager: DatabaseManager = None, 
                 temperature: float = None, max_tokens: int = None, **kwargs):
        """Initialize the chat assistant with unified AI client"""
        
        normalized_provider = ai_provider.lower()
        self.ai_provider = normalized_provider
        
        # Set temperature and max_tokens from parameters or environment variables
        self.temperature = temperature if temperature is not None else float(os.getenv('TEMPERATURE', '0.3'))
        self.max_tokens = max_tokens if max_tokens is not None else int(os.getenv('MAX_TOKENS', '2000'))
        
        self.subagent_client: Optional[ClaudeSubagentClient] = None
        self.ai_client: Optional[UnifiedAIClient] = None
        
        if normalized_provider == "claude_subagent":
            # Claude sub-agent mode uses the local CLI, no API client required
            self.model = "claude-subagent"
            self.subagent_client = ClaudeSubagentClient()
        else:
            # Set defaults based on API provider
            if normalized_provider == "gemini":
                default_model = model or "gemini-1.5-flash"
                api_key = api_key or os.getenv('GEMINI_API_KEY')
            else:  # OpenAI (default)
                default_model = model or "gpt-3.5-turbo"
                api_key = api_key or os.getenv('OPENAI_API_KEY')
            
            try:
                self.ai_client = UnifiedAIClient(
                    provider=normalized_provider,
                    api_key=api_key,
                    model=default_model,
                    temperature=self.temperature,
                    max_tokens=self.max_tokens,
                    **kwargs
                )
                self.model = default_model
            except Exception as e:
                print(f"Error initializing AI client: {e}")
                raise
        
        self.db = database_manager
        self.current_patient_context = None
        
        print(f"ChatAssistant initialized with provider: {self.ai_provider}, model: {self.model}, temperature: {self.temperature}, max_tokens: {self.max_tokens}")
        
    def set_patient_context(self, patient_name: str = None, patient_id: str = None):
        """Set the current patient context for the conversation"""
        if patient_name or patient_id:
            patient_data = self.db.get_patient_data(patient_name=patient_name, patient_id=patient_id)
            if patient_data:
                self.current_patient_context = patient_data
                return f"Context set to patient: {patient_data['patient_info']['name']}"
            else:
                self.current_patient_context = None
                return f"Patient not found: {patient_name or patient_id}"
        else:
            self.current_patient_context = None
            return "Patient context cleared"
    
    def clear_patient_context(self):
        """Clear the current patient context"""
        self.current_patient_context = None
        return "Patient context cleared"
    
    def get_current_patient_context(self):
        """Get information about the current patient context"""
        if self.current_patient_context:
            patient_info = self.current_patient_context['patient_info']
            return {
                'has_context': True,
                'patient_name': patient_info['name'],
                'patient_id': patient_info.get('patient_id', 'N/A'),
                'context_message': f"Current patient context: {patient_info['name']} (ID: {patient_info.get('patient_id', 'N/A')})"
            }
        else:
            return {
                'has_context': False,
                'patient_name': None,
                'patient_id': None,
                'context_message': "No patient context is currently set"
            }
    
    def format_patient_data_for_context(self, patient_data: Dict) -> str:
        """Format patient data for use in AI prompts"""
        if not patient_data:
            return "No patient data available"
        
        patient_name = patient_data['patient_info']['name']
        patient_id = patient_data['patient_info'].get('patient_id', 'N/A')
        
        context = f"""
PATIENT INFORMATION:
Name: {patient_name}
Patient ID: {patient_id}
Records Created: {patient_data['patient_info']['created_at']}

MEDICAL DOCUMENTS ({len(patient_data['documents'])} total):
"""
        
        # Add document summaries
        for i, doc in enumerate(patient_data['documents'][:10], 1):  # Limit to first 10 docs
            context += f"\nDocument {i} ({doc['file_name']}):\n"
            # Use processed content if available, otherwise original content
            content = doc.get('processed_content') or doc['content']
            context += content[:1000] + "...\n" if len(content) > 1000 else content + "\n"
        
        if len(patient_data['documents']) > 10:
            context += f"\n... and {len(patient_data['documents']) - 10} more documents\n"
        
        # Add image transcriptions with emphasis on patient connection
        if patient_data['images']:
            context += f"\nMEDICAL IMAGING RESULTS FOR {patient_name} ({len(patient_data['images'])} total):\n"
            context += "=" * 50 + "\n"
            for i, img in enumerate(patient_data['images'][:5], 1):  # Limit to first 5 images
                context += f"\nIMAGE {i}: {img['category']} - {img['file_name']}\n"
                context += f"Patient: {patient_name} (ID: {patient_id})\n"
                context += "-" * 30 + "\n"
                transcription = img['transcription']
                if len(transcription) > 800:
                    context += transcription[:800] + "...\n"
                else:
                    context += transcription + "\n"
                context += "-" * 30 + "\n"
            
            if len(patient_data['images']) > 5:
                context += f"\n... and {len(patient_data['images']) - 5} more images for {patient_name}\n"
        else:
            context += f"\nNo medical imaging results found for {patient_name}.\n"
        
        return context

    def _collect_sources_from_patient(self, patient_data: Dict) -> List[str]:
        """Collect filesystem paths for documents and images tied to a patient."""
        sources: List[str] = []
        for doc in patient_data.get('documents', []):
            source = doc.get('metadata', {}).get('source') or doc.get('file_path')
            if source and source not in sources:
                sources.append(source)
        for img in patient_data.get('images', []):
            meta = img.get('metadata', {}) if isinstance(img, dict) else {}
            source = meta.get('source') or img.get('file_path') or img.get('image_path')
            if source and source not in sources:
                sources.append(source)
        return sources

    def search_and_prepare_context_with_sources(self, query: str) -> Dict[str, Any]:
        """Search for relevant patients and return context string plus file sources."""
        sources: List[str] = []

        if self.is_database_stats_query(query):
            return {
                'context': self.prepare_database_stats_context(),
                'sources': sources
            }

        patient_mentioned = self.extract_patient_from_query(query)

        if patient_mentioned:
            patient_value = patient_mentioned['value']
            search_results = self.db.search_patients(patient_value)
            if search_results:
                patient_data = self.db.get_patient_data(patient_name=search_results[0]['name'])
                sources.extend(self._collect_sources_from_patient(patient_data))
                return {
                    'context': self.format_patient_data_for_context(patient_data),
                    'sources': sources
                }

        search_results = self.db.search_patients(query)

        if search_results:
            context_parts = ["RELEVANT PATIENTS AND INFORMATION:\n"]
            for patient in search_results[:5]:
                patient_data = self.db.get_patient_data(patient_name=patient['name'])
                context_parts.append(f"--- PATIENT: {patient['name']} ---")
                context_parts.append(self.format_patient_data_for_context(patient_data))
                context_parts.append("\n" + "=" * 50 + "\n")
                sources.extend(self._collect_sources_from_patient(patient_data))
            return {
                'context': "\n".join(context_parts),
                'sources': sources
            }

        return {
            'context': self.prepare_database_stats_context(),
            'sources': sources
        }

    def search_and_prepare_context(self, query: str) -> str:
        result = self.search_and_prepare_context_with_sources(query)
        return result['context']
    
    def extract_patient_id_from_query(self, query: str) -> Optional[str]:
        """Extract patient ID from query using pattern matching"""
        import re
        
        # Patient ID patterns - looking for format like M0001, M0123, etc.
        id_patterns = [
            r"\b([Mm]\d{4})\b",  # M0001, m0001
            r"patient\s+id\s*:?\s*([Mm]\d{4})",  # "patient id: M0001" or "patient ID M0001"
            r"id\s*:?\s*([Mm]\d{4})",  # "id: M0001" or "ID M0001"
            r"patient\s+([Mm]\d{4})",  # "patient M0001"
        ]
        
        for pattern in id_patterns:
            matches = re.findall(pattern, query, re.IGNORECASE)
            if matches:
                # Extract the first valid patient ID found
                for match in matches:
                    # Handle both string matches and group matches
                    if isinstance(match, str) and re.match(r'^[Mm]\d{4}$', match):
                        return match.upper()  # Normalize to uppercase
        
        return None

    def extract_patient_from_query(self, query: str) -> Optional[dict]:
        """Extract patient name or ID from query using enhanced pattern matching and fuzzy name matching"""
        
        # First try to extract patient ID
        patient_id = self.extract_patient_id_from_query(query)
        if patient_id:
            return {'type': 'id', 'value': patient_id}
        
        # Then try to extract patient name
        query_lower = query.lower()
        
        # Enhanced patterns for patient queries
        patterns = [
            "patient ",
            "what did ",
            "about ",
            "for ",
            "diagnosis for ",
            "treatment for ",
            "results for ",
            "data for ",
            "information on ",
            "info on ",
            "report on ",
            "record of ",
            "records for ",
            "history of ",
            "condition of ",
            "status of ",
            "case of ",
            " with ",  # e.g., "John Smith with diabetes"
        ]
        
        # Look for patient names after these patterns
        for pattern in patterns:
            if pattern in query_lower:
                # Try to extract the name after the pattern
                start_idx = query_lower.find(pattern) + len(pattern)
                remaining = query[start_idx:].strip()
                
                # Extract potential patient name (stop at common question words and medical terms)
                stop_words = [
                    'have', 'had', 'do', 'does', 'was', 'is', 'what', 'when', 'where', 'how', 'why', '?',
                    'and', 'or', 'but', 'with', 'without', 'the', 'a', 'an', 'his', 'her', 'their',
                    'diabetes', 'cancer', 'heart', 'disease', 'condition', 'diagnosis', 'treatment',
                    'medication', 'surgery', 'test', 'scan', 'mri', 'ct', 'xray', 'blood',
                    # Add pronouns to prevent them from being treated as patient names
                    'him', 'her', 'them', 'they', 'he', 'she', 'it', 'this', 'that', 'these', 'those',
                    'patient', 'person', 'individual', 'case', 'subject'
                ]
                words = remaining.split()
                
                name_words = []
                for word in words:
                    # Clean up punctuation from word for checking
                    clean_word = word.strip('.,?!').lower()
                    if clean_word in stop_words or len(clean_word) <= 1:
                        break
                    name_words.append(word)
                
                if name_words:
                    extracted_name = ' '.join(name_words).strip('.,?!')
                    
                    # Filter out pronouns and common non-name words
                    pronouns = ['him', 'her', 'them', 'they', 'he', 'she', 'it', 'this', 'that', 'these', 'those']
                    if extracted_name.lower() not in pronouns:
                        # Limit to reasonable name length (2-4 words typically)
                        if len(name_words) <= 4:
                            # After extracting the name, match it with names in the database
                            return self.get_most_similar_patient_from_db(extracted_name, query)
        
        # Also try to match direct questions with patient names at the beginning
        # e.g., "John Smith's diagnosis", "Mary Johnson condition"
        import re
        
        # Pattern for possessive or direct name references (anywhere in query)
        name_patterns = [
            r"([A-Z][a-z]+ [A-Z][a-z]+)'s\s",  # "John Smith's"
            r"([A-Z][a-z]+ [A-Z][a-z]+)'\s",   # "John Smith' " (without s)
            r"([A-Z][a-z]+ [A-Z]\. [A-Z][a-z]+)'s?\s",  # "John A. Smith's" or "John A. Smith'"
            r"\b([A-Z][a-z]+ [A-Z][a-z]+)\s+(medical|history|record|condition|diagnosis|treatment)",  # "John Smith medical history"
        ]
        
        for pattern in name_patterns:
            match = re.search(pattern, query)
            if match:
                potential_name = match.group(1).strip()
                # Filter out pronouns
                pronouns = ['him', 'her', 'them', 'they', 'he', 'she', 'it', 'this', 'that', 'these', 'those']
                if potential_name.lower() not in pronouns:
                    # After extracting the name, match it with names in the database
                    return self.get_most_similar_patient_from_db(potential_name, query)
        
        return None
    
    def get_most_similar_patient_from_db(self, extracted_name: str, query: str) -> dict:
        """Find the most similar patient name from the database using fuzzy matching and context"""
        
        # Fetch all patient names from the database
        patients = self.db.get_all_patients()
        
        # Find the patient with the highest similarity score
        highest_score = 0
        most_similar_patient = None
        
        for patient in patients:
            patient_name = patient['name']
            score = fuzz.ratio(extracted_name.lower(), patient_name.lower())  # Compare lowercased names
            
            if score > highest_score:
                highest_score = score
                most_similar_patient = patient
        
        # If the similarity score is sufficiently high (e.g., > 85%), return the most similar patient
        return {'type': 'name', 'value': most_similar_patient['name']}
    
    def is_database_stats_query(self, query: str) -> bool:
        """Check if query is asking for database statistics or analysis across all patients"""
        query_lower = query.lower()
        stats_keywords = [
            # General database queries
            'how many patients', 'patient count', 'total patients', 'number of patients',
            'database stats', 'statistics', 'how many', 'count', 'total', 'summary',
            'overview', 'all patients', 'patient list',
            
            # Disease and condition analysis queries
            'common disease', 'most common', 'frequent disease', 'majority', 'prevalent',
            'what disease', 'which disease', 'disease found', 'diagnosis found',
            'conditions found', 'most frequent', 'common condition', 'popular disease',
            'disease pattern', 'health trend', 'medical trend', 'diagnosis trend',
            
            # Analysis queries
            'analyze', 'analysis', 'trend', 'pattern', 'distribution', 'breakdown',
            'what are the', 'show me all', 'list all', 'across all', 'in the database',
            'among patients', 'in patients', 'patient analysis'
        ]
        
        return any(keyword in query_lower for keyword in stats_keywords)
    
    def prepare_database_stats_context(self) -> str:
        """Prepare context with database statistics and comprehensive patient data for analysis"""
        stats = self.db.get_stats()
        all_patients = self.db.get_all_patients()
        
        context = f"""
DATABASE STATISTICS:
- Total Patients: {stats['total_patients']}
- Total Documents: {stats['total_documents']} 
- Total Images: {stats['total_images']}
- Processed Files: {stats['processed_files']}

COMPREHENSIVE PATIENT DATA FOR ANALYSIS:
"""
        
        # Get detailed patient data for analysis
        patient_summaries = []
        for patient in all_patients:
            patient_data = self.db.get_patient_data(patient_name=patient['name'])
            if patient_data and patient_data['documents']:
                # Extract key medical information from each patient
                for doc in patient_data['documents']:
                    content = doc.get('processed_content') or doc['content']
                    patient_summaries.append(f"""
Patient: {patient['name']} (ID: {patient.get('patient_id', 'N/A')})
Medical Data: {content[:800]}{'...' if len(content) > 800 else ''}
""")
        
        # Add patient summaries (limit to prevent token overflow)
        context += "\n".join(patient_summaries[:50])  # Limit to 50 patients for analysis
        
        if len(patient_summaries) > 50:
            context += f"\n... and {len(patient_summaries) - 50} more patients with similar detailed records\n"
        
        # Add analytics summary
        if stats['total_patients'] > 0:
            avg_docs = stats['total_documents'] / stats['total_patients']
            avg_images = stats['total_images'] / stats['total_patients']
            context += f"\nDATABASE ANALYTICS:\n"
            context += f"- Average Documents per Patient: {avg_docs:.1f}\n"
            context += f"- Average Images per Patient: {avg_images:.1f}\n"
            context += f"- Total Clinical Records Available: {len(patient_summaries)}\n"
        
        return context
    
    def generate_response(self, query: str, session_id: str = None, debug_mode: bool = False) -> Dict[str, Any]:
        """Generate AI response to user query"""
        # Initialize patient_context so it's always available in exception handler
        patient_context = None
        debug_info = {}
        
        try:
            # First, check if query mentions a specific patient
            mentioned_patient = self.extract_patient_from_query(query)
            
            # If a patient is mentioned and we don't have context for them, set it automatically
            if mentioned_patient:
                patient_type = mentioned_patient['type']
                patient_value = mentioned_patient['value']
                
                # Check current context to see if we need to switch
                needs_context_switch = True
                if self.current_patient_context:
                    current_patient_name = self.current_patient_context['patient_info']['name']
                    current_patient_id = self.current_patient_context['patient_info'].get('patient_id')
                    
                    if patient_type == 'name' and current_patient_name and current_patient_name.lower() == patient_value.lower():
                        needs_context_switch = False
                    elif patient_type == 'id' and current_patient_id and current_patient_id.upper() == patient_value.upper():
                        needs_context_switch = False
                
                if needs_context_switch:
                    # Try to set context for the mentioned patient
                    if patient_type == 'name':
                        self.set_patient_context(patient_name=patient_value)
                    elif patient_type == 'id':
                        self.set_patient_context(patient_id=patient_value)
            
            # Prepare context
            context_sources: List[str] = []
            if self.current_patient_context:
                # Use current patient context - maintain context for follow-up questions
                context = self.format_patient_data_for_context(self.current_patient_context)
                patient_context = self.current_patient_context['patient_info']['name']
                context_sources = self._collect_sources_from_patient(self.current_patient_context)
            else:
                # Only search for new context if no patient context is set
                context_bundle = self.search_and_prepare_context_with_sources(query)
                context = context_bundle['context']
                context_sources = context_bundle['sources']
                patient_context = None
            
            # Build the prompt
            system_prompt = """
    You are a medical AI assistant helping doctors analyze patient records. You have access to patient medical data including documents, reports, and image transcriptions.

    Guidelines:
    1. Always provide accurate, helpful information based on the available data
    2. If information is not available in the provided context, clearly state that
    3. Highlight important medical findings, diagnoses, and treatment plans
    4. Be concise but comprehensive in your responses
    5. Use medical terminology appropriately but explain complex terms when helpful
    6. Always prioritize patient privacy and medical ethics
    7. If asked about multiple patients, provide comparative analysis when relevant
    8. Reference specific documents or images when citing information
    9. IMPORTANT: When patient context is set, focus only on that specific patient unless explicitly asked about others
    10. For follow-up questions (like "tell me more", "what else", etc.), continue discussing the same patient from the provided context

    Answer the user's question based on the provided patient data context.
    """
            
            # Build user prompt with clear patient context indication
            if self.current_patient_context:
                current_patient_name = self.current_patient_context['patient_info']['name']
                current_patient_id = self.current_patient_context['patient_info'].get('patient_id', 'N/A')
                user_prompt = f"""
    CURRENT PATIENT CONTEXT: {current_patient_name} (ID: {current_patient_id})
    This conversation is focused on this specific patient. All questions should be answered in relation to this patient unless explicitly stated otherwise.

    Patient Data Context:
    {context}

    User Question: {query}

    Please provide a comprehensive answer based on the available patient information for {current_patient_name}.
    """
            else:
                user_prompt = f"""
    Patient Data Context:
    {context}

    User Question: {query}

    Please provide a comprehensive answer based on the available patient information.
    """
            
            # Prepare messages for API call (used by API providers) and provide context for sub-agent mode
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]
            
            # Capture debug information if debug mode is enabled
            if debug_mode:
                debug_info = {
                    "api_request": {
                        "provider": self.ai_provider,
                        "model": self.model,
                        "messages": messages,
                        "temperature": self.temperature,
                        "max_tokens": self.max_tokens
                    },
                    "context_info": {
                        "has_patient_context": bool(self.current_patient_context),
                        "patient_name": patient_context,
                        "mentioned_patient": mentioned_patient,
                        "context_length_chars": len(context),
                        "system_prompt_length": len(system_prompt),
                        "user_prompt_length": len(user_prompt),
                        "context_sources": context_sources,
                    }
                }
            
            # Get AI response using unified client
            try:
                if self.ai_provider == "claude_subagent":
                    subagent_result = self.subagent_client.run_question(
                        question=query,
                        context_markdown=user_prompt,
                        context_sources=context_sources,
                        session_token=session_id,
                        patient_hint=patient_context
                    )
                    response_text = subagent_result.content

                    if debug_mode:
                        debug_info["subagent_response"] = {
                            "job_id": subagent_result.job_id,
                            "output_path": str(subagent_result.output_path),
                            "files_created": subagent_result.files_created,
                            "raw_message_preview": subagent_result.raw_message[:400]
                        }
                else:
                    ai_response = self.ai_client.generate_text(
                        messages=messages,
                        temperature=self.temperature,
                        max_tokens=self.max_tokens
                    )
                    
                    # Add response details to debug info
                    if debug_mode:
                        debug_info["api_response"] = {
                            "completion_tokens": ai_response['usage'].get('completion_tokens'),
                            "prompt_tokens": ai_response['usage'].get('prompt_tokens'),
                            "total_tokens": ai_response['usage'].get('total_tokens'),
                            "model": ai_response.get('model', self.model),
                            "finish_reason": ai_response.get('finish_reason')
                        }
                    
                    response_text = ai_response['content']
                
            except Exception as e:
                print(f"Error generating AI response: {e}")
                response_text = f"I apologize, but I encountered an error processing your request: {str(e)}"
                
                if debug_mode:
                    debug_info["error"] = str(e)
            
            # Save to chat history if session_id provided
            if session_id and self.db:
                self.db.add_chat_message(session_id, query, response_text, patient_context)
            
            return {
                'status': 'success',
                'response': response_text,
                'patient_context': patient_context,
                'has_context': bool(context and context != "No relevant patient information found for this query."),
                'auto_context_set': bool(mentioned_patient and self.current_patient_context),
                'debug_info': debug_info if debug_mode else {}
            }
            
        except Exception as e:
            error_message = f"Error generating response: {str(e)}"
            
            # Add error details to debug info
            if debug_mode:
                debug_info["error"] = {
                    "error_type": type(e).__name__,
                    "error_message": str(e),
                    "patient_context": patient_context
                }
            
            # Save error to chat history if session_id provided
            if session_id and self.db:
                self.db.add_chat_message(session_id, query, error_message, patient_context)
            
            return {
                'status': 'error',
                'response': error_message,
                'patient_context': patient_context,
                'has_context': False,
                'auto_context_set': False,
                'debug_info': debug_info if debug_mode else {}
            }
    
    def get_suggested_questions(self, patient_name: str = None) -> List[str]:
        """Get suggested questions based on patient data or general questions"""
        if patient_name and self.db:
            patient_data = self.db.get_patient_data(patient_name=patient_name)
            if patient_data:
                suggestions = [
                    f"What is the diagnosis for {patient_name}?",
                    f"What treatments has {patient_name} received?",
                    f"What are the recent test results for {patient_name}?",
                    f"What medications is {patient_name} taking?",
                    f"What is the medical history of {patient_name}?",
                ]
                
                # Add specific suggestions based on available data
                if patient_data['images']:
                    suggestions.append(f"What do the medical images show for {patient_name}?")
                
                return suggestions
        
        # General suggestions
        return [
            "How many patients are in the database?",
            "What are the most common diagnoses?",
            "Show me patients with cardiovascular conditions",
            "What imaging studies have been performed?",
            "Which patients need follow-up care?",
            "What are the recent test results across all patients?",
        ]
    
    def get_patient_summary(self, patient_name: str = None, patient_id: str = None) -> Dict[str, Any]:
        """Get a comprehensive AI-generated summary of a patient"""
        patient_data = self.db.get_patient_data(patient_name=patient_name, patient_id=patient_id)
        
        if not patient_data:
            return {
                'status': 'error',
                'message': 'Patient not found'
            }
        
        try:
            context = self.format_patient_data_for_context(patient_data)
            
            prompt = f"""
Based on the following patient data, provide a comprehensive medical summary including:

1. Patient Demographics
2. Key Medical Conditions/Diagnoses
3. Treatment History
4. Current Status
5. Risk Factors
6. Recommendations for Further Care

Patient Data:
{context}

Format the response in clear sections with bullet points where appropriate.
"""
            
            # Generate summary using unified AI client
            ai_response = self.ai_client.generate_text(
                messages=[{"role": "user", "content": prompt}],
                temperature=self.temperature * 0.67,  # Slightly lower temperature for summaries
                max_tokens=min(self.max_tokens, 1500)  # Cap at 1500 for summaries
            )
            
            return {
                'status': 'success',
                'summary': ai_response['content'],
                'patient_info': patient_data['patient_info']
            }
            
        except Exception as e:
            return {
                'status': 'error',
                'message': f"Error generating summary: {str(e)}"
            }
    
    def analyze_patient_trends(self, query: str = None) -> Dict[str, Any]:
        """Analyze trends across all patients"""
        try:
            # Get database statistics
            stats = self.db.get_stats()
            all_patients = self.db.get_all_patients()
            
            # Prepare data for analysis
            context = f"""
DATABASE STATISTICS:
- Total Patients: {stats['total_patients']}
- Total Documents: {stats['total_documents']}
- Total Images: {stats['total_images']}

PATIENT LIST:
"""
            
            for patient in all_patients[:20]:  # Limit to prevent token overflow
                context += f"- {patient['name']} (ID: {patient.get('patient_id', 'N/A')}) - {patient['doc_count']} docs, {patient['image_count']} images\n"
            
            if len(all_patients) > 20:
                context += f"... and {len(all_patients) - 20} more patients\n"
            
            analysis_prompt = f"""
Analyze the following clinical database and provide insights about:

1. Patient Demographics and Distribution
2. Common Medical Conditions or Patterns
3. Data Quality and Completeness
4. Recommendations for Clinical Care

Database Information:
{context}

Specific Analysis Request: {query or "General overview"}

Provide a comprehensive analysis with actionable insights.
"""
            
            # Generate analysis using unified AI client
            ai_response = self.ai_client.generate_text(
                messages=[{"role": "user", "content": analysis_prompt}],
                temperature=self.temperature,
                max_tokens=self.max_tokens
            )
            
            return {
                'status': 'success',
                'analysis': ai_response['content'],
                'stats': stats
            }
            
        except Exception as e:
            return {
                'status': 'error',
                'message': f"Error analyzing trends: {str(e)}"
            } 
