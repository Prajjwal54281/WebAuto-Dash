"""
WebAutoDash Provider-Based Data Processor
Processes JSON extraction files with complete provider separation
"""

import json
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
import os
from pathlib import Path

from db_connection_provider import (
    provider_db_manager, get_provider_connection, 
    calculate_data_checksum
)

logger = logging.getLogger(__name__)

class ProviderDataProcessor:
    """
    Data processor that handles provider-separated databases
    Each provider's data is stored in their own database for complete isolation
    """
    
    def __init__(self):
        self.db_manager = provider_db_manager
        self.processed_files = set()
        self.stats = {
            'total_files_processed': 0,
            'total_patients_processed': 0,
            'new_patients_created': 0,
            'duplicate_extractions_found': 0,
            'conflicts_detected': 0,
            'errors_encountered': 0,
            'providers_processed': set()
        }
    
    def process_json_file(self, json_filepath: str) -> Dict[str, Any]:
        """
        Main entry point: Process a JSON results file with provider separation
        
        Args:
            json_filepath: Path to the JSON file to process
            
        Returns:
            Processing results and statistics
        """
        try:
            self.db_manager.log_system_event('INFO', 'DataProcessor', 
                                           f'Starting processing of {json_filepath}')
            
            # Validate file exists and is readable
            if not os.path.exists(json_filepath):
                raise FileNotFoundError(f"JSON file not found: {json_filepath}")
            
            # Load and validate JSON
            with open(json_filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Validate JSON structure
            if not self._validate_json_structure(data):
                raise ValueError("Invalid JSON structure")
            
            # Extract metadata and results
            metadata = data.get('extraction_metadata', {})
            extraction_results = data.get('extraction_results', [])
            
            # Get provider name and ensure provider is registered
            provider_name = metadata.get('provider_name', 'unknown_provider')
            provider_info = self.db_manager.register_provider(provider_name)
            
            logger.info(f"Processing for provider: {provider_name} -> {provider_info['database_name']}")
            
            # Create extraction session in provider's database
            session_id = self._create_extraction_session(metadata, json_filepath, provider_name)
            
            # Process each patient in the results
            processing_results = []
            for patient_data in extraction_results:
                result = self._process_patient_data(patient_data, session_id, metadata, provider_name)
                processing_results.append(result)
            
            # Update session statistics
            self._update_session_statistics(session_id, processing_results, provider_name)
            
            # Update internal statistics
            self.stats['total_files_processed'] += 1
            self.stats['total_patients_processed'] += len(extraction_results)
            self.stats['providers_processed'].add(provider_name)
            
            self.db_manager.log_system_event('INFO', 'DataProcessor', 
                                           f'Successfully processed {json_filepath}',
                                           provider_name,
                                           {'patients_processed': len(extraction_results),
                                            'session_id': session_id,
                                            'database': provider_info['database_name']})
            
            return {
                'success': True,
                'provider_name': provider_name,
                'database_name': provider_info['database_name'],
                'session_id': session_id,
                'patients_processed': len(extraction_results),
                'processing_results': processing_results,
                'statistics': self.stats
            }
            
        except Exception as e:
            self.stats['errors_encountered'] += 1
            error_msg = f"Error processing {json_filepath}: {str(e)}"
            logger.error(error_msg)
            
            # Try to log to system even if provider processing failed
            try:
                provider_name = data.get('extraction_metadata', {}).get('provider_name', 'unknown')
                self.db_manager.log_system_event('ERROR', 'DataProcessor', error_msg, 
                                               provider_name,
                                               {'file_path': json_filepath, 'error_type': type(e).__name__})
            except:
                pass
            
            return {
                'success': False,
                'error': str(e),
                'file_path': json_filepath,
                'statistics': self.stats
            }
    
    def _validate_json_structure(self, data: Dict) -> bool:
        """Validate that JSON has required structure"""
        required_fields = ['extraction_metadata', 'extraction_results']
        
        for field in required_fields:
            if field not in data:
                logger.error(f"Missing required field: {field}")
                return False
        
        if not isinstance(data['extraction_results'], list):
            logger.error("extraction_results must be a list")
            return False
        
        metadata = data['extraction_metadata']
        if not metadata.get('provider_name'):
            logger.warning("No provider_name in metadata, will use 'unknown_provider'")
        
        return True
    
    def _create_extraction_session(self, metadata: Dict, filepath: str, provider_name: str) -> int:
        """Create an extraction session record in provider's database"""
        try:
            conn = get_provider_connection(provider_name)
            cursor = conn.cursor()
            
            query = """
                INSERT INTO extraction_sessions (
                    job_id, job_name, portal_name, extraction_mode,
                    target_medication, start_date, end_date, extracted_at,
                    results_filename, provider_directory
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            
            # Parse dates safely
            start_date = self._parse_date(metadata.get('start_date'))
            end_date = self._parse_date(metadata.get('end_date'))
            extracted_at = self._parse_datetime(metadata.get('extracted_at'))
            
            values = (
                metadata.get('job_id'),
                metadata.get('job_name'),
                metadata.get('portal_name'),
                metadata.get('extraction_mode'),
                metadata.get('medication'),
                start_date,
                end_date,
                extracted_at,
                os.path.basename(filepath),
                metadata.get('provider_directory')
            )
            
            cursor.execute(query, values)
            conn.commit()
            session_id = cursor.lastrowid
            
            self.db_manager.log_system_event('INFO', 'SessionCreation', 
                                           f'Created extraction session {session_id}',
                                           provider_name, metadata)
            
            return session_id
            
        except Exception as e:
            logger.error(f"Failed to create extraction session for {provider_name}: {e}")
            raise
        finally:
            if conn.is_connected():
                cursor.close()
                conn.close()
    
    def _process_patient_data(self, patient_data: Dict, session_id: int, 
                            metadata: Dict, provider_name: str) -> Dict[str, Any]:
        """Process individual patient data in provider's database"""
        prn = None
        try:
            # Extract patient identifiers
            demographics = patient_data.get('demographics_printable', {})
            prn = demographics.get('prn')
            patient_uuid = patient_data.get('patient_id')
            patient_name = patient_data.get('patient_name')
            
            if not prn:
                error_msg = f"No PRN found for patient {patient_name}"
                logger.warning(error_msg)
                self.db_manager.log_system_event('WARNING', 'PatientProcessing', error_msg,
                                               provider_name,
                                               {'patient_name': patient_name, 'patient_uuid': patient_uuid})
                return {
                    'success': False,
                    'error': 'No PRN found',
                    'patient_name': patient_name,
                    'skipped': True
                }
            
            # Get or create patient record
            patient_id = self._get_or_create_patient(patient_data, provider_name)
            
            # Check for duplicate extraction
            existing_extraction = self._check_existing_extraction(
                prn, session_id, metadata, patient_data, provider_name
            )
            
            if existing_extraction:
                # Handle duplicate/conflict
                conflict_result = self._handle_duplicate_extraction(
                    patient_id, existing_extraction, patient_data, session_id, provider_name
                )
                
                # Create comprehensive record even for duplicates (if no conflict or conflict handled)
                comprehensive_record_id = self._create_comprehensive_patient_record(
                    patient_id, session_id, patient_data, metadata, provider_name
                )
                
                return {
                    'success': True,
                    'prn': prn,
                    'patient_id': patient_id,
                    'comprehensive_record_id': comprehensive_record_id,
                    'action': 'duplicate_handled',
                    'conflict_detected': conflict_result['conflict_detected'],
                    'details': conflict_result
                }
            else:
                # Create new extraction record
                extraction_id = self._create_patient_extraction(
                    patient_id, session_id, patient_data, metadata, provider_name
                )
                
                # Process medical data
                medical_data_result = self._process_medical_data(extraction_id, patient_data, provider_name)
                
                # Create comprehensive patient record organized by date range
                comprehensive_record_id = self._create_comprehensive_patient_record(
                    patient_id, session_id, patient_data, metadata, provider_name
                )
                
                self.stats['new_patients_created'] += 1
                
                return {
                    'success': True,
                    'prn': prn,
                    'patient_id': patient_id,
                    'extraction_id': extraction_id,
                    'comprehensive_record_id': comprehensive_record_id,
                    'action': 'new_extraction_created',
                    'medical_data': medical_data_result
                }
        
        except Exception as e:
            self.stats['errors_encountered'] += 1
            error_msg = f"Error processing patient {prn}: {str(e)}"
            logger.error(error_msg)
            self.db_manager.log_system_event('ERROR', 'PatientProcessing', error_msg,
                                           provider_name,
                                           {'prn': prn, 'error_type': type(e).__name__})
            
            return {
                'success': False,
                'error': str(e),
                'prn': prn,
                'action': 'processing_failed'
            }
    
    def _get_or_create_patient(self, patient_data: Dict, provider_name: str) -> int:
        """Get existing patient by PRN or create new one in provider's database"""
        demographics = patient_data.get('demographics_printable', {})
        prn = demographics.get('prn')
        patient_uuid = patient_data.get('patient_id')
        
        try:
            conn = get_provider_connection(provider_name)
            cursor = conn.cursor()
            
            # Look for existing patient by PRN
            cursor.execute("SELECT id, patient_name, patient_uuid FROM patients WHERE prn = %s", (prn,))
            result = cursor.fetchone()
            
            if result:
                patient_id = result[0]
                
                # Update UUID and demographics if needed
                self._update_patient_if_changed(patient_id, patient_data, {
                    'id': result[0],
                    'patient_name': result[1],
                    'patient_uuid': result[2]
                }, provider_name)
                
                return patient_id
            
            # Create new patient record
            return self._create_new_patient(patient_data, provider_name)
            
        except Exception as e:
            logger.error(f"Error in get_or_create_patient for PRN {prn} in {provider_name}: {e}")
            raise
        finally:
            if conn.is_connected():
                cursor.close()
                conn.close()
    
    def _create_new_patient(self, patient_data: Dict, provider_name: str) -> int:
        """Create a new patient record with full demographics in provider's database"""
        demographics = patient_data.get('demographics_printable', {})
        
        # Parse patient name
        full_name = demographics.get('patient_name', '')
        name_parts = full_name.split(' ', 1) if full_name else ['', '']
        first_name = name_parts[0] if name_parts else ''
        last_name = name_parts[1] if len(name_parts) > 1 else ''
        
        # Parse date of birth
        dob = self._parse_date(demographics.get('date_of_birth'))
        
        try:
            conn = get_provider_connection(provider_name)
            cursor = conn.cursor()
            
            query = """
                INSERT INTO patients (
                    prn, patient_uuid, patient_name, first_name, last_name,
                    date_of_birth, age, gender, created_at
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            
            values = (
                demographics.get('prn'),
                patient_data.get('patient_id'),
                full_name,
                first_name,
                last_name,
                dob,
                demographics.get('age'),
                demographics.get('gender'),
                datetime.now()
            )
            
            cursor.execute(query, values)
            conn.commit()
            patient_id = cursor.lastrowid
            
            self.db_manager.log_system_event('INFO', 'PatientCreation', 
                                           f'Created new patient record',
                                           provider_name,
                                           {'prn': demographics.get('prn'), 'name': full_name})
            
            return patient_id
            
        except Exception as e:
            logger.error(f"Failed to create patient in {provider_name}: {e}")
            raise
        finally:
            if conn.is_connected():
                cursor.close()
                conn.close()
    
    def _update_patient_if_changed(self, patient_id: int, new_data: Dict, 
                                 existing_record: Dict, provider_name: str):
        """Update patient record if demographics have changed"""
        demographics = new_data.get('demographics_printable', {})
        new_uuid = new_data.get('patient_id')
        new_name = demographics.get('patient_name', '')
        
        changes = []
        
        # Check for UUID change
        if new_uuid != existing_record.get('patient_uuid'):
            changes.append('patient_uuid')
        
        # Check for name change
        if new_name != existing_record.get('patient_name'):
            changes.append('patient_name')
        
        if changes:
            try:
                conn = get_provider_connection(provider_name)
                cursor = conn.cursor()
                
                # Parse name for update
                name_parts = new_name.split(' ', 1) if new_name else ['', '']
                first_name = name_parts[0] if name_parts else ''
                last_name = name_parts[1] if len(name_parts) > 1 else ''
                
                query = """
                    UPDATE patients 
                    SET patient_uuid = %s, patient_name = %s, first_name = %s, 
                        last_name = %s, age = %s, gender = %s, updated_at = %s
                    WHERE id = %s
                """
                
                values = (
                    new_uuid,
                    new_name,
                    first_name,
                    last_name,
                    demographics.get('age'),
                    demographics.get('gender'),
                    datetime.now(),
                    patient_id
                )
                
                cursor.execute(query, values)
                conn.commit()
                
                self.db_manager.log_system_event('INFO', 'PatientUpdate', 
                                               f'Updated patient demographics',
                                               provider_name,
                                               {'changes': changes, 'patient_id': patient_id})
                
            except Exception as e:
                logger.error(f"Failed to update patient {patient_id} in {provider_name}: {e}")
                raise
            finally:
                if conn.is_connected():
                    cursor.close()
                    conn.close()
    
    def _check_existing_extraction(self, prn: str, session_id: int, 
                                 metadata: Dict, patient_data: Dict, provider_name: str) -> Optional[Dict]:
        """Check if extraction already exists for same PRN with overlapping date ranges"""
        try:
            conn = get_provider_connection(provider_name)
            cursor = conn.cursor(dictionary=True)
            
            # Get current extraction's date range
            current_start = self._parse_date(metadata.get('start_date'))
            current_end = self._parse_date(metadata.get('end_date'))
            current_medication = metadata.get('medication')
            
            # Find extractions with overlapping date ranges for same PRN
            query = """
                SELECT pe.id, pe.data_checksum, pe.extraction_session_id,
                       es.extracted_at, es.results_filename, es.target_medication,
                       es.start_date, es.end_date
                FROM patient_extractions pe
                JOIN extraction_sessions es ON pe.extraction_session_id = es.id
                WHERE pe.prn = %s 
                AND es.id != %s
                AND (
                    (es.start_date <= %s AND es.end_date >= %s) OR  -- Overlapping ranges
                    (es.start_date <= %s AND es.end_date >= %s) OR  -- Current range overlaps existing
                    (es.start_date >= %s AND es.end_date <= %s)     -- Existing range within current
                )
                ORDER BY es.extracted_at DESC
            """
            
            cursor.execute(query, (
                prn, session_id,
                current_end, current_start,    # Check if existing ends after current starts
                current_start, current_end,    # Check if existing starts before current ends  
                current_start, current_end     # Check if existing is completely within current
            ))
            
            results = cursor.fetchall()
            
            # If specific medication filtering is needed, filter results
            if current_medication and current_medication.lower() != 'all':
                filtered_results = []
                for result in results:
                    if (result['target_medication'] and 
                        result['target_medication'].lower() == current_medication.lower()):
                        filtered_results.append(result)
                results = filtered_results
            
            return results[0] if results else None
            
        except Exception as e:
            logger.error(f"Error checking existing extraction for PRN {prn} in {provider_name}: {e}")
            return None
        finally:
            if conn.is_connected():
                cursor.close()
                conn.close()
    
    def _handle_duplicate_extraction(self, patient_id: int, existing_extraction: Dict,
                                   new_patient_data: Dict, new_session_id: int, 
                                   provider_name: str) -> Dict:
        """Handle duplicate extraction detection and conflict resolution with improved date range logic"""
        existing_checksum = existing_extraction['data_checksum']
        
        # Calculate checksum for medical data only (excluding UUID and metadata)
        medical_data_only = self._extract_medical_data_for_checksum(new_patient_data)
        new_checksum = calculate_data_checksum(medical_data_only)
        
        prn = new_patient_data.get('demographics_printable', {}).get('prn')
        
        if existing_checksum != new_checksum:
            # Data has changed - create conflict record
            conflict_id = self._log_data_conflict(
                patient_id=patient_id,
                prn=prn,
                existing_session_id=existing_extraction['extraction_session_id'],
                new_session_id=new_session_id,
                conflict_type='data_changed',
                description=f"Medical data changed for overlapping date range",
                old_checksum=existing_checksum,
                new_checksum=new_checksum,
                provider_name=provider_name
            )
            
            # Create new extraction record to track the change
            extraction_id = self._create_patient_extraction(
                patient_id, new_session_id, new_patient_data, {}, provider_name
            )
            
            # Process new medical data
            self._process_medical_data(extraction_id, new_patient_data, provider_name)
            
            self.stats['conflicts_detected'] += 1
            
            self.db_manager.log_system_event('WARNING', 'ConflictDetection',
                                           f'Medical data conflict detected for PRN {prn} in overlapping date ranges',
                                           provider_name,
                                           {'conflict_id': conflict_id, 'old_checksum': existing_checksum,
                                            'new_checksum': new_checksum,
                                            'existing_session': existing_extraction['extraction_session_id'],
                                            'new_session': new_session_id})
            
            return {
                'conflict_detected': True,
                'conflict_id': conflict_id,
                'action': 'new_extraction_created',
                'extraction_id': extraction_id
            }
        else:
            # Data is identical - just log duplicate
            self.stats['duplicate_extractions_found'] += 1
            
            self.db_manager.log_system_event('INFO', 'DuplicateDetection',
                                           f'Identical medical data found for PRN {prn} in overlapping date ranges',
                                           provider_name,
                                           {'existing_session': existing_extraction['extraction_session_id'],
                                            'new_session': new_session_id})
            
            return {
                'conflict_detected': False,
                'action': 'duplicate_skipped',
                'message': 'Identical medical data already exists for overlapping date range'
            }
    
    def _extract_medical_data_for_checksum(self, patient_data: Dict) -> Dict:
        """Extract only medical data for checksum calculation (excluding UUID and metadata)"""
        return {
            'demographics_printable': {
                'prn': patient_data.get('demographics_printable', {}).get('prn'),
                'patient_name': patient_data.get('demographics_printable', {}).get('patient_name'),
                'date_of_birth': patient_data.get('demographics_printable', {}).get('date_of_birth'),
                'gender': patient_data.get('demographics_printable', {}).get('gender'),
                'age': patient_data.get('demographics_printable', {}).get('age'),
            },
            'all_medications': patient_data.get('all_medications', []),
            'all_diagnoses': patient_data.get('all_diagnoses', []),
            'all_allergies': patient_data.get('all_allergies', []),
            'all_health_concerns': patient_data.get('all_health_concerns', [])
        }
    
    def _create_patient_extraction(self, patient_id: int, session_id: int,
                                 patient_data: Dict, metadata: Dict, provider_name: str) -> int:
        """Create a new patient extraction record in provider's database"""
        demographics = patient_data.get('demographics_printable', {})
        
        try:
            conn = get_provider_connection(provider_name)
            cursor = conn.cursor()
            
            query = """
                INSERT INTO patient_extractions (
                    prn, patient_id, extraction_session_id, patient_uuid,
                    filter_medication_name, filter_medication_strength,
                    filter_start_date, filter_stop_date, filter_last_seen,
                    filter_provider, summary_page_url, extraction_method,
                    found_at, data_checksum, processing_status
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            
            # Calculate data checksum
            data_checksum = calculate_data_checksum(patient_data)
            
            # Extract filter criteria
            extraction_metadata = patient_data.get('extraction_metadata', {})
            
            values = (
                demographics.get('prn'),
                patient_id,
                session_id,
                patient_data.get('patient_id'),
                patient_data.get('filter_medication_name'),
                patient_data.get('filter_medication_strength'),
                self._parse_date(patient_data.get('filter_start_date')),
                self._parse_date(patient_data.get('filter_stop_date')),
                self._parse_date(patient_data.get('filter_last_seen')),
                patient_data.get('filter_provider'),
                patient_data.get('summary_page_url'),
                extraction_metadata.get('extraction_method'),
                self._parse_datetime(extraction_metadata.get('found_at')),
                data_checksum,
                'processed'
            )
            
            cursor.execute(query, values)
            conn.commit()
            extraction_id = cursor.lastrowid
            
            return extraction_id
            
        except Exception as e:
            logger.error(f"Failed to create patient extraction in {provider_name}: {e}")
            raise
        finally:
            if conn.is_connected():
                cursor.close()
                conn.close()
    
    def _process_medical_data(self, extraction_id: int, patient_data: Dict, provider_name: str) -> Dict:
        """Process all medical data for a patient extraction in provider's database"""
        results = {
            'medications': 0,
            'diagnoses': 0,
            'allergies': 0,
            'health_concerns': 0,
            'errors': []
        }
        
        try:
            conn = get_provider_connection(provider_name)
            
            # Process medications
            medications = patient_data.get('all_medications', [])
            for med in medications:
                try:
                    self._process_medication(extraction_id, med, conn)
                    results['medications'] += 1
                except Exception as e:
                    results['errors'].append(f"Medication processing error: {e}")
            
            # Process diagnoses
            diagnoses = patient_data.get('all_diagnoses', [])
            for diag in diagnoses:
                try:
                    self._process_diagnosis(extraction_id, diag, conn)
                    results['diagnoses'] += 1
                except Exception as e:
                    results['errors'].append(f"Diagnosis processing error: {e}")
            
            # Process allergies
            allergies = patient_data.get('all_allergies', [])
            for allergy in allergies:
                try:
                    self._process_allergy(extraction_id, allergy, conn)
                    results['allergies'] += 1
                except Exception as e:
                    results['errors'].append(f"Allergy processing error: {e}")
            
            # Process health concerns
            health_concerns = patient_data.get('all_health_concerns', [])
            for concern in health_concerns:
                try:
                    self._process_health_concern(extraction_id, concern, conn)
                    results['health_concerns'] += 1
                except Exception as e:
                    results['errors'].append(f"Health concern processing error: {e}")
            
        except Exception as e:
            logger.error(f"Error processing medical data for extraction {extraction_id} in {provider_name}: {e}")
            results['errors'].append(f"General medical data processing error: {e}")
        finally:
            if conn.is_connected():
                conn.close()
        
        return results
    
    def _process_medication(self, extraction_id: int, medication: Dict, conn):
        """Process individual medication record"""
        cursor = conn.cursor()
        
        try:
            query = """
                INSERT INTO medications (
                    patient_extraction_id, medication_type, row_index,
                    medication_name, medication_strength, sig, start_date,
                    stop_date, dates, diagnosis, extraction_method, extracted_at
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            
            values = (
                extraction_id,
                medication.get('medication_type'),
                medication.get('row_index'),
                medication.get('medication_name'),
                self._extract_medication_strength(medication.get('medication_name', '')),
                medication.get('sig'),
                medication.get('start_date'),
                medication.get('stop_date'),
                medication.get('dates'),
                medication.get('diagnosis'),
                medication.get('extraction_method'),
                self._parse_datetime(medication.get('extracted_at'))
            )
            
            cursor.execute(query, values)
            conn.commit()
            
        finally:
            cursor.close()
    
    def _process_diagnosis(self, extraction_id: int, diagnosis: Dict, conn):
        """Process individual diagnosis record"""
        cursor = conn.cursor()
        
        try:
            query = """
                INSERT INTO diagnoses (
                    patient_extraction_id, diagnosis_type, row_index,
                    diagnosis_text, diagnosis_code, acuity, start_date,
                    stop_date, extraction_method, extracted_at
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            
            # Extract diagnosis code if present
            diagnosis_text = diagnosis.get('diagnosis_text', '')
            diagnosis_code = self._extract_diagnosis_code(diagnosis_text)
            
            values = (
                extraction_id,
                diagnosis.get('diagnosis_type'),
                diagnosis.get('row_index'),
                diagnosis_text,
                diagnosis_code,
                diagnosis.get('acuity'),
                diagnosis.get('start_date'),
                diagnosis.get('stop_date'),
                diagnosis.get('extraction_method'),
                self._parse_datetime(diagnosis.get('extracted_at'))
            )
            
            cursor.execute(query, values)
            conn.commit()
            
        finally:
            cursor.close()
    
    def _process_allergy(self, extraction_id: int, allergy: Any, conn):
        """Process individual allergy record"""
        cursor = conn.cursor()
        
        try:
            query = """
                INSERT INTO allergies (
                    patient_extraction_id, allergy_type, allergy_name, 
                    allergen, reaction, severity, notes, extraction_method, extracted_at
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            
            # Handle different allergy data formats
            if isinstance(allergy, dict):
                allergy_name = allergy.get('allergy_name', str(allergy))
                allergy_type = allergy.get('allergy_type', 'drug')
                reaction = allergy.get('reaction', '')
                severity = allergy.get('severity', '')
                notes = allergy.get('notes', '')
            else:
                allergy_name = str(allergy)
                allergy_type = 'drug'  # Default assumption
                reaction = ''
                severity = ''
                notes = ''
            
            values = (
                extraction_id,
                allergy_type,
                allergy_name,
                allergy_name,  # Use same as allergen for now
                reaction,
                severity,
                notes,
                'json_extraction',
                datetime.now()
            )
            
            cursor.execute(query, values)
            conn.commit()
            
        finally:
            cursor.close()
    
    def _process_health_concern(self, extraction_id: int, concern: Any, conn):
        """Process individual health concern record"""
        cursor = conn.cursor()
        
        try:
            query = """
                INSERT INTO health_concerns (
                    patient_extraction_id, concern_type, concern_text,
                    concern_category, status, priority, extraction_method, extracted_at
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """
            
            # Handle different concern data formats
            if isinstance(concern, dict):
                concern_text = concern.get('concern_text', str(concern))
                concern_type = concern.get('concern_type', 'active')
                status = concern.get('status', '')
                priority = concern.get('priority', '')
            else:
                concern_text = str(concern)
                concern_type = 'active'
                status = ''
                priority = ''
            
            values = (
                extraction_id,
                concern_type,
                concern_text,
                '',  # category
                status,
                priority,
                'json_extraction',
                datetime.now()
            )
            
            cursor.execute(query, values)
            conn.commit()
            
        finally:
            cursor.close()
    
    def _log_data_conflict(self, patient_id: int, prn: str, existing_session_id: int,
                         new_session_id: int, conflict_type: str, description: str,
                         old_checksum: str, new_checksum: str, provider_name: str) -> int:
        """Log a data conflict in provider's database"""
        try:
            conn = get_provider_connection(provider_name)
            cursor = conn.cursor()
            
            query = """
                INSERT INTO data_conflicts (
                    patient_id, prn, conflict_type, extraction_session_id_1, 
                    extraction_session_id_2, field_name, old_value, new_value, 
                    conflict_description, severity
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            
            cursor.execute(query, (
                patient_id, prn, conflict_type, existing_session_id, new_session_id,
                'data_checksum', old_checksum, new_checksum, description, 'medium'
            ))
            conn.commit()
            conflict_id = cursor.lastrowid
            
            logger.warning(f"Data conflict logged for patient {prn} in {provider_name}: {description}")
            return conflict_id
            
        except Exception as e:
            logger.error(f"Failed to log conflict in {provider_name}: {e}")
            raise
        finally:
            if conn.is_connected():
                cursor.close()
                conn.close()
    
    def _update_session_statistics(self, session_id: int, results: List[Dict], provider_name: str):
        """Update session statistics in provider's database"""
        try:
            conn = get_provider_connection(provider_name)
            cursor = conn.cursor()
            
            total_patients = len(results)
            successful = sum(1 for r in results if r.get('success'))
            failed = total_patients - successful
            conflicts = sum(1 for r in results if r.get('conflict_detected'))
            
            query = """
                UPDATE extraction_sessions 
                SET total_patients_found = %s, successful_extractions = %s, 
                    failed_extractions = %s, conflicts_detected = %s
                WHERE id = %s
            """
            
            cursor.execute(query, (total_patients, successful, failed, conflicts, session_id))
            conn.commit()
            
        except Exception as e:
            logger.error(f"Failed to update session statistics in {provider_name}: {e}")
        finally:
            if conn.is_connected():
                cursor.close()
                conn.close()
    
    # Helper methods
    def _parse_date(self, date_str):
        """Parse date string safely"""
        if not date_str:
            return None
        try:
            # Handle different date formats
            for fmt in ['%Y-%m-%d', '%m/%d/%Y', '%d/%m/%Y']:
                try:
                    return datetime.strptime(date_str, fmt).date()
                except ValueError:
                    continue
            return None
        except:
            return None
    
    def _parse_datetime(self, datetime_str):
        """Parse datetime string safely"""
        if not datetime_str:
            return None
        try:
            return datetime.fromisoformat(datetime_str.replace('Z', '+00:00'))
        except:
            return None
    
    def _extract_medication_strength(self, medication_name: str) -> str:
        """Extract medication strength from medication name"""
        import re
        if not medication_name:
            return ''
        
        # Look for patterns like "10 mg", "0.5 mg", "100 MG", etc.
        strength_patterns = [
            r'(\d+\.?\d*\s*mg)',
            r'(\d+\.?\d*\s*MG)',
            r'(\d+\.?\d*\s*mcg)',
            r'(\d+\.?\d*\s*MCG)',
            r'(\d+\.?\d*\s*units?)',
            r'(\d+\.?\d*\s*ml)',
            r'(\d+\.?\d*\s*ML)'
        ]
        
        for pattern in strength_patterns:
            match = re.search(pattern, medication_name, re.IGNORECASE)
            if match:
                return match.group(1).strip()
        
        return ''
    
    def _extract_diagnosis_code(self, diagnosis_text: str) -> str:
        """Extract diagnosis code from diagnosis text"""
        import re
        if not diagnosis_text:
            return ''
        
        # Look for ICD-10 codes like (M10.079), (G89.4), etc.
        code_match = re.search(r'\(([A-Z]\d+\.?\d*)\)', diagnosis_text)
        if code_match:
            return code_match.group(1)
        
        return ''
    
    def get_provider_statistics(self, provider_name: str = None) -> Dict[str, Any]:
        """Get statistics for a specific provider or all providers"""
        if provider_name:
            try:
                conn = get_provider_connection(provider_name)
                cursor = conn.cursor(dictionary=True)
                
                # Get basic counts
                cursor.execute("SELECT COUNT(*) as patient_count FROM patients")
                patient_count = cursor.fetchone()['patient_count']
                
                cursor.execute("SELECT COUNT(*) as session_count FROM extraction_sessions")
                session_count = cursor.fetchone()['session_count']
                
                cursor.execute("SELECT COUNT(*) as conflict_count FROM data_conflicts WHERE status = 'unresolved'")
                conflict_count = cursor.fetchone()['conflict_count']
                
                return {
                    'provider_name': provider_name,
                    'database_name': self.db_manager.get_provider_database_name(provider_name),
                    'total_patients': patient_count,
                    'total_sessions': session_count,
                    'unresolved_conflicts': conflict_count
                }
                
            except Exception as e:
                logger.error(f"Failed to get statistics for {provider_name}: {e}")
                return {'error': str(e)}
            finally:
                if conn.is_connected():
                    cursor.close()
                    conn.close()
        else:
            # Get statistics for all providers
            providers = self.db_manager.list_providers()
            all_stats = []
            
            for provider in providers:
                stats = self.get_provider_statistics(provider['provider_name'])
                all_stats.append(stats)
            
            return {
                'total_providers': len(providers),
                'provider_statistics': all_stats,
                'processing_statistics': self.stats
            }

    def _create_comprehensive_patient_record(self, patient_id: int, session_id: int, 
                                           patient_data: Dict, metadata: Dict, provider_name: str) -> int:
        """Create or update comprehensive patient record organized by date range"""
        try:
            conn = get_provider_connection(provider_name)
            cursor = conn.cursor(dictionary=True)
            
            demographics = patient_data.get('demographics_printable', {})
            prn = demographics.get('prn')
            
            # Get date range and medication from metadata
            date_range_start = self._parse_date(metadata.get('start_date'))
            date_range_end = self._parse_date(metadata.get('end_date'))
            target_medication = metadata.get('medication', 'all')
            
            # Check if comprehensive record already exists for this date range
            existing_record = self._check_existing_comprehensive_record(
                prn, date_range_start, date_range_end, target_medication, provider_name
            )
            
            # Prepare comprehensive medical data
            comprehensive_data = {
                'medications': patient_data.get('all_medications', []),
                'diagnoses': patient_data.get('all_diagnoses', []),
                'allergies': patient_data.get('all_allergies', []),
                'health_concerns': patient_data.get('all_health_concerns', [])
            }
            
            # Calculate checksum for comprehensive data
            data_checksum = calculate_data_checksum(comprehensive_data)
            
            if existing_record:
                return self._handle_existing_comprehensive_record(
                    existing_record, comprehensive_data, data_checksum, 
                    session_id, patient_data, provider_name
                )
            else:
                return self._create_new_comprehensive_record(
                    patient_id, session_id, patient_data, metadata, 
                    comprehensive_data, data_checksum, provider_name
                )
                
        except Exception as e:
            logger.error(f"Failed to create comprehensive patient record in {provider_name}: {e}")
            raise
        finally:
            if conn.is_connected():
                cursor.close()
                conn.close()

    def _check_existing_comprehensive_record(self, prn: str, date_range_start, date_range_end, 
                                           target_medication: str, provider_name: str) -> Optional[Dict]:
        """Check if comprehensive record exists for same PRN and date range"""
        try:
            conn = get_provider_connection(provider_name)
            cursor = conn.cursor(dictionary=True)
            
            query = """
                SELECT id, data_checksum, record_status, all_medications, 
                       all_diagnoses, all_allergies, all_health_concerns
                FROM comprehensive_patient_records 
                WHERE prn = %s 
                AND date_range_start = %s 
                AND date_range_end = %s 
                AND target_medication = %s
                ORDER BY created_at DESC
                LIMIT 1
            """
            
            cursor.execute(query, (prn, date_range_start, date_range_end, target_medication))
            return cursor.fetchone()
            
        except Exception as e:
            logger.error(f"Error checking existing comprehensive record for PRN {prn}: {e}")
            return None
        finally:
            if conn.is_connected():
                cursor.close()
                conn.close()

    def _handle_existing_comprehensive_record(self, existing_record: Dict, new_data: Dict, 
                                            new_checksum: str, session_id: int, 
                                            patient_data: Dict, provider_name: str) -> int:
        """Handle existing comprehensive record - check for conflicts or update"""
        existing_checksum = existing_record['data_checksum']
        prn = patient_data.get('demographics_printable', {}).get('prn')
        
        if existing_checksum != new_checksum:
            # Data conflict detected for same date range
            self._log_comprehensive_data_conflict(
                existing_record['id'], prn, existing_checksum, 
                new_checksum, session_id, provider_name
            )
            
            # Mark existing record as having conflict
            self._update_comprehensive_record_status(
                existing_record['id'], 'conflict', provider_name
            )
            
            # Create new record with conflict status
            return self._create_comprehensive_record_with_conflict(
                existing_record, new_data, new_checksum, session_id, 
                patient_data, provider_name
            )
        else:
            # Data is identical - just update metadata
            self.db_manager.log_system_event('INFO', 'ComprehensiveRecord',
                                           f'Identical comprehensive data found for PRN {prn}',
                                           provider_name,
                                           {'existing_record_id': existing_record['id']})
            return existing_record['id']

    def _create_new_comprehensive_record(self, patient_id: int, session_id: int, 
                                       patient_data: Dict, metadata: Dict, 
                                       comprehensive_data: Dict, data_checksum: str, 
                                       provider_name: str) -> int:
        """Create new comprehensive patient record"""
        try:
            conn = get_provider_connection(provider_name)
            cursor = conn.cursor()
            
            demographics = patient_data.get('demographics_printable', {})
            
            query = """
                INSERT INTO comprehensive_patient_records (
                    prn, patient_id, patient_name, date_of_birth, gender, age,
                    date_range_start, date_range_end, target_medication,
                    all_medications, all_diagnoses, all_allergies, all_health_concerns,
                    extraction_session_id, data_checksum, record_status
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            
            values = (
                demographics.get('prn'),
                patient_id,
                demographics.get('patient_name'),
                self._parse_date(demographics.get('date_of_birth')),
                demographics.get('gender'),
                demographics.get('age'),
                self._parse_date(metadata.get('start_date')),
                self._parse_date(metadata.get('end_date')),
                metadata.get('medication', 'all'),
                json.dumps(comprehensive_data['medications']),
                json.dumps(comprehensive_data['diagnoses']),
                json.dumps(comprehensive_data['allergies']),
                json.dumps(comprehensive_data['health_concerns']),
                session_id,
                data_checksum,
                'active'
            )
            
            cursor.execute(query, values)
            conn.commit()
            record_id = cursor.lastrowid
            
            self.db_manager.log_system_event('INFO', 'ComprehensiveRecord',
                                           f'Created comprehensive record {record_id} for PRN {demographics.get("prn")}',
                                           provider_name,
                                           {'record_id': record_id, 'session_id': session_id})
            
            return record_id
            
        except Exception as e:
            logger.error(f"Failed to create comprehensive record in {provider_name}: {e}")
            raise
        finally:
            if conn.is_connected():
                cursor.close()
                conn.close()

    def _create_comprehensive_record_with_conflict(self, existing_record: Dict, new_data: Dict, 
                                                 new_checksum: str, session_id: int, 
                                                 patient_data: Dict, provider_name: str) -> int:
        """Create new comprehensive record when conflict detected"""
        try:
            conn = get_provider_connection(provider_name)
            cursor = conn.cursor()
            
            # Get data from existing record
            cursor.execute("SELECT * FROM comprehensive_patient_records WHERE id = %s", 
                          (existing_record['id'],))
            existing_full = cursor.fetchone()
            
            demographics = patient_data.get('demographics_printable', {})
            
            query = """
                INSERT INTO comprehensive_patient_records (
                    prn, patient_id, patient_name, date_of_birth, gender, age,
                    date_range_start, date_range_end, target_medication,
                    all_medications, all_diagnoses, all_allergies, all_health_concerns,
                    extraction_session_id, data_checksum, record_status
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            
            values = (
                demographics.get('prn'),
                existing_full[2],  # patient_id
                demographics.get('patient_name'),
                self._parse_date(demographics.get('date_of_birth')),
                demographics.get('gender'),
                demographics.get('age'),
                existing_full[7],  # date_range_start
                existing_full[8],  # date_range_end
                existing_full[9],  # target_medication
                json.dumps(new_data['medications']),
                json.dumps(new_data['diagnoses']),
                json.dumps(new_data['allergies']),
                json.dumps(new_data['health_concerns']),
                session_id,
                new_checksum,
                'conflict'
            )
            
            cursor.execute(query, values)
            conn.commit()
            record_id = cursor.lastrowid
            
            self.db_manager.log_system_event('WARNING', 'ComprehensiveRecordConflict',
                                           f'Created conflicting comprehensive record {record_id} for PRN {demographics.get("prn")}',
                                           provider_name,
                                           {'record_id': record_id, 'existing_record_id': existing_record['id']})
            
            return record_id
            
        except Exception as e:
            logger.error(f"Failed to create conflicting comprehensive record in {provider_name}: {e}")
            raise
        finally:
            if conn.is_connected():
                cursor.close()
                conn.close()

    def _log_comprehensive_data_conflict(self, existing_record_id: int, prn: str, 
                                       old_checksum: str, new_checksum: str, 
                                       session_id: int, provider_name: str):
        """Log data conflict for comprehensive records"""
        try:
            conn = get_provider_connection(provider_name)
            cursor = conn.cursor()
            
            query = """
                INSERT INTO data_conflicts (
                    patient_id, prn, conflict_type, extraction_session_id_1, 
                    extraction_session_id_2, field_name, conflict_description,
                    severity, status
                ) VALUES (
                    (SELECT patient_id FROM comprehensive_patient_records WHERE id = %s),
                    %s, 'data_changed', 
                    (SELECT extraction_session_id FROM comprehensive_patient_records WHERE id = %s),
                    %s, 'comprehensive_medical_data',
                    'Comprehensive medical data changed for same date range',
                    'medium', 'unresolved'
                )
            """
            
            cursor.execute(query, (existing_record_id, prn, existing_record_id, session_id))
            conn.commit()
            
        except Exception as e:
            logger.error(f"Failed to log comprehensive data conflict in {provider_name}: {e}")
        finally:
            if conn.is_connected():
                cursor.close()
                conn.close()

    def _update_comprehensive_record_status(self, record_id: int, status: str, provider_name: str):
        """Update status of comprehensive record"""
        try:
            conn = get_provider_connection(provider_name)
            cursor = conn.cursor()
            
            cursor.execute("""
                UPDATE comprehensive_patient_records 
                SET record_status = %s, updated_at = CURRENT_TIMESTAMP 
                WHERE id = %s
            """, (status, record_id))
            
            conn.commit()
            
        except Exception as e:
            logger.error(f"Failed to update comprehensive record status in {provider_name}: {e}")
        finally:
            if conn.is_connected():
                cursor.close()
                conn.close()

# Global instance
provider_processor = ProviderDataProcessor()

def process_json_file(filepath: str) -> Dict[str, Any]:
    """
    Process a JSON file with provider separation (legacy compatibility)
    
    Args:
        filepath: Path to JSON file
        
    Returns:
        Processing results
    """
    return provider_processor.process_json_file(filepath) 