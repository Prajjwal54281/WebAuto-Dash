"""
Real-time API for WebAutoDash
Provides real-time updates, enhanced job management, and system monitoring
"""

from flask import Blueprint, request, jsonify, current_app
from flask_socketio import emit
from models import db, ExtractionJob, PortalAdapter
from datetime import datetime, timedelta
import json
import threading
import time
import logging
from sqlalchemy import text

logger = logging.getLogger(__name__)

realtime_bp = Blueprint('realtime', __name__)

# Global job progress tracking
job_progress = {}
system_stats = {
    'active_jobs': 0,
    'completed_jobs': 0,
    'failed_jobs': 0,
    'system_health': 'healthy',
    'last_updated': datetime.now().isoformat()
}

# Global SocketIO instance
socketio_instance = None

def init_socketio(socketio):
    """Initialize SocketIO instance for real-time features"""
    global socketio_instance
    socketio_instance = socketio
    logger.info("✅ SocketIO initialized for real-time features")
    
    # Start system monitoring
    start_system_monitor()
    
    @socketio.on('connect')
    def handle_connect():
        logger.info("Client connected to SocketIO")
        emit('connected', {'message': 'Connected to WebAutoDash real-time updates'})
    
    @socketio.on('disconnect')
    def handle_disconnect():
        logger.info("Client disconnected from SocketIO")
    
    @socketio.on('subscribe_job_updates')
    def handle_job_subscription(data):
        logger.info(f"Client subscribed to job updates: {data}")
        emit('subscription_confirmed', {'type': 'job_updates'})
    
    @socketio.on('subscribe_portal_analysis')
    def handle_portal_analysis_subscription(data):
        logger.info(f"Client subscribed to portal analysis updates: {data}")
        emit('subscription_confirmed', {'type': 'portal_analysis'})

def extract_job_parameters(job):
    """Extract job parameters from database record for adapter"""
    try:
        job_parameters = {}
        
        # Required parameters for comprehensive adapter
        if job.doctor_name:
            job_parameters['doctor_name'] = job.doctor_name
        if job.medication:
            job_parameters['medication'] = job.medication
        if job.start_date:
            job_parameters['start_date'] = job.start_date.strftime('%m/%d/%Y')
        if job.end_date:
            job_parameters['stop_date'] = job.end_date.strftime('%m/%d/%Y')  # Note: stop_date for adapter
        
        # Extraction mode
        job_parameters['extraction_mode'] = 'All Patients' if job.extraction_mode == 'ALL_PATIENTS' else 'Target Patient by Name'
        
        # Patient identifier for single patient mode
        if job.input_patient_identifier:
            job_parameters['patient_identifier'] = job.input_patient_identifier
            if job.extraction_mode == 'SINGLE_PATIENT':
                job_parameters['target_patient_name'] = job.input_patient_identifier
        
        logger.info(f"📋 Extracted job parameters for job {job.id}: {job_parameters}")
        return job_parameters
        
    except Exception as e:
        logger.error(f"❌ Failed to extract job parameters for job {job.id}: {str(e)}")
        return {}

@realtime_bp.route('/job-progress/<int:job_id>', methods=['GET'])
def get_job_progress(job_id):
    """Get real-time progress for a specific job"""
    try:
        job = ExtractionJob.query.get(job_id)
        if not job:
            return jsonify({
                'success': False,
                'error': 'Job not found'
            }), 404
        
        progress_data = job_progress.get(job_id, {
            'job_id': job_id,
            'status': job.status,
            'progress': 0,
            'current_step': 'Initializing...',
            'steps_completed': 0,
            'total_steps': 5,
            'error_message': job.error_message,
            'updated_at': job.updated_at.isoformat()
        })
        
        return jsonify({
            'success': True,
            'progress': progress_data
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Failed to get job progress: {str(e)}'
        }), 500

@realtime_bp.route('/job/<int:job_id>/retry', methods=['POST'])
def retry_job(job_id):
    """Retry a failed job"""
    try:
        job = ExtractionJob.query.get(job_id)
        if not job:
            return jsonify({
                'success': False,
                'error': 'Job not found'
            }), 404
        
        if job.status not in ['FAILED', 'COMPLETED']:
            return jsonify({
                'success': False,
                'error': f'Cannot retry job with status: {job.status}'
            }), 400
        
        # Reset job status and clear error
        job.status = 'PENDING_LOGIN'
        job.error_message = None
        job.raw_extracted_data_json = None
        job.updated_at = datetime.utcnow()
        
        db.session.commit()
        
        # Clear progress tracking
        if job_id in job_progress:
            del job_progress[job_id]
        
        # Start the job with Playwright orchestrator
        try:
            from playwright_orchestrator.orchestrator import PlaywrightSessionManager
            
            session_manager = PlaywrightSessionManager()
            adapter = PortalAdapter.query.get(job.portal_adapter_id)
            
            # Extract job parameters from database
            job_parameters = extract_job_parameters(job)
            
            # Create a proper app context factory
            def app_context_factory():
                return current_app._get_current_object().app_context()
            
            job_started = session_manager.start_job(
                job_id=job.id,
                target_url=job.target_url,
                adapter_script_path=adapter.script_filename,
                mode=job.extraction_mode,
                patient_identifier=job.input_patient_identifier,
                job_parameters=job_parameters,  # ← Fixed: Added job parameters
                app_context_factory=app_context_factory
            )
            
            if not job_started:
                job.status = 'FAILED'
                job.error_message = 'Failed to start Playwright session'
                db.session.commit()
                
                return jsonify({
                    'success': False,
                    'error': 'Failed to restart extraction job'
                }), 500
            
        except Exception as playwright_error:
            job.status = 'FAILED'
            job.error_message = f'Playwright orchestrator error: {str(playwright_error)}'
            db.session.commit()
            
            return jsonify({
                'success': False,
                'error': f'Failed to restart Playwright session: {str(playwright_error)}'
            }), 500
        
        # Emit real-time update
        current_app.socketio.emit('job_retried', {
            'job_id': job_id,
            'status': job.status,
            'timestamp': datetime.now().isoformat()
        })
        
        return jsonify({
            'success': True,
            'message': 'Job restarted successfully',
            'job': job.to_dict()
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Failed to retry job: {str(e)}'
        }), 500

@realtime_bp.route('/jobs/batch', methods=['POST'])
def create_batch_jobs():
    """Create multiple jobs for batch processing"""
    try:
        data = request.get_json()
        
        if 'jobs' not in data or not isinstance(data['jobs'], list):
            return jsonify({
                'success': False,
                'error': 'Missing or invalid jobs array'
            }), 400
        
        created_jobs = []
        failed_jobs = []
        
        for job_config in data['jobs']:
            try:
                # Validate required fields for each job
                required_fields = ['target_url', 'adapter_id', 'extraction_mode']
                for field in required_fields:
                    if field not in job_config:
                        failed_jobs.append({
                            'config': job_config,
                            'error': f'Missing required field: {field}'
                        })
                        continue
                
                # Verify adapter exists
                adapter = PortalAdapter.query.filter_by(
                    id=job_config['adapter_id'], 
                    is_active=True
                ).first()
                
                if not adapter:
                    failed_jobs.append({
                        'config': job_config,
                        'error': 'Invalid or inactive adapter_id'
                    })
                    continue
                
                # Parse dates if provided
                from datetime import datetime as dt
                start_date = None
                end_date = None
                
                if job_config.get('start_date'):
                    try:
                        start_date = dt.strptime(job_config['start_date'], '%Y-%m-%d').date()
                    except ValueError:
                        failed_jobs.append({
                            'config': job_config,
                            'error': 'Invalid start_date format. Use YYYY-MM-DD'
                        })
                        continue
                
                if job_config.get('end_date'):
                    try:
                        end_date = dt.strptime(job_config['end_date'], '%Y-%m-%d').date()
                    except ValueError:
                        failed_jobs.append({
                            'config': job_config,
                            'error': 'Invalid end_date format. Use YYYY-MM-DD'
                        })
                        continue
                
                # Create job
                job = ExtractionJob(
                    job_name=job_config.get('job_name', f"Batch Job {len(created_jobs) + 1}"),
                    target_url=job_config['target_url'],
                    portal_adapter_id=job_config['adapter_id'],
                    extraction_mode=job_config['extraction_mode'],
                    input_patient_identifier=job_config.get('input_patient_identifier'),
                    doctor_name=job_config.get('doctor_name'),
                    medication=job_config.get('medication'),
                    start_date=start_date,
                    end_date=end_date,
                    status='PENDING_LOGIN'
                )
                
                db.session.add(job)
                db.session.flush()  # Get the job ID
                
                created_jobs.append(job.to_dict())
                
            except Exception as job_error:
                failed_jobs.append({
                    'config': job_config,
                    'error': str(job_error)
                })
        
        db.session.commit()
        
        # Start jobs if requested
        if data.get('start_immediately', False):
            for job_dict in created_jobs:
                try:
                    start_job_async(job_dict['id'])
                except Exception as e:
                    # Update job status to failed
                    job = ExtractionJob.query.get(job_dict['id'])
                    if job:
                        job.status = 'FAILED'
                        job.error_message = f'Failed to start: {str(e)}'
                        db.session.commit()
        
        # Emit batch creation event
        current_app.socketio.emit('batch_jobs_created', {
            'created_count': len(created_jobs),
            'failed_count': len(failed_jobs),
            'jobs': created_jobs,
            'timestamp': datetime.now().isoformat()
        })
        
        return jsonify({
            'success': True,
            'created_jobs': created_jobs,
            'failed_jobs': failed_jobs,
            'summary': {
                'created': len(created_jobs),
                'failed': len(failed_jobs)
            }
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': f'Failed to create batch jobs: {str(e)}'
        }), 500

@realtime_bp.route('/system/stats', methods=['GET'])
def get_system_stats():
    """Get real-time system statistics"""
    try:
        # Calculate current stats
        total_jobs = ExtractionJob.query.count()
        active_jobs = ExtractionJob.query.filter(
            ExtractionJob.status.in_(['PENDING_LOGIN', 'LAUNCHING_BROWSER', 'AWAITING_USER_CONFIRMATION', 'EXTRACTING'])
        ).count()
        completed_jobs = ExtractionJob.query.filter_by(status='COMPLETED').count()
        failed_jobs = ExtractionJob.query.filter_by(status='FAILED').count()
        
        # Get recent activity (last 24 hours)
        yesterday = datetime.utcnow() - timedelta(hours=24)
        recent_jobs = ExtractionJob.query.filter(
            ExtractionJob.created_at >= yesterday
        ).count()
        
        # Calculate success rate
        success_rate = 0
        if total_jobs > 0:
            success_rate = (completed_jobs / total_jobs) * 100
        
        # Get adapter stats
        active_adapters = PortalAdapter.query.filter_by(is_active=True).count()
        
        # Update global stats
        global system_stats
        system_stats.update({
            'total_jobs': total_jobs,
            'active_jobs': active_jobs,
            'completed_jobs': completed_jobs,
            'failed_jobs': failed_jobs,
            'recent_activity': recent_jobs,
            'success_rate': round(success_rate, 1),
            'active_adapters': active_adapters,
            'system_health': 'healthy' if active_jobs < 10 else 'busy',
            'last_updated': datetime.now().isoformat()
        })
        
        return jsonify({
            'success': True,
            'stats': system_stats
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Failed to get system stats: {str(e)}'
        }), 500

@realtime_bp.route('/jobs/cancel/<int:job_id>', methods=['POST'])
def cancel_job(job_id):
    """Cancel an active job"""
    try:
        job = ExtractionJob.query.get(job_id)
        if not job:
            return jsonify({
                'success': False,
                'error': 'Job not found'
            }), 404
        
        if job.status in ['COMPLETED', 'FAILED']:
            return jsonify({
                'success': False,
                'error': f'Cannot cancel job with status: {job.status}'
            }), 400
        
        # Try to stop the job in Playwright orchestrator
        try:
            from playwright_orchestrator.orchestrator import PlaywrightSessionManager
            session_manager = PlaywrightSessionManager()
            session_manager.cancel_job(job_id)
        except Exception as e:
            # Continue with cancellation even if orchestrator fails
            pass
        
        # Update job status
        job.status = 'FAILED'
        job.error_message = 'Job cancelled by user'
        job.updated_at = datetime.utcnow()
        
        db.session.commit()
        
        # Clean up progress tracking
        if job_id in job_progress:
            del job_progress[job_id]
        
        # Emit real-time update
        current_app.socketio.emit('job_cancelled', {
            'job_id': job_id,
            'timestamp': datetime.now().isoformat()
        })
        
        return jsonify({
            'success': True,
            'message': 'Job cancelled successfully'
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Failed to cancel job: {str(e)}'
        }), 500

@realtime_bp.route('/jobs/health-check', methods=['POST'])
def health_check_jobs():
    """Check health of all active jobs and fix stuck ones"""
    try:
        # Find jobs that have been in non-terminal states for too long
        stuck_threshold = datetime.utcnow() - timedelta(hours=2)
        
        stuck_jobs = ExtractionJob.query.filter(
            ExtractionJob.status.in_(['PENDING_LOGIN', 'LAUNCHING_BROWSER', 'AWAITING_USER_CONFIRMATION', 'EXTRACTING']),
            ExtractionJob.updated_at < stuck_threshold
        ).all()
        
        fixed_jobs = []
        
        for job in stuck_jobs:
            job.status = 'FAILED'
            job.error_message = 'Job timed out - automatically marked as failed'
            job.updated_at = datetime.utcnow()
            
            fixed_jobs.append({
                'id': job.id,
                'job_name': job.job_name,
                'previous_status': job.status
            })
        
        db.session.commit()
        
        # Emit health check results
        current_app.socketio.emit('health_check_complete', {
            'fixed_jobs': len(fixed_jobs),
            'jobs': fixed_jobs,
            'timestamp': datetime.now().isoformat()
        })
        
        return jsonify({
            'success': True,
            'fixed_jobs': fixed_jobs,
            'message': f'Health check complete. Fixed {len(fixed_jobs)} stuck jobs.'
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Health check failed: {str(e)}'
        }), 500

def start_job_async(job_id):
    """Start a job asynchronously"""
    def _start_job():
        try:
            from playwright_orchestrator.orchestrator import PlaywrightSessionManager
            
            session_manager = PlaywrightSessionManager()
            job = ExtractionJob.query.get(job_id)
            adapter = PortalAdapter.query.get(job.portal_adapter_id)
            
            # Extract job parameters from database
            job_parameters = extract_job_parameters(job)
            
            # Create a proper app context factory
            def app_context_factory():
                return current_app._get_current_object().app_context()
            
            session_manager.start_job(
                job_id=job.id,
                target_url=job.target_url,
                adapter_script_path=adapter.script_filename,
                mode=job.extraction_mode,
                patient_identifier=job.input_patient_identifier,
                job_parameters=job_parameters,  # ← Fixed: Added job parameters
                app_context_factory=app_context_factory
            )
            
        except Exception as e:
            # Update job status to failed
            with current_app.app_context():
                job = ExtractionJob.query.get(job_id)
                if job:
                    job.status = 'FAILED'
                    job.error_message = f'Failed to start: {str(e)}'
                    db.session.commit()
    
    thread = threading.Thread(target=_start_job)
    thread.daemon = True
    thread.start()

def update_job_progress(job_id, progress, current_step, steps_completed=None, total_steps=None):
    """Update job progress and emit real-time updates"""
    global job_progress
    
    progress_data = job_progress.get(job_id, {})
    progress_data.update({
        'job_id': job_id,
        'progress': progress,
        'current_step': current_step,
        'updated_at': datetime.now().isoformat()
    })
    
    if steps_completed is not None:
        progress_data['steps_completed'] = steps_completed
    if total_steps is not None:
        progress_data['total_steps'] = total_steps
    
    job_progress[job_id] = progress_data
    
    # Emit real-time update
    current_app.socketio.emit('job_progress_update', progress_data)

def start_system_monitor():
    """Start non-blocking system monitoring thread with optimized queries"""
    def monitor():
        while True:
            try:
                # Use current app context for database access
                app = current_app._get_current_object()
                with app.app_context():
                    # Use raw SQL for better performance and avoid ORM overhead
                    stats_query = text("""
                        SELECT 
                            COUNT(*) as total_jobs,
                            SUM(CASE WHEN status IN ('PENDING_LOGIN', 'LAUNCHING_BROWSER', 'AWAITING_USER_CONFIRMATION', 'EXTRACTING') THEN 1 ELSE 0 END) as active_jobs,
                            SUM(CASE WHEN status = 'COMPLETED' THEN 1 ELSE 0 END) as completed_jobs,
                            SUM(CASE WHEN status = 'FAILED' THEN 1 ELSE 0 END) as failed_jobs,
                            SUM(CASE WHEN created_at >= datetime('now', '-1 day') THEN 1 ELSE 0 END) as recent_jobs
                        FROM extraction_jobs
                    """)
                    
                    # Get adapter count separately
                    adapter_query = text("SELECT COUNT(*) as active_adapters FROM portal_adapters WHERE is_active = 1")
                    
                    stats_result = db.session.execute(stats_query).fetchone()
                    adapter_result = db.session.execute(adapter_query).fetchone()
                    
                    # Calculate success rate
                    success_rate = 0
                    if stats_result.total_jobs > 0:
                        success_rate = (stats_result.completed_jobs / stats_result.total_jobs) * 100
                    
                    # Update global stats without blocking
                    global system_stats
                    system_stats.update({
                        'total_jobs': stats_result.total_jobs,
                        'active_jobs': stats_result.active_jobs,
                        'completed_jobs': stats_result.completed_jobs,
                        'failed_jobs': stats_result.failed_jobs,
                        'recent_activity': stats_result.recent_jobs,
                        'success_rate': round(success_rate, 1),
                        'active_adapters': adapter_result.active_adapters,
                        'system_health': 'healthy' if stats_result.active_jobs < 10 else 'busy',
                        'last_updated': datetime.now().isoformat()
                    })
                    
                    # Emit system stats update if socketio is available
                    if socketio_instance:
                        socketio_instance.emit('system_stats_update', {
                            'stats': system_stats,
                            'timestamp': datetime.now().isoformat()
                        })
                
                time.sleep(30)  # Update every 30 seconds
            except Exception as e:
                logger.error(f"System monitor error: {e}")
                time.sleep(60)  # Wait longer on error to avoid spam
    
    # Start monitoring thread
    thread = threading.Thread(target=monitor, name='SystemMonitor')
    thread.daemon = True
    thread.start()
    logger.info("✅ Non-blocking system monitor started")

# Start system monitor when module is imported
# Note: This will be called when the blueprint is registered
def init_realtime_monitoring(app):
    """Initialize real-time monitoring"""
    with app.app_context():
        start_system_monitor()

# Export functions for use by other modules
__all__ = ['update_job_progress', 'init_realtime_monitoring']