import os
import time
from pathlib import Path
from typing import List, Dict, Any
from concurrent.futures import ThreadPoolExecutor, as_completed
import streamlit as st
import pandas as pd

from .database_manager import DatabaseManager
from .document_processor import DocumentProcessor

class IngestionManager:
    def __init__(self, database_manager: DatabaseManager, document_processor: DocumentProcessor):
        self.db = database_manager
        self.processor = document_processor
        
        # Dataset paths
        self.dataset_path = Path("dataset")
        self.documents_path = self.dataset_path / "documents"
        self.images_base_path = self.dataset_path / "images"  # Fixed: should include 'images' directory
        self.excel_file_path = self.documents_path / "clinical_data.xlsx"
        
        # Create directories if they don't exist
        self.dataset_path.mkdir(exist_ok=True)
        self.documents_path.mkdir(exist_ok=True)
        self.images_base_path.mkdir(exist_ok=True)
        
        # Supported file extensions
        self.supported_extensions = {
            'documents': ['.xlsx', '.xls', '.docx', '.txt', '.pdf'],
            'images': ['.jpg', '.jpeg', '.png', '.bmp', '.tiff']
        }
    
    def scan_dataset_folder(self) -> Dict[str, List[str]]:
        """Scan the dataset folder and return categorized file paths"""
        files = {
            'documents': [],
            'images': [],
            'unknown': []
        }

        if not self.dataset_path.exists():
            print(f"Dataset folder not found: {self.dataset_path}")
            return files

        print(f"Scanning dataset folder: {self.dataset_path}")

        # Check for the main Excel file
        if self.excel_file_path.exists():
            files['documents'].append(str(self.excel_file_path))
            print(f"Found main dataset file: {self.excel_file_path.relative_to(self.dataset_path)}")
        
        # Check for PDF files
        for file_path in self.dataset_path.rglob("*.pdf"):
            if file_path.is_file():
                files['documents'].append(str(file_path))
                print(f"Found PDF file: {file_path.relative_to(self.dataset_path)}")

        # Check for DOCX files
        for file_path in self.dataset_path.rglob("*.docx"):
            if file_path.is_file():
                files['documents'].append(str(file_path))
                print(f"Found DOCX file: {file_path.relative_to(self.dataset_path)}")

        # Count images for informational purposes (already handled by ImagePath column in Excel)
        images_dir = self.dataset_path / "images"
        image_count = 0
        if images_dir.exists():
            for file_path in images_dir.rglob("*"):
                if file_path.is_file():
                    ext = file_path.suffix.lower()
                    if ext in self.supported_extensions['images']:
                        image_count += 1

        print(f"Found {image_count} images in the dataset")

        return files
    
    def get_files_to_process(self) -> Dict[str, List[str]]:
        """Get files that need to be processed (new or modified)"""
        all_files = self.scan_dataset_folder()
        
        files_to_process = {
            'documents': [],
            'images': [],
            'unknown': []
        }
        
        # Check if the main Excel file needs processing
        if self.excel_file_path.exists() and not self.db.is_file_processed(str(self.excel_file_path)):
            files_to_process['documents'].append(str(self.excel_file_path))
        
        # Check for additional document files (DOCX) in the documents directory that might have been added
        documents_dir = self.dataset_path / "documents"
        if documents_dir.exists():
            for file_path in documents_dir.glob("*.docx"):
                if file_path.is_file() and file_path != self.excel_file_path:
                    ext = file_path.suffix.lower()
                    if ext in self.supported_extensions['documents']:
                        if not self.db.is_file_processed(str(file_path)):
                            files_to_process['documents'].append(str(file_path))
                            print(f"📄 Found new/modified document: {file_path.name}")

        # Check for additional PDF files in the PDFs directory that might have been added
        pdfs_dir = self.dataset_path / "documents"
        if pdfs_dir.exists():
            for file_path in pdfs_dir.glob("*.pdf"):
                if file_path.is_file():
                    ext = file_path.suffix.lower()
                    if ext in self.supported_extensions['documents']:
                        if not self.db.is_file_processed(str(file_path)):
                            files_to_process['documents'].append(str(file_path))
                            print(f"📄 Found new/modified PDF: {file_path.name}")
        
        # Note: Images are processed as part of the Excel dataset processing via ImagePath column
        # We don't process standalone images that aren't referenced in the dataset
        
        # Print summary of files to process
        if any(files_to_process.values()):
            total_files = sum(len(files) for files in files_to_process.values())
            print(f"📋 Found {total_files} files to process:")
            if files_to_process['documents']:
                print(f"   📄 Documents: {len(files_to_process['documents'])}")
            if files_to_process['images']:
                print(f"   🖼️ Images: {len(files_to_process['images'])}")
        else:
            print("✅ All files are up to date - no processing needed")
        
        return files_to_process
    
    def process_excel_dataset(self, file_path: str) -> Dict[str, Any]:
        """Process the main Excel dataset file with integrated patient data and images"""
        try:
            print(f"📊 Processing main dataset: {file_path}")
            
            # Read the Excel file
            df = pd.read_excel(file_path)
            print(f"Dataset shape: {df.shape}")
            print(f"Columns: {list(df.columns)}")
            
            processed_count = 0
            image_processed_count = 0
            errors = []
            
            for index, row in df.iterrows():
                try:
                    # Extract patient information
                    patient_id = str(row.get('PatientID', '')).strip()
                    patient_name = str(row.get('Name', '')).strip()
                    
                    if not patient_name or patient_name == 'nan':
                        print(f"Skipping row {index}: No patient name found")
                        continue
                    
                    # Find or create patient
                    patient_uuid = self.db.find_or_create_patient(patient_name, patient_id)
                    
                    # Prepare clinical data content
                    clinical_data = self._prepare_clinical_content(row)
                    
                    # Add clinical document to database
                    # Use a virtual file path that includes the row index
                    virtual_file_path = f"{file_path}#row_{index}"
                    
                    self.db.add_document(
                        patient_uuid=patient_uuid,
                        file_path=virtual_file_path,
                        content=clinical_data['content'],
                        processed_content=clinical_data['processed_content'],
                        metadata=clinical_data['metadata']
                    )
                    processed_count += 1
                    
                    # Process associated image if available
                    image_path = row.get('ImagePath', '').strip()
                    if image_path and image_path != 'nan':
                        # Remove 'images\' or 'images/' prefix if it exists since images_base_path already includes it
                        clean_image_path = image_path
                        if clean_image_path.startswith('images\\') or clean_image_path.startswith('images/'):
                            clean_image_path = clean_image_path[7:]  # Remove 'images\' or 'images/' prefix (7 characters)
                        
                        # Convert relative path to absolute path
                        full_image_path = self.images_base_path / clean_image_path.replace('\\', os.sep)
                        
                        if full_image_path.exists():
                            print(f"   Processing image: {image_path}")
                            image_result = self._process_patient_image(
                                str(full_image_path), 
                                patient_uuid, 
                                patient_name, 
                                patient_id
                            )
                            if image_result['status'] == 'success':
                                image_processed_count += 1
                                print(f"   ✅ Image processed for {patient_name}")
                            else:
                                print(f"   ❌ Image processing failed for {patient_name}: {image_result['message']}")
                        else:
                            print(f"   ⚠️ Image not found for {patient_name}: {full_image_path}")
                            print(f"       Expected path: {full_image_path}")
                            print(f"       Raw image path from Excel: {image_path}")
                            print(f"       Cleaned image path: {clean_image_path}")
                            print(f"       Images base path: {self.images_base_path}")
                    
                    # Show progress every 25 records
                    if (index + 1) % 25 == 0:
                        print(f"✅ Processed {index + 1}/{len(df)} patients... ({processed_count} patients, {image_processed_count} images)")
                
                except Exception as e:
                    error_msg = f"Error processing row {index} (Patient: {row.get('Name', 'Unknown')}): {str(e)}"
                    errors.append(error_msg)
                    print(f"❌ {error_msg}")
                    continue
            
            # Mark the main Excel file as processed (not the individual rows)
            self.db.mark_file_processed(file_path)
            
            return {
                'status': 'success',
                'file_path': file_path,
                'patients_processed': processed_count,
                'images_processed': image_processed_count,
                'errors': errors,
                'message': f"Successfully processed {processed_count} patients and {image_processed_count} images"
            }
            
        except Exception as e:
            return {
                'status': 'error',
                'file_path': file_path,
                'patients_processed': 0,
                'images_processed': 0,
                'message': f"Error processing dataset: {str(e)}"
            }
    
    def _prepare_clinical_content(self, row: pd.Series) -> Dict[str, str]:
        """Prepare clinical content from a row of data"""
        # Build structured clinical content
        content_parts = []
        
        # Patient demographics
        content_parts.append(f"Patient: {row.get('Name', 'Unknown')}")
        content_parts.append(f"Patient ID: {row.get('PatientID', 'Unknown')}")
        content_parts.append(f"Age: {row.get('Age', 'Unknown')}")
        content_parts.append(f"Gender: {row.get('Gender', 'Unknown')}")
        
        # Clinical information
        if pd.notna(row.get('TreatmentDate')):
            content_parts.append(f"Treatment Date: {row.get('TreatmentDate')}")
        
        if pd.notna(row.get('DoctorName')):
            content_parts.append(f"Doctor: {row.get('DoctorName')}")
            
        if pd.notna(row.get('Department')):
            content_parts.append(f"Department: {row.get('Department')}")
        
        # Medical details
        if pd.notna(row.get('Diagnosis')):
            content_parts.append(f"Diagnosis: {row.get('Diagnosis')}")
            
        if pd.notna(row.get('Description')):
            content_parts.append(f"Description: {row.get('Description')}")
            
        if pd.notna(row.get('Procedures')):
            content_parts.append(f"Procedures: {row.get('Procedures')}")
            
        if pd.notna(row.get('Medicines')):
            content_parts.append(f"Medications: {row.get('Medicines')}")
            
        if pd.notna(row.get('Allergies')):
            content_parts.append(f"Allergies: {row.get('Allergies')}")
            
        if pd.notna(row.get('PastMedicalHistory')):
            content_parts.append(f"Past Medical History: {row.get('PastMedicalHistory')}")
            
        if pd.notna(row.get('Assessments')):
            content_parts.append(f"Assessments: {row.get('Assessments')}")
            
        if pd.notna(row.get('FollowUpDate')):
            content_parts.append(f"Follow-up Date: {row.get('FollowUpDate')}")
        
        # Image reference
        if pd.notna(row.get('ImagePath')):
            content_parts.append(f"Associated Image: {row.get('ImagePath')}")
        
        content = "\n".join(content_parts)
        
        # Enhanced content for better searchability
        processed_content = self.processor.enhance_text_with_ai(content, "clinical_record")
        
        # Metadata
        metadata = {
            'file_type': 'clinical_record',
            'patient_id': str(row.get('PatientID', '')),
            'patient_name': str(row.get('Name', '')),
            'age': str(row.get('Age', '')),
            'gender': str(row.get('Gender', '')),
            'department': str(row.get('Department', '')),
            'image_path': str(row.get('ImagePath', ''))
        }
        
        return {
            'content': content,
            'processed_content': processed_content,
            'metadata': metadata
        }
    
    def _process_patient_image(self, image_path: str, patient_uuid: int, 
                              patient_name: str, patient_id: str) -> Dict[str, Any]:
        """Process an image associated with a patient using comprehensive analysis"""
        try:
            print(f"   🔍 Analyzing image: {os.path.basename(image_path)}")
            
            # Get patient clinical data to provide context for image analysis
            patient_data = self.db.get_patient_data(patient_name=patient_name, patient_id=patient_id)
            clinical_context = ""
            if patient_data and patient_data.get('documents'):
                # Extract key clinical information for context
                clinical_doc = patient_data['documents'][0]  # Use the first (most recent) document
                clinical_content = clinical_doc.get('content', '')
                # Extract key info for image analysis context
                clinical_context = f"Clinical History: {clinical_content[:800]}..."
            
            # Use comprehensive image analysis (tries both Google Vision and OpenAI Vision)
            analysis_result = self.processor.transcribe_and_analyze_image(
                image_path=image_path,
                patient_name=patient_name,
                patient_id=patient_id,
                clinical_context=clinical_context
            )
            
            # Use the combined analysis as the main transcription
            final_transcription = analysis_result['combined_analysis']
            image_category = analysis_result['image_category']
            processing_method = analysis_result['processing_method']
            
            print(f"   ✅ Image processed using: {processing_method}")
            
            # Add to database
            self.db.add_image(
                patient_uuid=patient_uuid,
                file_path=image_path,
                transcription=final_transcription,
                image_category=image_category,
                metadata={
                    'patient_name': patient_name,
                    'patient_id': patient_id,
                    'processing_method': processing_method,
                    'text_extraction': analysis_result['text_extraction'],
                    'visual_analysis': analysis_result['visual_analysis'],
                    'processing_status': 'success' if 'Error' not in final_transcription else 'partial_success'
                }
            )
            
            return {
                'status': 'success',
                'message': f"Processed image for {patient_name} using {processing_method}"
            }
            
        except Exception as e:
            print(f"   ❌ Error processing image: {str(e)}")
            return {
                'status': 'error',
                'message': f"Error processing image for {patient_name}: {str(e)}"
            }
    
    def _get_image_category_from_path(self, image_path: str) -> str:
        """Determine image category from the file path"""
        path_lower = image_path.lower()
        
        if 'cxr' in path_lower:
            return 'CXR'
        elif 'chestct' in path_lower:
            return 'ChestCT'
        elif 'abdomect' in path_lower or 'abdomenct' in path_lower:
            return 'AbdomenCT'
        elif 'headct' in path_lower:
            return 'HeadCT'
        elif 'breastmri' in path_lower:
            return 'BreastMRI'
        elif 'hand' in path_lower:
            return 'Hand'
        else:
            return 'Unknown'
    
    def process_single_document(self, file_path: str) -> Dict[str, Any]:
        """Process a single document file - now handles the main Excel dataset"""
        if file_path == str(self.excel_file_path):
            # This is our main clinical dataset
            return self.process_excel_dataset(file_path)
        else:
            # Fallback for other document types (if any)
            return self._process_legacy_document(file_path)

    def _process_legacy_document(self, file_path: str) -> Dict[str, Any]:
        """Fallback method for processing individual document files (legacy support)"""
        try:
            results = self.processor.process_file(file_path)
            processed_count = 0
            
            for result in results:
                if result and result.get('content'):
                    # Find or create patient
                    patient_uuid = self.db.find_or_create_patient(
                        result['patient_name'], 
                        result['patient_id']
                    )
                    
                    # Enhance content with AI if enabled
                    enhanced_content = self.processor.enhance_text_with_ai(
                        result['content'], 
                        result.get('metadata', {}).get('file_type', 'document')
                    )
                    
                    # Add to database
                    self.db.add_document(
                        patient_uuid=patient_uuid,
                        file_path=file_path,
                        content=result['content'],
                        processed_content=enhanced_content,
                        metadata=result.get('metadata', {})
                    )
                    processed_count += 1
            
            return {
                'status': 'success',
                'file_path': file_path,
                'records_processed': processed_count,
                'message': f"Processed {processed_count} records from {os.path.basename(file_path)}"
            }
            
        except Exception as e:
            return {
                'status': 'error',
                'file_path': file_path,
                'records_processed': 0,
                'message': f"Error processing {os.path.basename(file_path)}: {str(e)}"
            }
    
    def process_single_image(self, file_path: str) -> Dict[str, Any]:
        """Process a single image file - now only used for standalone images not in the dataset"""
        print(f"⚠️ Processing standalone image: {os.path.basename(file_path)}")
        print("   Note: Images should now be processed as part of the clinical dataset.")
        
        try:
            # For standalone images, try to extract patient info from filename/path
            patient_name = self._extract_patient_from_filename(file_path)
            patient_id = ""
            
            # Find or create patient
            patient_uuid = self.db.find_or_create_patient(patient_name, patient_id)
            
            # Process the image
            result = self._process_patient_image(file_path, patient_uuid, patient_name, patient_id)
            
            if result['status'] == 'success':
                return {
                    'status': 'success',
                    'file_path': file_path,
                    'records_processed': 1,
                    'message': f"Processed standalone image {os.path.basename(file_path)}"
                }
            else:
                return {
                    'status': 'error',
                    'file_path': file_path,
                    'records_processed': 0,
                    'message': result['message']
                }
                
        except Exception as e:
            return {
                'status': 'error',
                'file_path': file_path,
                'records_processed': 0,
                'message': f"Error processing image {os.path.basename(file_path)}: {str(e)}"
            }

    def ingest_images(self, file_paths: List[str], show_progress: bool = True) -> List[Dict[str, Any]]:
        """Process standalone images not part of the main clinical dataset"""
        if not file_paths:
            return []
            
        print(f"⚠️ Processing {len(file_paths)} standalone images.")
        print("   Note: Images should be linked via the clinical dataset Excel file.")
        
        results = []
        
        if show_progress:
            progress_bar = st.progress(0)
            status_text = st.empty()
        
        for i, file_path in enumerate(file_paths):
            if show_progress:
                progress_bar.progress((i + 1) / len(file_paths))
                status_text.text(f"Processing {os.path.basename(file_path)}...")
            
            result = self.process_single_image(file_path)
            results.append(result)
            
            # Mark file as processed if successful
            if result['status'] == 'success':
                self.db.mark_file_processed(file_path)
            
            # Print progress
            if result['status'] == 'success':
                print(f"✅ {os.path.basename(file_path)}: processed")
            else:
                print(f"❌ {os.path.basename(file_path)}: {result['message']}")
        
        if show_progress:
            progress_bar.empty()
            status_text.empty()
        
        return results
    
    def ingest_documents(self, file_paths: List[str], show_progress: bool = True) -> List[Dict[str, Any]]:
        """Ingest documents using the new Excel-based approach"""
        if not file_paths:
            return []
        
        results = []
        
        if show_progress:
            progress_bar = st.progress(0)
            status_text = st.empty()
        
        for i, file_path in enumerate(file_paths):
            if show_progress:
                progress_bar.progress((i + 1) / len(file_paths))
                status_text.text(f"Processing {os.path.basename(file_path)}...")
            
            result = self.process_single_document(file_path)
            results.append(result)
            
            # Mark file as processed if successful
            if result['status'] == 'success':
                self.db.mark_file_processed(file_path)
            
            # Print progress
            if result['status'] == 'success':
                patients_count = result.get('patients_processed', result.get('records_processed', 0))
                images_count = result.get('images_processed', 0)
                if images_count > 0:
                    print(f"✅ {os.path.basename(file_path)}: {patients_count} patients, {images_count} images")
                else:
                    print(f"✅ {os.path.basename(file_path)}: {patients_count} records")
            else:
                print(f"❌ {os.path.basename(file_path)}: {result['message']}")
        
        if show_progress:
            progress_bar.empty()
            status_text.empty()
        
        return results
    
    def full_ingestion(self, show_progress: bool = True) -> Dict[str, Any]:
        """Perform full ingestion of the dataset"""
        start_time = time.time()
        
        print("🚀 Starting full dataset ingestion...")
        
        # Get files to process
        files_to_process = self.get_files_to_process()
        
        total_documents = 0
        total_images = 0
        total_errors = 0
        
        # Process documents (DOCX and PDF files)
        all_documents = files_to_process['documents']
        if all_documents:
            print(f"📄 Processing {len(all_documents)} document file(s)...")
            doc_results = self.ingest_documents(all_documents, show_progress)
            
            for result in doc_results:
                if result['status'] == 'success':
                    total_documents += result.get('patients_processed', result.get('records_processed', 0))
                    total_images += result.get('images_processed', 0)
                else:
                    total_errors += 1
        
        # Note: Images are now processed as part of the Excel dataset, 
        # so we don't need separate image processing
        
        end_time = time.time()
        processing_time = end_time - start_time
        
        # Summary of the ingestion process
        summary = {
            'total_patients': total_documents,
            'total_images': total_images,
            'total_errors': total_errors,
            'processing_time': processing_time,
            'files_processed': len(all_documents),
            'status': 'success' if total_errors == 0 else 'partial_success'
        }
        
        print(f"✅ Ingestion completed in {processing_time:.2f} seconds")
        print(f"   📊 Documents processed: {total_documents}")
        print(f"   🖼️  Images processed: {total_images}")
        if total_errors > 0:
            print(f"   ⚠️  Errors: {total_errors}")
        
        return summary
    
    def get_ingestion_summary(self) -> Dict[str, Any]:
        """Get summary of ingestion status and dataset information"""
        stats = self.db.get_stats()
        
        # Check if main dataset file exists and when it was last processed
        excel_file_processed = False
        excel_file_info = "Not found"
        
        if self.excel_file_path.exists():
            excel_file_processed = self.db.is_file_processed(str(self.excel_file_path))
            file_size = self.excel_file_path.stat().st_size / 1024  # KB
            excel_file_info = f"Found ({file_size:.1f} KB)"
            if excel_file_processed:
                excel_file_info += " - Processed ✅"
            else:
                excel_file_info += " - Needs Processing ⚠️"
        
        # Check for files that need processing
        files_to_process = self.get_files_to_process()
        total_pending_files = sum(len(files) for files in files_to_process.values())
        
        # Check for additional document files (DOCX and PDF)
        additional_docs = []
        documents_dir = self.dataset_path / "documents"
        
        # Check for DOCX files
        if documents_dir.exists():
            for file_path in documents_dir.glob("*.docx"):
                if file_path.is_file() and file_path != self.excel_file_path:
                    ext = file_path.suffix.lower()
                    if ext in self.supported_extensions['documents']:
                        processed = self.db.is_file_processed(str(file_path))
                        additional_docs.append({
                            'name': file_path.name,
                            'size_kb': file_path.stat().st_size / 1024,
                            'processed': processed,
                            'type': 'DOCX'
                        })
        
        # Check for PDF files in the documents directory
        pdfs_dir = self.dataset_path / "documents"  # Update directory to "documents" for PDFs as well
        if pdfs_dir.exists():
            for file_path in pdfs_dir.glob("*.pdf"):  # Only look for PDF files in the "documents" folder
                if file_path.is_file():
                    ext = file_path.suffix.lower()
                    if ext in self.supported_extensions['documents']:
                        processed = self.db.is_file_processed(str(file_path))
                        additional_docs.append({
                            'name': file_path.name,
                            'size_kb': file_path.stat().st_size / 1024,
                            'processed': processed,
                            'type': 'PDF'
                        })
        
        # Return the summary dictionary
        return {
            'database_stats': stats,
            'excel_dataset': {
                'file_path': str(self.excel_file_path),
                'status': excel_file_info,
                'processed': excel_file_processed
            },
            'additional_documents': additional_docs,
            'images_directory': {
                'path': str(self.dataset_path / "images"),
                'exists': (self.dataset_path / "images").exists(),
                'note': 'Images are processed via Excel dataset ImagePath column'
            },
            'pending_processing': {
                'total_files': total_pending_files,
                'documents': len(files_to_process['documents']),
                'images': len(files_to_process['images']),
                'needs_processing': total_pending_files > 0
            }
        }
    
    def force_reprocess_all(self) -> Dict[str, Any]:
        """Force reprocessing of the entire dataset"""
        print("🔄 Forcing complete reprocessing of dataset...")
        
        # Clear file processing status for the main Excel file
        if self.excel_file_path.exists():
            import sqlite3
            with sqlite3.connect(self.db.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('DELETE FROM file_status WHERE file_path = ?', (str(self.excel_file_path),))
                conn.commit()
            
            print(f"✅ Cleared processing status for {self.excel_file_path.name}")
        
        # Clear all patient, document, and image data
        import sqlite3
        with sqlite3.connect(self.db.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM images')
            cursor.execute('DELETE FROM documents') 
            cursor.execute('DELETE FROM patients')
            cursor.execute('DELETE FROM chat_sessions')
            cursor.execute('DELETE FROM file_status')  # Clear all file processing status
            conn.commit()
            
        print("✅ Cleared all existing data from database")
        
        # Run full ingestion
        return self.full_ingestion(show_progress=True)
    
    def reprocess_patient_files(self, patient_name: str) -> Dict[str, Any]:
        """Reprocess all files for a specific patient"""
        # Find patient files and clear their processing status
        patient_data = self.db.get_patient_data(patient_name=patient_name)
        
        if not patient_data:
            return {
                'status': 'error',
                'message': f'Patient {patient_name} not found in database'
            }
        
        # Get file paths for this patient
        file_paths = []
        for doc in patient_data['documents']:
            file_paths.append(doc['metadata'].get('source', ''))
        for img in patient_data['images']:
            file_paths.append(img['metadata'].get('source', ''))
        
        # Clear processing status for these files
        import sqlite3
        with sqlite3.connect(self.db.db_path) as conn:
            cursor = conn.cursor()
            for file_path in file_paths:
                if file_path:
                    cursor.execute('DELETE FROM file_status WHERE file_path = ?', (file_path,))
            conn.commit()
        
        print(f"Cleared processing status for {len(file_paths)} files belonging to patient {patient_name}")
        
        # Reprocess
        return self.full_ingestion()
    
    def _print_folder_summary(self, files_to_process: Dict[str, List[str]]):
        """Print a summary of the folder structure being processed"""
        if not any(files_to_process.values()):
            return
        
        folder_summary = {}
        all_files = []
        for file_list in files_to_process.values():
            all_files.extend(file_list)
        
        # Analyze folder structure
        for file_path in all_files:
            relative_path = Path(file_path).relative_to(self.dataset_path)
            folder_path = relative_path.parent
            
            if folder_path not in folder_summary:
                folder_summary[folder_path] = {'documents': 0, 'images': 0}
            
            ext = Path(file_path).suffix.lower()
            if ext in self.supported_extensions['documents']:
                folder_summary[folder_path]['documents'] += 1
            elif ext in self.supported_extensions['images']:
                folder_summary[folder_path]['images'] += 1
        
        print("\n📁 Folder Structure Summary:")
        for folder, counts in sorted(folder_summary.items()):
            folder_str = str(folder) if str(folder) != '.' else '(root)'
            total_files = counts['documents'] + counts['images']
            print(f"   {folder_str}: {total_files} files ({counts['documents']} docs, {counts['images']} images)")
    
    def get_folder_structure_info(self) -> Dict[str, Any]:
        """Get detailed information about the dataset folder structure"""
        all_files = self.scan_dataset_folder()
        
        structure_info = {
            'total_folders': set(),
            'folder_details': {},
            'file_types': {},
            'patient_folders': []
        }
        
        all_file_paths = []
        for file_list in all_files.values():
            all_file_paths.extend(file_list)
        
        for file_path in all_file_paths:
            relative_path = Path(file_path).relative_to(self.dataset_path)
            folder_path = relative_path.parent
            structure_info['total_folders'].add(str(folder_path))
            
            # Track file types
            ext = Path(file_path).suffix.lower()
            structure_info['file_types'][ext] = structure_info['file_types'].get(ext, 0) + 1
            
            # Track folder details
            folder_str = str(folder_path)
            if folder_str not in structure_info['folder_details']:
                structure_info['folder_details'][folder_str] = {
                    'file_count': 0,
                    'file_types': set(),
                    'potential_patient_folder': False
                }
            
            structure_info['folder_details'][folder_str]['file_count'] += 1
            structure_info['folder_details'][folder_str]['file_types'].add(ext)
            
            # Check if this might be a patient folder
            folder_lower = folder_str.lower()
            if any(keyword in folder_lower for keyword in ['patient', 'episode', 'case', 'record']):
                structure_info['folder_details'][folder_str]['potential_patient_folder'] = True
                if folder_str not in structure_info['patient_folders']:
                    structure_info['patient_folders'].append(folder_str)
        
        structure_info['total_folders'] = len(structure_info['total_folders'])
        
        return structure_info
    
    def _extract_patient_from_filename(self, file_path: str) -> str:
        """Extract patient name from filename or folder structure as fallback"""
        filename = os.path.basename(file_path)
        path_parts = Path(file_path).parts
        
        # Try to extract patient info from various folder naming patterns
        for part in path_parts:
            part_lower = part.lower()
            
            # Look for patterns indicating patient folders
            if any(keyword in part_lower for keyword in ['episode', 'patient', 'case', 'record']):
                # Extract patient name from episode/patient folder
                patient_name = part.replace('_Episode', '').replace('_Patient', '').replace('_Case', '').replace('_Record', '')
                patient_name = patient_name.replace('_', ' ').replace('-', ' ').strip()
                if patient_name and len(patient_name) > 2:  # Valid name
                    return patient_name
        
        # Try to extract from filename patterns
        filename_base = os.path.splitext(filename)[0]
        
        # Look for patient name patterns in filename (e.g., "PatientName_date.docx")
        if '_' in filename_base:
            parts = filename_base.split('_')
            # If first part looks like a name (contains letters, reasonable length)
            if parts[0] and len(parts[0]) > 2 and any(c.isalpha() for c in parts[0]):
                potential_name = parts[0].replace('-', ' ').strip()
                return potential_name
        
        # Look for space-separated names in filename
        if ' ' in filename_base:
            words = filename_base.split()
            # Take first few words that look like names
            name_words = []
            for word in words[:3]:  # Maximum 3 words for name
                if word and len(word) > 1 and any(c.isalpha() for c in word):
                    name_words.append(word)
                else:
                    break
            if name_words:
                return ' '.join(name_words)
        
        # Check if any folder in the path could be a patient identifier
        for part in path_parts[:-1]:  # Exclude the filename itself
            # Skip common folder names
            skip_folders = {'dataset', 'documents', 'images', 'files', 'data', 'medical', 'records', 'reports'}
            if part.lower() not in skip_folders and len(part) > 2:
                # This could be a patient folder
                return part.replace('_', ' ').replace('-', ' ').strip()
        
        # Final fallback: use filename without extension
        return filename_base.replace('_', ' ').replace('-', ' ').strip() or 'Unknown Patient' 