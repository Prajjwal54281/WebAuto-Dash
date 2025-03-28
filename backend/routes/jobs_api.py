from flask import Blueprint, request, jsonify, current_app
from models import db, PortalAdapter, ExtractionJob
from datetime import datetime
import sys
import os
from pathlib import Path
import json
import os
from sqlalchemy import text

# Add the project root to the Python path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

# Import our enhanced utilities
from backend.file_utils import (
    FileNameUtils, 
    WebAutoDashPaths, 
    get_consistent_result_file_path,
    save_extraction_results
)
from backend.enhanced_resume_utils import (
    is_extraction_truly_successful,
    analyze_extraction_completeness,
    create_resume_plan
)

jobs_bp = Blueprint('jobs', __name__)

@jobs_bp.route('/health', methods=['GET'])
def health_check():
    """Simple health check endpoint for monitoring system status"""
    try:
        # Quick database connectivity test
        db.session.execute(text('SELECT 1')).fetchone()
        
        return jsonify({
            'success': True,
            'status': 'healthy',
            'timestamp': datetime.utcnow().isoformat(),
            'database': 'connected'
        }), 200
    except Exception as e:
        return jsonify({
            'success': False,
            'status': 'unhealthy',
            'error': str(e),
            'timestamp': datetime.utcnow().isoformat(),
            'database': 'disconnected'
        }), 500

@jobs_bp.route('/adapters', methods=['GET'])
def get_adapters():
    """Get all active portal adapters"""
    try:
        adapters = PortalAdapter.query.filter_by(is_active=True).all()
        return jsonify({
            'success': True,
            'adapters': [adapter.to_dict() for adapter in adapters]
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Failed to fetch adapters: {str(e)}'
        }), 500

@jobs_bp.route('/jobs', methods=['POST'])
def create_job():
    """Create a new extraction job"""
    try:
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['target_url', 'adapter_id', 'extraction_mode']
        for field in required_fields:
            if field not in data:
                return jsonify({
                    'success': False,
                    'error': f'Missing required field: {field}'
                }), 400
        
        # Validate extraction_mode
        if data['extraction_mode'] not in ['SINGLE_PATIENT', 'ALL_PATIENTS']:
            return jsonify({
                'success': False,
                'error': 'extraction_mode must be SINGLE_PATIENT or ALL_PATIENTS'
            }), 400
        
        # Validate patient_identifier for single patient mode
        if data['extraction_mode'] == 'SINGLE_PATIENT':
            if not data.get('input_patient_identifier'):
                return jsonify({
                    'success': False,
                    'error': 'input_patient_identifier is required for SINGLE_PATIENT mode'
                }), 400
        
        # Verify adapter exists and is active
        adapter = PortalAdapter.query.filter_by(
            id=data['adapter_id'], 
            is_active=True
        ).first()
        
        if not adapter:
            return jsonify({
                'success': False,
                'error': 'Invalid or inactive adapter_id'
            }), 400
        
        # Parse dates if provided
        from datetime import datetime
        start_date = None
        end_date = None
        
        if data.get('start_date'):
            try:
                start_date = datetime.strptime(data['start_date'], '%Y-%m-%d').date()
            except ValueError:
                return jsonify({
                    'success': False,
                    'error': 'Invalid start_date format. Use YYYY-MM-DD'
                }), 400
        
        if data.get('end_date'):
            try:
                end_date = datetime.strptime(data['end_date'], '%Y-%m-%d').date()
            except ValueError:
                return jsonify({
                    'success': False,
                    'error': 'Invalid end_date format. Use YYYY-MM-DD'
                }), 400
        
        # Create extraction job
        job = ExtractionJob(
            job_name=data.get('job_name'),  # Optional custom job name
            target_url=data['target_url'],
            portal_adapter_id=data['adapter_id'],
            extraction_mode=data['extraction_mode'],
            input_patient_identifier=data.get('input_patient_identifier'),
            doctor_name=data.get('doctor_name'),
            medication=data.get('medication'),
            start_date=start_date,
            end_date=end_date,
            status='PENDING_LOGIN'
        )
        
        db.session.add(job)
        db.session.commit()
        
        # Start the job with Playwright orchestrator
        try:
            from playwright_orchestrator.orchestrator import PlaywrightSessionManager
            
            session_manager = PlaywrightSessionManager()
            
            # Create a proper app context factory
            def app_context_factory():
                return current_app._get_current_object().app_context()
            
            # Extract job_parameters from the request data
            job_parameters = data.get('job_parameters', {})
            
            # Ensure job_parameters is a dictionary
            if not isinstance(job_parameters, dict):
                job_parameters = {}
            
            # Add fallback parameters from direct fields if job_parameters is empty
            if not job_parameters:
                job_parameters = {
                    'doctor_name': data.get('doctor_name', ''),
                    'medication': data.get('medication', ''),
                    'start_date': data.get('start_date', ''),
                    'stop_date': data.get('end_date', ''),  # Note: frontend sends end_date, adapter expects stop_date
                    'extraction_mode': data['extraction_mode']
                }
            
            job_started = session_manager.start_job(
                job_id=job.id,
                target_url=job.target_url,
                adapter_script_path=adapter.script_filename,
                mode=job.extraction_mode,
                patient_identifier=job.input_patient_identifier,
                job_parameters=job_parameters,
                app_context_factory=app_context_factory
            )
            
            if not job_started:
                job.status = 'FAILED'
                job.error_message = 'Failed to start Playwright session'
                db.session.commit()
                
                return jsonify({
                    'success': False,
                    'error': 'Failed to start extraction job'
                }), 500
            
        except Exception as playwright_error:
            job.status = 'FAILED'
            job.error_message = f'Playwright orchestrator error: {str(playwright_error)}'
            db.session.commit()
            
            return jsonify({
                'success': False,
                'error': f'Failed to start Playwright session: {str(playwright_error)}'
            }), 500
        
        return jsonify({
            'success': True,
            'job': job.to_dict()
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': f'Failed to create job: {str(e)}'
        }), 500

@jobs_bp.route('/jobs/<int:job_id>/confirm_login', methods=['POST'])
def confirm_login(job_id):
    """Confirm that user has logged in to the portal"""
    try:
        # Verify job exists
        job = ExtractionJob.query.get(job_id)
        if not job:
            return jsonify({
                'success': False,
                'error': 'Job not found'
            }), 404
        
        # Check if job is in the correct status
        if job.status != 'AWAITING_USER_CONFIRMATION':
            return jsonify({
                'success': False,
                'error': f'Job is not awaiting confirmation. Current status: {job.status}'
            }), 400
        
        # Signal the Playwright orchestrator
        try:
            from playwright_orchestrator.orchestrator import PlaywrightSessionManager
            
            session_manager = PlaywrightSessionManager()
            confirmation_sent = session_manager.signal_login_confirmed(job_id)
            
            if not confirmation_sent:
                return jsonify({
                    'success': False,
                    'error': 'Failed to signal login confirmation - job may not be active'
                }), 400
            
            return jsonify({
                'success': True,
                'message': 'Login confirmation sent successfully'
            })
            
        except Exception as playwright_error:
            return jsonify({
                'success': False,
                'error': f'Failed to signal confirmation: {str(playwright_error)}'
            }), 500
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Failed to confirm login: {str(e)}'
        }), 500

@jobs_bp.route('/jobs/<int:job_id>', methods=['GET'])
def get_job(job_id):
    """Get details of a specific job"""
    try:
        job = ExtractionJob.query.get(job_id)
        if not job:
            return jsonify({
                'success': False,
                'error': 'Job not found'
            }), 404
        
        return jsonify({
            'success': True,
            'job': job.to_dict()
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Failed to fetch job: {str(e)}'
        }), 500

@jobs_bp.route('/jobs/<int:job_id>', methods=['DELETE'])
def delete_job(job_id):
    """Delete a specific job"""
    try:
        job = ExtractionJob.query.get(job_id)
        if not job:
            return jsonify({
                'success': False,
                'error': 'Job not found'
            }), 404
        
        # Check if job is currently active and stop it if needed
        if job.status in ['PENDING_LOGIN', 'AWAITING_USER_CONFIRMATION', 'EXTRACTING']:
            try:
                from playwright_orchestrator.orchestrator import PlaywrightSessionManager
                session_manager = PlaywrightSessionManager()
                session_manager.stop_job(job_id)
            except Exception as e:
                current_app.logger.warning(f'Failed to stop active job {job_id}: {str(e)}')
        
        # Delete the job from database
        db.session.delete(job)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'Job {job_id} deleted successfully'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': f'Failed to delete job: {str(e)}'
        }), 500

@jobs_bp.route('/jobs', methods=['GET'])
def get_jobs():
    """Get paginated list of all jobs with optimized queries"""
    try:
        # Get pagination parameters
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        
        # Limit per_page to prevent abuse
        per_page = min(per_page, 100)
        
        # Get jobs with pagination AND eager loading of adapters to prevent N+1 queries
        jobs_query = ExtractionJob.query.options(
            db.joinedload(ExtractionJob.adapter)
        ).order_by(ExtractionJob.created_at.desc())
        
        jobs_pagination = jobs_query.paginate(
            page=page, 
            per_page=per_page, 
            error_out=False
        )
        
        return jsonify({
            'success': True,
            'jobs': [job.to_dict() for job in jobs_pagination.items],
            'pagination': {
                'page': page,
                'pages': jobs_pagination.pages,
                'per_page': per_page,
                'total': jobs_pagination.total,
                'has_next': jobs_pagination.has_next,
                'has_prev': jobs_pagination.has_prev
            }
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Failed to fetch jobs: {str(e)}'
        }), 500

@jobs_bp.route('/jobs/active', methods=['GET'])
def get_active_jobs():
    """Get currently active jobs from the Playwright orchestrator"""
    try:
        from playwright_orchestrator.orchestrator import PlaywrightSessionManager
        
        session_manager = PlaywrightSessionManager()
        active_jobs = session_manager.get_active_jobs()
        
        return jsonify({
            'success': True,
            'active_jobs': active_jobs
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Failed to fetch active jobs: {str(e)}'
        }), 500 

class ResultsAnalyzer:
    """ENHANCED: Analyze extraction results for resume opportunities using new utilities"""
    
    def __init__(self, job):
        self.job = job
        
    def analyze_medication_completeness(self):
        """ENHANCED: Analyze job results using improved utilities"""
        try:
            # Create job config for file utilities
            job_config = {
                'doctor_name': self.job.doctor_name or 'unknown',
                'medication': self.job.medication or '',
                'start_date': self.job.start_date.strftime('%Y-%m-%d') if self.job.start_date else '',
                'end_date': self.job.end_date.strftime('%Y-%m-%d') if self.job.end_date else '',
                'extraction_mode': self.job.extraction_mode or 'ALL_PATIENTS'
            }
            
            # Use enhanced file utilities to find result files
            job_fingerprint = FileNameUtils.create_job_fingerprint(job_config)
            existing_files = FileNameUtils.find_existing_result_files(job_config, job_fingerprint)
            
            if not existing_files:
                return {
                    'total': 0,
                    'successful': 0,
                    'failed': 0,
                    'can_resume': False,
                    'reason': 'No result files found'
                }
            
            # Load the most recent file
            latest_file = existing_files[0]  # Already sorted by modification time
            
            with open(latest_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Handle different data formats using enhanced utilities
            if isinstance(data, dict):
                if 'extraction_results' in data:
                    results = data['extraction_results']
                elif 'patients' in data:
                    results = data['patients']
                else:
                    results = []
            elif isinstance(data, list):
                results = data
            else:
                results = []
            
            if not results:
                return {
                    'total': 0,
                    'successful': 0,
                    'failed': 0,
                    'can_resume': False,
                    'reason': 'No patient data found in results file'
                }
            
            # Use enhanced analysis utilities
            analysis = analyze_extraction_completeness(results)
            
            return {
                'total': analysis['total_patients'],
                'successful': analysis['successful_extractions'],
                'failed': analysis['failed_extractions'],
                'success_rate': analysis['success_rate'],
                'can_resume': analysis['failed_extractions'] > 0,
                'time_savings': analysis['estimated_time_savings'],
                'result_file': str(latest_file),
                'reason': analysis['analysis_summary'],
                'resume_recommended': analysis['resume_recommended']
            }
            
        except Exception as e:
            current_app.logger.error(f"❌ Error analyzing results: {e}")
            return {
                'total': 0,
                'successful': 0,
                'failed': 0,
                'can_resume': False,
                'error': str(e)
            }

@jobs_bp.route('/jobs/<int:job_id>/resume-analysis', methods=['GET'])
def analyze_job_resume_status(job_id):
    """Analyze job results for resume opportunities"""
    try:
        job = ExtractionJob.query.get(job_id)
        if not job:
            return jsonify({'success': False, 'error': 'Job not found'}), 404
        
        # Load result file and analyze
        results_analyzer = ResultsAnalyzer(job)
        analysis = results_analyzer.analyze_medication_completeness()
        
        return jsonify({
            'success': True,
            'analysis': {
                'total_patients': analysis['total'],
                'successful_medications': analysis['successful'],
                'incomplete_medications': analysis['failed'],
                'success_rate': analysis.get('success_rate', 0),
                'can_resume': analysis['failed'] > 0,
                'resume_recommended': analysis['failed'] > analysis['successful'] * 0.1,  # >10% failed
                'estimated_time_savings': analysis.get('time_savings', 0),
                'result_file': analysis.get('result_file', ''),
                'reason': analysis.get('reason', '')
            }
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@jobs_bp.route('/jobs/<int:job_id>/retry', methods=['POST'])
def retry_job_with_resume(job_id):
    """ENHANCED: Retry job with enhanced resume capability"""
    try:
        data = request.get_json() or {}
        retry_mode = data.get('mode', 'resume')  # 'resume' or 'restart'
        
        job = ExtractionJob.query.get(job_id)
        if not job:
            return jsonify({'success': False, 'error': 'Job not found'}), 404
        
        # Create job config for enhanced utilities
        job_config = {
            'doctor_name': job.doctor_name or 'unknown',
            'medication': job.medication or '',
            'start_date': job.start_date.strftime('%Y-%m-%d') if job.start_date else '',
            'end_date': job.end_date.strftime('%Y-%m-%d') if job.end_date else '',
            'extraction_mode': job.extraction_mode or 'ALL_PATIENTS',
            'input_patient_identifier': job.input_patient_identifier or ''
        }
        
        # Generate job fingerprint for consistent file handling
        job_fingerprint = FileNameUtils.create_job_fingerprint(job_config)
        
        # Create new job with enhanced resume parameters
        retry_job = ExtractionJob(
            job_name=f"{job.job_name} (Resume)" if retry_mode == 'resume' else f"{job.job_name} (Restart)",
            target_url=job.target_url,
            portal_adapter_id=job.portal_adapter_id,
            extraction_mode=job.extraction_mode,
            input_patient_identifier=job.input_patient_identifier,
            doctor_name=job.doctor_name,
            medication=job.medication,
            start_date=job.start_date,
            end_date=job.end_date,
            status='PENDING_LOGIN'
        )
        
        db.session.add(retry_job)
        db.session.commit()
        
        # Start retry with enhanced resume mode
        from playwright_orchestrator.orchestrator import PlaywrightSessionManager
        session_manager = PlaywrightSessionManager()
        
        job_parameters = {
            'doctor_name': job.doctor_name,
            'medication': job.medication,
            'start_date': job.start_date.isoformat() if job.start_date else '',
            'stop_date': job.end_date.isoformat() if job.end_date else '',
            'end_date': job.end_date.isoformat() if job.end_date else '',  # Handle both variations
            'extraction_mode': job.extraction_mode,
            'input_patient_identifier': job.input_patient_identifier or '',
            'resume_mode': retry_mode,  # 'resume' or 'restart'
            'original_job_id': job_id,
            'job_fingerprint': job_fingerprint,  # NEW: For enhanced file handling
            'enhanced_resume': True  # NEW: Enable enhanced resume features
        }
        
        # Get adapter from database
        adapter = PortalAdapter.query.get(job.portal_adapter_id)
        adapter_script = adapter.script_filename if adapter else 'example_adapter.py'
        
        job_started = session_manager.start_job(
            job_id=retry_job.id,
            target_url=retry_job.target_url,
            adapter_script_path=adapter_script,
            mode=retry_job.extraction_mode,
            patient_identifier=retry_job.input_patient_identifier,
            job_parameters=job_parameters,
            app_context_factory=lambda: current_app._get_current_object().app_context()
        )
        
        if job_started:
            current_app.logger.info(f"✅ Started enhanced retry job {retry_job.id} with mode: {retry_mode}")
            return jsonify({
                'success': True,
                'retry_job_id': retry_job.id,
                'job_fingerprint': job_fingerprint,
                'message': f'Enhanced job retry started with mode: {retry_mode}',
                'retry_mode': retry_mode
            })
        else:
            retry_job.status = 'FAILED'
            retry_job.error_message = 'Failed to start enhanced retry session'
            db.session.commit()
            return jsonify({'success': False, 'error': 'Failed to start enhanced retry'}), 500
            
    except Exception as e:
        current_app.logger.error(f"❌ Error starting retry job: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500