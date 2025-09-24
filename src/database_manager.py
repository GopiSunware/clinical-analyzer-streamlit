import sqlite3
import hashlib
import os
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional
import json
from fuzzywuzzy import fuzz
import pandas as pd

class DatabaseManager:
    def __init__(self, db_path: str = "clinical_analyzer.db"):
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """Initialize the database with required tables"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Patients table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS patients (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    patient_name TEXT NOT NULL,
                    patient_id TEXT,
                    normalized_name TEXT NOT NULL,
                    normalized_id TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Documents table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS documents (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    patient_uuid INTEGER,
                    file_path TEXT NOT NULL,
                    file_name TEXT NOT NULL,
                    file_type TEXT NOT NULL,
                    file_hash TEXT NOT NULL UNIQUE,
                    content TEXT,
                    processed_content TEXT,
                    metadata TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (patient_uuid) REFERENCES patients (id)
                )
            ''')
            
            # Images table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS images (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    patient_uuid INTEGER,
                    file_path TEXT NOT NULL,
                    file_name TEXT NOT NULL,
                    file_hash TEXT NOT NULL UNIQUE,
                    transcription TEXT,
                    image_category TEXT,
                    metadata TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (patient_uuid) REFERENCES patients (id)
                )
            ''')
            
            # Chat sessions table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS chat_sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    message TEXT NOT NULL,
                    response TEXT NOT NULL,
                    patient_context TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # File processing status table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS file_status (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    file_path TEXT NOT NULL UNIQUE,
                    file_hash TEXT NOT NULL,
                    last_modified TIMESTAMP,
                    processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    status TEXT DEFAULT 'processed'
                )
            ''')
            
            # Create indexes for better performance
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_patients_name ON patients (normalized_name)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_patients_id ON patients (normalized_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_documents_patient ON documents (patient_uuid)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_images_patient ON images (patient_uuid)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_file_hash ON documents (file_hash)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_image_hash ON images (file_hash)')
            
            conn.commit()
    
    def normalize_text(self, text: str) -> str:
        """Normalize text for fuzzy matching"""
        if not text:
            return ""
        return text.lower().strip().replace(" ", "").replace("_", "").replace("-", "")
    
    def calculate_file_hash(self, file_path: str) -> str:
        """Calculate MD5 hash of file"""
        hash_md5 = hashlib.md5()
        try:
            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_md5.update(chunk)
        except Exception as e:
            print(f"Error calculating hash for {file_path}: {e}")
            return ""
        return hash_md5.hexdigest()
    
    def find_or_create_patient(self, patient_name: str, patient_id: str = None) -> int:
        """Find existing patient or create new one using fuzzy matching"""
        normalized_name = self.normalize_text(patient_name)
        normalized_id = self.normalize_text(patient_id) if patient_id else ""
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # First, try exact match
            cursor.execute(''' 
                SELECT id FROM patients 
                WHERE normalized_name = ? AND (normalized_id = ? OR normalized_id = '')
            ''', (normalized_name, normalized_id))
            
            result = cursor.fetchone()
            if result:
                # If exact match found, return the existing patient id
                return result[0]
            
            # If no exact match, try fuzzy matching to see if the patient is a close match
            cursor.execute('SELECT id, normalized_name, normalized_id FROM patients')
            patients = cursor.fetchall()
            
            for pid, p_name, p_id in patients:
                # Perform fuzzy matching for names
                name_similarity = fuzz.ratio(normalized_name, p_name)
                
                if name_similarity > 90:  # Increase the threshold for name matching
                    # If both IDs are present, match them as well
                    if normalized_id and p_id:
                        id_similarity = fuzz.ratio(normalized_id, p_id)
                        if id_similarity > 85:  # More strict ID matching
                            return pid
                    elif not normalized_id or not p_id:  # If one of the IDs is missing
                        return pid
            
            # If no match found, create a new patient
            cursor.execute('''
                INSERT INTO patients (patient_name, patient_id, normalized_name, normalized_id)
                VALUES (?, ?, ?, ?)
            ''', (patient_name, patient_id, normalized_name, normalized_id))
            
            return cursor.lastrowid
    
    def is_file_processed(self, file_path: str) -> bool:
        """Check if file has been processed and hasn't changed"""
        current_hash = self.calculate_file_hash(file_path)
        current_mtime = os.path.getmtime(file_path)
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT file_hash, last_modified FROM file_status 
                WHERE file_path = ?
            ''', (file_path,))
            
            result = cursor.fetchone()
            if result:
                stored_hash, stored_mtime = result
                return (stored_hash == current_hash and 
                       stored_mtime == current_mtime)
            
            return False
    
    def mark_file_processed(self, file_path: str):
        """Mark file as processed"""
        file_hash = self.calculate_file_hash(file_path)
        file_mtime = os.path.getmtime(file_path)
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR REPLACE INTO file_status (file_path, file_hash, last_modified)
                VALUES (?, ?, ?)
            ''', (file_path, file_hash, file_mtime))
            conn.commit()
    
    def add_document(self, patient_uuid: int, file_path: str, content: str, 
                    processed_content: str = None, metadata: Dict = None):
        """Add document to database"""
        # Handle virtual file paths (Excel rows) differently
        if '#row_' in file_path:
            # This is a virtual file path representing a row in an Excel file
            actual_file_path = file_path.split('#')[0]  # Get the actual Excel file path
            file_hash = self.calculate_file_hash(actual_file_path) + f"#{file_path.split('#')[1]}"  # Unique hash per row
        else:
            file_hash = self.calculate_file_hash(file_path)
        
        file_name = os.path.basename(file_path)
        file_type = Path(file_path).suffix.lower()
        
        metadata_json = json.dumps(metadata) if metadata else None
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            try:
                cursor.execute('''
                    INSERT INTO documents (
                        patient_uuid, file_path, file_name, file_type, 
                        file_hash, content, processed_content, metadata
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (patient_uuid, file_path, file_name, file_type, 
                      file_hash, content, processed_content, metadata_json))
                conn.commit()
                
                # Only mark actual files as processed, not virtual rows
                if '#row_' not in file_path:
                    self.mark_file_processed(file_path)
                
            except sqlite3.IntegrityError as e:
                if "UNIQUE constraint failed" in str(e):
                    # Document already exists, update it instead
                    cursor.execute('''
                        UPDATE documents 
                        SET content = ?, processed_content = ?, metadata = ?, 
                            updated_at = CURRENT_TIMESTAMP
                        WHERE file_hash = ?
                    ''', (content, processed_content, metadata_json, file_hash))
                    conn.commit()
                else:
                    raise e
    
    def add_image(self, patient_uuid: int, file_path: str, transcription: str, 
                 image_category: str = None, metadata: Dict = None):
        """Add image transcription to database"""
        file_hash = self.calculate_file_hash(file_path)
        file_name = os.path.basename(file_path)
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            try:
                cursor.execute('''
                    INSERT INTO images (patient_uuid, file_path, file_name, file_hash, 
                                      transcription, image_category, metadata)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (patient_uuid, file_path, file_name, file_hash, transcription, 
                     image_category, json.dumps(metadata or {})))
                conn.commit()
                self.mark_file_processed(file_path)
            except sqlite3.IntegrityError:
                # File already exists, update it
                cursor.execute('''
                    UPDATE images SET transcription = ?, image_category = ?, 
                                    metadata = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE file_hash = ?
                ''', (transcription, image_category, json.dumps(metadata or {}), file_hash))
                conn.commit()
    
    def get_patient_data(self, patient_name: str = None, patient_id: str = None) -> Dict:
        """Get all data for a specific patient"""
        if not patient_name and not patient_id:
            return {}
        
        # Find patient
        if patient_name:
            normalized_name = self.normalize_text(patient_name)
            condition = "normalized_name = ?"
            param = normalized_name
        else:
            normalized_id = self.normalize_text(patient_id)
            condition = "normalized_id = ?"
            param = normalized_id
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Get patient info
            cursor.execute(f'SELECT * FROM patients WHERE {condition}', (param,))
            patient = cursor.fetchone()
            
            if not patient:
                return {}
            
            patient_uuid = patient[0]
            
            # Get documents
            cursor.execute('''
                SELECT file_name, content, processed_content, metadata, created_at 
                FROM documents WHERE patient_uuid = ?
                ORDER BY created_at DESC
            ''', (patient_uuid,))
            documents = cursor.fetchall()
            
            # Get images
            cursor.execute('''
                SELECT file_name, transcription, image_category, metadata, created_at 
                FROM images WHERE patient_uuid = ?
                ORDER BY created_at DESC
            ''', (patient_uuid,))
            images = cursor.fetchall()
            
            return {
                'patient_info': {
                    'id': patient[0],
                    'name': patient[1],
                    'patient_id': patient[2],
                    'created_at': patient[5]
                },
                'documents': [{'file_name': doc[0], 'content': doc[1], 
                             'processed_content': doc[2], 'metadata': json.loads(doc[3] or '{}'),
                             'created_at': doc[4]} for doc in documents],
                'images': [{'file_name': img[0], 'transcription': img[1], 
                          'category': img[2], 'metadata': json.loads(img[3] or '{}'),
                          'created_at': img[4]} for img in images]
            }
    
    def get_all_patients(self) -> List[Dict]:
        """Get list of all patients"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT p.patient_name, p.patient_id, p.created_at,
                       COUNT(DISTINCT d.id) as doc_count,
                       COUNT(DISTINCT i.id) as image_count
                FROM patients p
                LEFT JOIN documents d ON p.id = d.patient_uuid
                LEFT JOIN images i ON p.id = i.patient_uuid
                GROUP BY p.id
                ORDER BY p.created_at DESC
            ''')
            
            patients = cursor.fetchall()
            return [{'name': p[0], 'patient_id': p[1], 'created_at': p[2],
                    'doc_count': p[3], 'image_count': p[4]} for p in patients]
    
    def get_stats(self) -> Dict:
        """Get database statistics"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            cursor.execute('SELECT COUNT(*) FROM patients')
            patient_count = cursor.fetchone()[0]
            
            cursor.execute('SELECT COUNT(*) FROM documents')
            doc_count = cursor.fetchone()[0]
            
            cursor.execute('SELECT COUNT(*) FROM images')
            image_count = cursor.fetchone()[0]
            
            cursor.execute('SELECT COUNT(*) FROM file_status WHERE status = "processed"')
            processed_files = cursor.fetchone()[0]
            
            return {
                'total_patients': patient_count,
                'total_documents': doc_count,
                'total_images': image_count,
                'processed_files': processed_files
            }
    
    def search_patients(self, query: str) -> List[Dict]:
        """Search patients by name or ID"""
        normalized_query = self.normalize_text(query)
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT DISTINCT p.patient_name, p.patient_id, p.created_at
                FROM patients p
                LEFT JOIN documents d ON p.id = d.patient_uuid
                LEFT JOIN images i ON p.id = i.patient_uuid
                WHERE p.normalized_name LIKE ? OR p.normalized_id LIKE ?
                   OR d.content LIKE ? OR i.transcription LIKE ?
                ORDER BY p.patient_name
            ''', (f'%{normalized_query}%', f'%{normalized_query}%', 
                  f'%{query}%', f'%{query}%'))
            
            results = cursor.fetchall()
            return [{'name': r[0], 'patient_id': r[1], 'created_at': r[2]} for r in results]
    
    def add_chat_message(self, session_id: str, message: str, response: str, patient_context: str = None):
        """Add chat message to history"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO chat_sessions (session_id, message, response, patient_context)
                VALUES (?, ?, ?, ?)
            ''', (session_id, message, response, patient_context))
            conn.commit()
    
    def get_chat_history(self, session_id: str) -> List[Dict]:
        """Get chat history for session"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT message, response, patient_context, created_at
                FROM chat_sessions 
                WHERE session_id = ?
                ORDER BY created_at ASC
            ''', (session_id,))
            
            history = cursor.fetchall()
            return [{'message': h[0], 'response': h[1], 'patient_context': h[2], 
                    'created_at': h[3]} for h in history] 