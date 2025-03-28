"""
Enhanced Resume Utilities for WebAutoDash
Provides improved patient validation and resume logic with medication-focused analysis
"""

import json
import logging
from datetime import datetime
from typing import Dict, List, Tuple, Optional, Any
from pathlib import Path

logger = logging.getLogger(__name__)

def is_extraction_truly_successful(patient_data: Dict) -> bool:
    """
    ENHANCED: Determine if patient extraction actually succeeded with comprehensive validation
    
    This function uses medication-focused validation to determine extraction success:
    - Validates extraction status
    - Checks medication data completeness and quality
    - Handles legitimate "no medications" cases
    - Validates data structure integrity
    
    Args:
        patient_data: Patient extraction data dictionary
        
    Returns:
        True if extraction was truly successful, False otherwise
    """
    try:
        patient_name = patient_data.get('patient_name', 'Unknown Patient')
        
        # 1. Must have complete extraction status
        if patient_data.get('extraction_status') != 'complete':
            logger.debug(f"❌ {patient_name}: Incomplete extraction status")
            return False
        
        # 2. Check for extraction errors
        if patient_data.get('extraction_error'):
            logger.debug(f"❌ {patient_name}: Has extraction error flag")
            return False
        
        # 3. CRITICAL: Medication data validation
        medications = patient_data.get('all_medications', [])
        
        # 3a. No medications - need to determine if legitimate
        if not medications:
            # Check for other clinical data indicators
            has_demographics = bool(patient_data.get('patient_name', '').strip())
            has_diagnoses = len(patient_data.get('all_diagnoses', [])) > 0
            has_allergies = len(patient_data.get('all_allergies', [])) > 0
            has_health_concerns = len(patient_data.get('all_health_concerns', [])) > 0
            
            # If patient has other clinical data, this might be legitimate no-medications
            if has_demographics and (has_diagnoses or has_allergies or has_health_concerns):
                logger.debug(f"ℹ️ {patient_name}: No medications but has clinical data - likely legitimate")
                return True
            else:
                logger.debug(f"❌ {patient_name}: No medications AND minimal clinical data - extraction failed")
                return False
        
        # 3b. Has medications - validate their structure and content
        valid_medications = 0
        for i, med in enumerate(medications):
            if not isinstance(med, dict):
                logger.debug(f"❌ {patient_name}: Medication {i} is not a dict")
                continue
            
            # Check for medication identification in various fields
            med_name = med.get('medication_name', '').strip()
            med_text = med.get('medication_text', '').strip()
            med_sig = med.get('sig', '').strip()
            
            # Valid medication should have at least a name or text
            if med_name or med_text:
                valid_medications += 1
                logger.debug(f"✅ {patient_name}: Valid medication {i}: {med_name or med_text}")
            else:
                logger.debug(f"⚠️ {patient_name}: Medication {i} has no name/text")
        
        # 3c. Validate that we have at least some valid medications
        if valid_medications == 0:
            logger.debug(f"❌ {patient_name}: Has medication array but no valid entries")
            return False
        
        # 4. Additional data integrity checks
        if not patient_data.get('patient_name', '').strip():
            logger.debug(f"❌ {patient_name}: Missing patient name")
            return False
        
        logger.debug(f"✅ {patient_name}: Extraction successful ({valid_medications} valid medications)")
        return True
        
    except Exception as e:
        logger.error(f"❌ Error validating extraction for {patient_data.get('patient_name', 'Unknown')}: {e}")
        return False

def analyze_extraction_completeness(results: List[Dict]) -> Dict[str, Any]:
    """
    Analyze extraction results to determine completeness and resume opportunities
    
    Args:
        results: List of patient extraction results
        
    Returns:
        Analysis dictionary with statistics and recommendations
    """
    if not results:
        return {
            'total_patients': 0,
            'successful_extractions': 0,
            'failed_extractions': 0,
            'success_rate': 0.0,
            'failed_patients': [],
            'successful_patients': [],
            'resume_recommended': False,
            'analysis_summary': 'No results to analyze'
        }
    
    successful_patients = []
    failed_patients = []
    
    # Analyze each patient
    for patient in results:
        if is_extraction_truly_successful(patient):
            successful_patients.append(patient)
        else:
            failed_patients.append(patient)
    
    total = len(results)
    successful_count = len(successful_patients)
    failed_count = len(failed_patients)
    success_rate = (successful_count / total * 100) if total > 0 else 0.0
    
    # Determine if resume is recommended (>10% failure rate or >5 failed patients)
    resume_recommended = failed_count > 0 and (
        failed_count / total > 0.1 or  # More than 10% failed
        failed_count > 5  # More than 5 failed patients
    )
    
    # Generate summary
    if failed_count == 0:
        summary = f"Perfect extraction - all {successful_count} patients successful"
    elif success_rate >= 90:
        summary = f"Excellent extraction - {success_rate:.1f}% success rate ({failed_count} need retry)"
    elif success_rate >= 75:
        summary = f"Good extraction - {success_rate:.1f}% success rate ({failed_count} need retry)"
    elif success_rate >= 50:
        summary = f"Moderate extraction - {success_rate:.1f}% success rate ({failed_count} need retry)"
    else:
        summary = f"Poor extraction - {success_rate:.1f}% success rate ({failed_count} need retry)"
    
    return {
        'total_patients': total,
        'successful_extractions': successful_count,
        'failed_extractions': failed_count,
        'success_rate': success_rate,
        'failed_patients': failed_patients,
        'successful_patients': successful_patients,
        'resume_recommended': resume_recommended,
        'estimated_time_savings': failed_count * 2,  # 2 minutes per patient estimate
        'analysis_summary': summary
    }

def identify_patients_for_retry(current_patient_list: List[Dict], 
                               previous_results: List[Dict]) -> Tuple[List[Dict], List[Dict], Dict]:
    """
    Identify which patients need re-extraction based on previous results
    
    Args:
        current_patient_list: Current list of patients to potentially extract
        previous_results: Previous extraction results
        
    Returns:
        Tuple of (patients_to_process, successfully_extracted, analysis_stats)
    """
    # Create lookup for previous results
    previous_patients = {}
    for result in previous_results:
        patient_name = result.get('patient_name', '').strip().lower()
        if patient_name:
            previous_patients[patient_name] = result
    
    patients_to_process = []
    successfully_extracted = []
    analysis_stats = {
        'total_current_patients': len(current_patient_list),
        'total_previous_results': len(previous_results),
        'patients_already_successful': 0,
        'patients_need_retry': 0,
        'patients_new': 0
    }
    
    for patient in current_patient_list:
        patient_name = patient.get('patient_name', '').strip().lower()
        
        if patient_name in previous_patients:
            previous_result = previous_patients[patient_name]
            
            if is_extraction_truly_successful(previous_result):
                # Patient was successfully extracted, skip
                successfully_extracted.append(previous_result)
                analysis_stats['patients_already_successful'] += 1
                logger.debug(f"✅ Skipping successful: {patient_name}")
            else:
                # Patient extraction failed, retry needed
                patients_to_process.append(patient)
                analysis_stats['patients_need_retry'] += 1
                logger.debug(f"🔄 Retry needed: {patient_name}")
        else:
            # New patient, needs processing
            patients_to_process.append(patient)
            analysis_stats['patients_new'] += 1
            logger.debug(f"🆕 New patient: {patient_name}")
    
    logger.info(f"📊 RETRY ANALYSIS: {analysis_stats}")
    return patients_to_process, successfully_extracted, analysis_stats

def validate_medication_data_quality(patient_data: Dict) -> Dict[str, Any]:
    """
    Detailed validation of medication data quality
    
    Args:
        patient_data: Patient extraction data
        
    Returns:
        Quality assessment dictionary
    """
    medications = patient_data.get('all_medications', [])
    patient_name = patient_data.get('patient_name', 'Unknown')
    
    if not medications:
        return {
            'has_medications': False,
            'medication_count': 0,
            'quality_score': 0.0,
            'issues': ['No medications found'],
            'recommendation': 'retry'
        }
    
    quality_issues = []
    valid_medications = 0
    total_medications = len(medications)
    
    for i, med in enumerate(medications):
        if not isinstance(med, dict):
            quality_issues.append(f"Medication {i} is not a dictionary")
            continue
        
        # Check required fields
        med_name = med.get('medication_name', '').strip()
        med_text = med.get('medication_text', '').strip()
        
        if not (med_name or med_text):
            quality_issues.append(f"Medication {i} missing name/text")
            continue
        
        # Check for common error indicators
        if any(indicator in (med_name + med_text).lower() for indicator in 
               ['error', 'failed', 'timeout', 'not found', 'unavailable']):
            quality_issues.append(f"Medication {i} contains error indicators")
            continue
        
        valid_medications += 1
    
    # Calculate quality score
    quality_score = (valid_medications / total_medications) if total_medications > 0 else 0.0
    
    # Determine recommendation
    if quality_score >= 0.8:
        recommendation = 'keep'
    elif quality_score >= 0.5:
        recommendation = 'review'
    else:
        recommendation = 'retry'
    
    return {
        'has_medications': True,
        'medication_count': total_medications,
        'valid_medication_count': valid_medications,
        'quality_score': quality_score,
        'issues': quality_issues,
        'recommendation': recommendation
    }

def find_resume_checkpoint(job_fingerprint: str, checkpoints_dir: Path) -> Optional[Dict]:
    """
    Find the most recent checkpoint for a given job fingerprint
    
    Args:
        job_fingerprint: Unique job identifier
        checkpoints_dir: Directory containing checkpoint files
        
    Returns:
        Checkpoint data dictionary or None if not found
    """
    try:
        if not checkpoints_dir.exists():
            logger.info(f"📁 No checkpoints directory: {checkpoints_dir}")
            return None
        
        matching_checkpoints = []
        
        # Search all checkpoint files
        for checkpoint_file in checkpoints_dir.glob("*.json"):
            try:
                with open(checkpoint_file, 'r', encoding='utf-8') as f:
                    checkpoint_data = json.load(f)
                
                # Check if fingerprint matches
                checkpoint_fingerprint = checkpoint_data.get('job_fingerprint')
                if checkpoint_fingerprint == job_fingerprint:
                    checkpoint_data['file_path'] = checkpoint_file
                    matching_checkpoints.append(checkpoint_data)
                    
            except Exception as e:
                logger.warning(f"⚠️ Failed to read checkpoint {checkpoint_file}: {e}")
                continue
        
        if not matching_checkpoints:
            logger.info(f"📁 No matching checkpoints found for fingerprint {job_fingerprint}")
            return None
        
        # Sort by timestamp and return most recent
        matching_checkpoints.sort(
            key=lambda x: x.get('timestamp', ''), 
            reverse=True
        )
        
        latest_checkpoint = matching_checkpoints[0]
        logger.info(f"✅ Found latest checkpoint: {latest_checkpoint.get('timestamp')}")
        
        return latest_checkpoint
        
    except Exception as e:
        logger.error(f"❌ Error finding resume checkpoint: {e}")
        return None

def create_resume_plan(config: Dict[str, Any], current_patients: List[Dict], 
                      existing_results: Optional[List[Dict]] = None) -> Dict[str, Any]:
    """
    Create comprehensive resume plan for extraction job
    
    Args:
        config: Job configuration
        current_patients: Current patient list from portal
        existing_results: Previous extraction results (if any)
        
    Returns:
        Resume plan with all necessary information
    """
    from .file_utils import FileNameUtils, WebAutoDashPaths
    
    # Create job fingerprint
    job_fingerprint = FileNameUtils.create_job_fingerprint(config)
    
    # Find existing results if not provided
    if existing_results is None:
        existing_files = FileNameUtils.find_existing_result_files(config, job_fingerprint)
        if existing_files:
            try:
                with open(existing_files[0], 'r', encoding='utf-8') as f:
                    data = json.load(f)
                if isinstance(data, dict) and 'extraction_results' in data:
                    existing_results = data['extraction_results']
                elif isinstance(data, list):
                    existing_results = data
                else:
                    existing_results = []
            except Exception as e:
                logger.warning(f"⚠️ Failed to load existing results: {e}")
                existing_results = []
        else:
            existing_results = []
    
    # Analyze existing results
    if existing_results:
        analysis = analyze_extraction_completeness(existing_results)
        patients_to_process, successful_patients, retry_stats = identify_patients_for_retry(
            current_patients, existing_results
        )
    else:
        analysis = {'total_patients': 0, 'successful_extractions': 0, 'failed_extractions': 0}
        patients_to_process = current_patients
        successful_patients = []
        retry_stats = {
            'total_current_patients': len(current_patients),
            'patients_already_successful': 0,
            'patients_need_retry': 0,
            'patients_new': len(current_patients)
        }
    
    # Find checkpoint
    checkpoints_dir = WebAutoDashPaths.get_doctor_checkpoints_dir(config.get('doctor_name', 'unknown'))
    checkpoint = find_resume_checkpoint(job_fingerprint, checkpoints_dir)
    
    resume_plan = {
        'job_fingerprint': job_fingerprint,
        'can_resume': len(patients_to_process) > 0,
        'resume_recommended': analysis.get('resume_recommended', False),
        'existing_analysis': analysis,
        'retry_statistics': retry_stats,
        'patients_to_process': patients_to_process,
        'successful_patients': successful_patients,
        'checkpoint_available': checkpoint is not None,
        'checkpoint_data': checkpoint,
        'estimated_time_savings': len(successful_patients) * 2,  # 2 minutes per skipped patient
        'config': config
    }
    
    # Generate summary message
    if len(successful_patients) > 0:
        resume_plan['summary'] = (
            f"Resume available: {len(successful_patients)} patients already successful, "
            f"{len(patients_to_process)} need processing. "
            f"Estimated time savings: {resume_plan['estimated_time_savings']} minutes."
        )
    else:
        resume_plan['summary'] = f"New extraction: {len(patients_to_process)} patients to process."
    
    logger.info(f"📋 RESUME PLAN: {resume_plan['summary']}")
    return resume_plan 