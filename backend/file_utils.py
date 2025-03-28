"""
File Utilities for WebAutoDash
Provides consistent file path resolution and filename generation across all components
"""

import os
import json
import hashlib
import re
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional, List, Tuple
import logging

logger = logging.getLogger(__name__)

class WebAutoDashPaths:
    """Centralized path management for WebAutoDash"""
    
    @staticmethod
    def get_project_root() -> Path:
        """Get the absolute path to the WebAutoDash project root"""
        # Start from this file's location and go up to find project root
        current_file = Path(__file__).resolve()
        
        # Look for project markers
        for parent in current_file.parents:
            if (parent / "start_webautodash.sh").exists() or \
               (parent / "portal_adapters").exists() or \
               (parent / "README.md").exists():
                return parent
        
        # Fallback: assume this file is in backend/ under project root
        return current_file.parent.parent
    
    @staticmethod
    def get_results_dir() -> Path:
        """Get the absolute path to the Results directory"""
        return WebAutoDashPaths.get_project_root() / "Results"
    
    @staticmethod
    def get_checkpoints_dir() -> Path:
        """Get the absolute path to the checkpoints directory"""
        return WebAutoDashPaths.get_results_dir() / "checkpoints"
    
    @staticmethod
    def get_doctor_results_dir(doctor_name: str) -> Path:
        """Get the absolute path to a doctor's results directory"""
        sanitized_name = FileNameUtils.sanitize_doctor_name(doctor_name)
        doctor_dir = WebAutoDashPaths.get_results_dir() / sanitized_name
        doctor_dir.mkdir(parents=True, exist_ok=True)
        return doctor_dir
    
    @staticmethod
    def get_doctor_checkpoints_dir(doctor_name: str) -> Path:
        """Get the absolute path to a doctor's checkpoint directory"""
        sanitized_name = FileNameUtils.sanitize_doctor_name(doctor_name)
        checkpoint_dir = WebAutoDashPaths.get_checkpoints_dir() / sanitized_name
        checkpoint_dir.mkdir(parents=True, exist_ok=True)
        return checkpoint_dir

class FileNameUtils:
    """Utilities for consistent filename generation"""
    
    @staticmethod
    def sanitize_doctor_name(doctor_name: str) -> str:
        """Sanitize doctor name for use in directory/file names"""
        if not doctor_name:
            return "unknown_provider"
        
        # Convert to lowercase and replace spaces/special chars with underscores
        sanitized = re.sub(r'[^\w\-.]', '_', doctor_name.lower())
        sanitized = re.sub(r'_+', '_', sanitized)  # Remove multiple underscores
        sanitized = sanitized.strip('_')  # Remove leading/trailing underscores
        
        return sanitized if sanitized else "unknown_provider"
    
    @staticmethod
    def create_job_fingerprint(config: Dict[str, Any]) -> str:
        """Create consistent job fingerprint for matching extraction jobs"""
        # Extract key parameters that define unique extraction jobs
        key_params = {
            'doctor_name': str(config.get('doctor_name', '')).strip().lower(),
            'medication': str(config.get('medication', '')).strip().lower(),
            'start_date': str(config.get('start_date', '')),
            'stop_date': str(config.get('stop_date', '')),
            'end_date': str(config.get('end_date', '')),  # Handle both variations
            'extraction_mode': str(config.get('extraction_mode', '')),
            'target_patient_name': str(config.get('target_patient_name', '')).strip().lower(),
            'input_patient_identifier': str(config.get('input_patient_identifier', '')).strip().lower()
        }
        
        # Normalize date fields (handle both stop_date and end_date)
        if not key_params['stop_date'] and key_params['end_date']:
            key_params['stop_date'] = key_params['end_date']
        
        # Create deterministic hash
        fingerprint_str = json.dumps(key_params, sort_keys=True)
        fingerprint = hashlib.md5(fingerprint_str.encode()).hexdigest()[:12]
        
        logger.debug(f"🔍 Job fingerprint created: {fingerprint} for params: {key_params}")
        return fingerprint
    
    @staticmethod
    def generate_consistent_filename(config: Dict[str, Any], job_fingerprint: str = None) -> str:
        """Generate consistent filename for extraction results"""
        if not job_fingerprint:
            job_fingerprint = FileNameUtils.create_job_fingerprint(config)
        
        doctor_name = FileNameUtils.sanitize_doctor_name(config.get('doctor_name', 'unknown'))
        extraction_mode = config.get('extraction_mode', 'all_patients').lower().replace(' ', '_')
        date_str = datetime.now().strftime('%Y%m%d')
        
        # Create filename: {doctor}_{adapter}_{mode}_{date}_{fingerprint}.json
        filename = f"{doctor_name}_extraction_{extraction_mode}_{date_str}_{job_fingerprint[:8]}.json"
        
        logger.debug(f"📁 Generated consistent filename: {filename}")
        return filename
    
    @staticmethod
    def find_existing_result_files(config: Dict[str, Any], job_fingerprint: str = None) -> List[Path]:
        """Find existing result files for the same job parameters"""
        if not job_fingerprint:
            job_fingerprint = FileNameUtils.create_job_fingerprint(config)
        
        doctor_dir = WebAutoDashPaths.get_doctor_results_dir(config.get('doctor_name', 'unknown'))
        fingerprint_pattern = job_fingerprint[:8]
        
        matching_files = []
        
        # Search for files with matching fingerprint
        for file_path in doctor_dir.glob("*.json"):
            if fingerprint_pattern in file_path.name:
                matching_files.append(file_path)
        
        # Sort by modification time (newest first)
        matching_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
        
        if matching_files:
            logger.info(f"✅ Found {len(matching_files)} existing result files with fingerprint {fingerprint_pattern}")
        else:
            logger.info(f"📁 No existing result files found for fingerprint {fingerprint_pattern}")
        
        return matching_files

class AtomicFileOperations:
    """Atomic file operations to prevent corruption and data loss"""
    
    @staticmethod
    def atomic_write_json(file_path: Path, data: Any, backup: bool = True) -> bool:
        """
        Atomically write JSON data to file with optional backup
        
        Args:
            file_path: Target file path
            data: Data to write
            backup: Whether to create backup of existing file
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Create backup if requested and file exists
            if backup and file_path.exists():
                backup_path = file_path.with_suffix(f".backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
                file_path.replace(backup_path)
                logger.info(f"💾 Created backup: {backup_path}")
            
            # Write to temporary file first
            temp_path = file_path.with_suffix('.tmp')
            with open(temp_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, default=str, ensure_ascii=False)
            
            # Atomic move to final location
            temp_path.replace(file_path)
            
            logger.info(f"✅ Atomically wrote file: {file_path}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to write file {file_path}: {e}")
            if temp_path.exists():
                temp_path.unlink()  # Clean up temp file
            return False
    
    @staticmethod
    def merge_patient_results(existing_data: List[Dict], new_data: List[Dict]) -> Tuple[List[Dict], Dict]:
        """
        Merge patient results, preserving successful extractions and updating failed ones
        
        Args:
            existing_data: Previously extracted patient data
            new_data: Newly extracted patient data
            
        Returns:
            Tuple of (merged_data, merge_stats)
        """
        from .enhanced_resume_utils import is_extraction_truly_successful
        
        # Create lookup for existing patients
        existing_patients = {}
        for patient in existing_data:
            patient_name = patient.get('patient_name', '').strip().lower()
            if patient_name:
                existing_patients[patient_name] = patient
        
        merged_patients = []
        merge_stats = {
            'total_existing': len(existing_data),
            'total_new': len(new_data),
            'preserved_successful': 0,
            'updated_failed': 0,
            'added_new': 0
        }
        
        # Start with all existing patients
        for patient in existing_data:
            patient_name = patient.get('patient_name', '').strip().lower()
            
            # Check if we have new data for this patient
            new_patient = None
            for new_p in new_data:
                if new_p.get('patient_name', '').strip().lower() == patient_name:
                    new_patient = new_p
                    break
            
            if new_patient:
                # Decide whether to keep existing or use new
                existing_success = is_extraction_truly_successful(patient)
                new_success = is_extraction_truly_successful(new_patient)
                
                if existing_success and not new_success:
                    # Keep successful existing extraction
                    merged_patients.append(patient)
                    merge_stats['preserved_successful'] += 1
                    logger.debug(f"✅ Preserved successful: {patient_name}")
                else:
                    # Use new extraction (better or replacing failed)
                    merged_patients.append(new_patient)
                    merge_stats['updated_failed'] += 1
                    logger.debug(f"🔄 Updated: {patient_name}")
            else:
                # No new data, keep existing
                merged_patients.append(patient)
                if is_extraction_truly_successful(patient):
                    merge_stats['preserved_successful'] += 1
        
        # Add completely new patients
        existing_names = {p.get('patient_name', '').strip().lower() for p in existing_data}
        for new_patient in new_data:
            new_name = new_patient.get('patient_name', '').strip().lower()
            if new_name not in existing_names:
                merged_patients.append(new_patient)
                merge_stats['added_new'] += 1
                logger.debug(f"🆕 Added new: {new_name}")
        
        return merged_patients, merge_stats

# Global utilities for easy import
def get_consistent_result_file_path(config: Dict[str, Any], job_fingerprint: str = None) -> Path:
    """Get consistent file path for result storage"""
    if not job_fingerprint:
        job_fingerprint = FileNameUtils.create_job_fingerprint(config)
    
    doctor_dir = WebAutoDashPaths.get_doctor_results_dir(config.get('doctor_name', 'unknown'))
    filename = FileNameUtils.generate_consistent_filename(config, job_fingerprint)
    
    return doctor_dir / filename

def save_extraction_results(config: Dict[str, Any], results: List[Dict], 
                          merge_with_existing: bool = True) -> Tuple[bool, Path, Dict]:
    """
    Save extraction results with optional merging
    
    Args:
        config: Job configuration
        results: Patient extraction results
        merge_with_existing: Whether to merge with existing files
        
    Returns:
        Tuple of (success, file_path, stats)
    """
    try:
        job_fingerprint = FileNameUtils.create_job_fingerprint(config)
        target_file = get_consistent_result_file_path(config, job_fingerprint)
        
        final_results = results
        merge_stats = {'operation': 'new_file'}
        
        if merge_with_existing and target_file.exists():
            # Load existing data and merge
            with open(target_file, 'r', encoding='utf-8') as f:
                existing_data = json.load(f)
            
            # Handle different data formats
            if isinstance(existing_data, dict):
                if 'extraction_results' in existing_data:
                    existing_results = existing_data['extraction_results']
                elif 'patients' in existing_data:
                    existing_results = existing_data['patients']
                else:
                    existing_results = []
            elif isinstance(existing_data, list):
                existing_results = existing_data
            else:
                existing_results = []
            
            final_results, merge_stats = AtomicFileOperations.merge_patient_results(
                existing_results, results
            )
            merge_stats['operation'] = 'merged'
            
            logger.info(f"🔄 Merged results: {merge_stats}")
        
        # Prepare final data structure
        extraction_data = {
            "extraction_metadata": {
                "job_fingerprint": job_fingerprint,
                "doctor_name": config.get('doctor_name', ''),
                "extraction_mode": config.get('extraction_mode', ''),
                "medication": config.get('medication', ''),
                "start_date": config.get('start_date', ''),
                "end_date": config.get('end_date', config.get('stop_date', '')),
                "extracted_at": datetime.now().isoformat(),
                "results_filename": target_file.name,
                "total_patients": len(final_results),
                "merge_stats": merge_stats
            },
            "extraction_results": final_results
        }
        
        # Atomic write
        success = AtomicFileOperations.atomic_write_json(target_file, extraction_data)
        
        if success:
            logger.info(f"✅ Saved {len(final_results)} patients to {target_file}")
            return True, target_file, merge_stats
        else:
            return False, target_file, merge_stats
            
    except Exception as e:
        logger.error(f"❌ Failed to save extraction results: {e}")
        return False, Path(), {'error': str(e)} 