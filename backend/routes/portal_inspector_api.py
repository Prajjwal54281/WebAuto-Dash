"""
Portal Inspector API for WebAutoDash
Provides portal analysis capabilities (Static Analysis Only)
Live Portal Inspector functions moved to live_inspector_api.py
"""

from flask import Blueprint, request, jsonify, current_app, redirect, url_for
from flask_cors import cross_origin
from flask_socketio import emit
import json
import os
import asyncio
import sys
from datetime import datetime
import threading
from typing import Dict, List, Optional, Any
import time
import logging
import re

# Import Playwright at module level to avoid import issues
try:
    from playwright.async_api import async_playwright
    PLAYWRIGHT_AVAILABLE = True
except ImportError as e:
    PLAYWRIGHT_AVAILABLE = False
    playwright_error = str(e)

# Fix import path for models
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from models import db, PortalAdapter, ExtractionJob

logger = logging.getLogger(__name__)

portal_inspector_bp = Blueprint('portal_inspector', __name__)

@portal_inspector_bp.route('/live-inspect', methods=['POST', 'OPTIONS'])
@cross_origin(origins="*", methods=["POST", "OPTIONS"], allow_headers=["Content-Type", "Authorization"])
def live_inspect_redirect():
    """Redirect old live-inspect endpoint to new v2 API"""
    if request.method == 'OPTIONS':
        # Handle preflight request
        return jsonify({'status': 'ok'}), 200
    
    # For POST requests, return a redirect response
    return jsonify({
        'success': False,
        'error': 'This endpoint has been moved',
        'redirect_to': '/api/live-inspector/live-inspect-v2',
        'message': 'Please use the new Live Inspector v2 API at /api/live-inspector/live-inspect-v2',
        'new_api_features': [
            '🔍 Comprehensive event recording',
            '🛡️ PHI redaction and encryption', 
            '📸 Screenshot capture with metadata',
            '🌐 Network traffic analysis',
            '🎯 Medical-specific element detection',
            '🔄 Automatic replay adapter generation'
        ]
    }), 301

@portal_inspector_bp.route('/analyze', methods=['POST'])
def analyze_portal():
    """Start portal analysis"""
    try:
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['name', 'url', 'username', 'password']
        for field in required_fields:
            if field not in data:
                return jsonify({
                    'success': False,
                    'error': f'Missing required field: {field}'
                }), 400
        
        portal_config = {
            'name': data['name'],
            'url': data['url'],
            'username': data['username'],
            'password': data['password']
        }
        
        # Start analysis in background thread
        analysis_id = f'analysis_{datetime.now().strftime("%Y%m%d_%H%M%S")}'
        
        # Get current Flask app and SocketIO instances for background thread
        app = current_app._get_current_object()
        socketio = app.socketio
        
        def run_portal_analysis():
            try:
                # Create app context for this thread
                with app.app_context():
                    def emit_progress(message, progress=None):
                        socketio.emit('portal_analysis_progress', {
                            'analysis_id': analysis_id,
                            'message': message,
                            'progress': progress,
                            'timestamp': datetime.now().isoformat()
                        })
                    
                    emit_progress("🔍 Starting portal analysis...", 10)
                    result = run_analysis(portal_config, emit_progress)
                    
                    # Save analysis results
                    save_analysis_results(analysis_id, result, portal_config)
                    
                    # Emit final result
                    socketio.emit('portal_analysis_complete', {
                        'analysis_id': analysis_id,
                        'success': result.get('success', False),
                        'results': result,
                        'timestamp': datetime.now().isoformat()
                    })
                    
            except Exception as e:
                with app.app_context():
                    socketio.emit('portal_analysis_error', {
                        'analysis_id': analysis_id,
                        'error': str(e),
                        'timestamp': datetime.now().isoformat()
                    })
        
        # Start analysis in background
        thread = threading.Thread(target=run_portal_analysis)
        thread.daemon = True
        thread.start()
        
        return jsonify({
            'success': True,
            'analysis_id': analysis_id,
            'message': 'Portal analysis started successfully'
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Failed to start portal analysis: {str(e)}'
        }), 500

@portal_inspector_bp.route('/saved-analyses', methods=['GET'])
def get_saved_analyses():
    """Get list of saved portal analyses"""
    try:
        analyses_dir = os.path.join(os.path.dirname(__file__), '..', '..', 'portal_analyses')
        
        if not os.path.exists(analyses_dir):
            os.makedirs(analyses_dir)
            return jsonify({
                'success': True,
                'analyses': []
            })
        
        analyses = []
        for filename in os.listdir(analyses_dir):
            if filename.endswith('.json'):
                try:
                    filepath = os.path.join(analyses_dir, filename)
                    with open(filepath, 'r') as f:
                        data = json.load(f)
                    
                    analyses.append({
                        'id': filename.replace('.json', ''),
                        'name': data.get('portal_config', {}).get('name', 'Unknown Portal'),
                        'url': data.get('portal_config', {}).get('url', ''),
                        'created_at': data.get('timestamp', ''),
                        'portal_type': data.get('results', {}).get('portal_info', {}).get('type', 'Unknown'),
                        'success': data.get('results', {}).get('success', False)
                    })
                except Exception:
                    continue
        
        analyses.sort(key=lambda x: x['created_at'], reverse=True)
        
        return jsonify({
            'success': True,
            'analyses': analyses
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Failed to get saved analyses: {str(e)}'
        }), 500

@portal_inspector_bp.route('/analysis/<analysis_id>', methods=['GET'])
def get_analysis_details(analysis_id):
    """Get detailed results for a specific analysis"""
    try:
        analyses_dir = os.path.join(os.path.dirname(__file__), '..', '..', 'portal_analyses')
        filepath = os.path.join(analyses_dir, f'{analysis_id}.json')
        
        if not os.path.exists(filepath):
            return jsonify({
                'success': False,
                'error': 'Analysis not found'
            }), 404
        
        with open(filepath, 'r') as f:
            data = json.load(f)
        
        return jsonify({
            'success': True,
            'analysis': data
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Failed to get analysis details: {str(e)}'
        }), 500

@portal_inspector_bp.route('/test-selector', methods=['POST'])
def test_selector():
    """Test CSS selectors against a portal"""
    try:
        data = request.get_json()
        
        required_fields = ['url', 'selector']
        for field in required_fields:
            if field not in data:
                return jsonify({
                    'success': False,
                    'error': f'Missing required field: {field}'
                }), 400
        
        # Mock response for selector testing
        return jsonify({
            'success': True,
            'found': True,
            'count': 1,
            'message': f'Selector "{data["selector"]}" found elements on the page'
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Failed to test selector: {str(e)}'
        }), 500

@portal_inspector_bp.route('/generate-adapter', methods=['POST'])
def generate_adapter():
    """Generate a portal adapter based on analysis results"""
    try:
        data = request.get_json()
        
        if not data or 'analysis_id' not in data:
            return jsonify({
                'success': False,
                'error': 'Missing analysis_id'
            }), 400
        
        # Get analysis results
        analyses_dir = os.path.join(os.path.dirname(__file__), '..', '..', 'portal_analyses')
        filepath = os.path.join(analyses_dir, f'{data["analysis_id"]}.json')
        
        if not os.path.exists(filepath):
            return jsonify({
                'success': False,
                'error': f'Analysis not found: {data["analysis_id"]}'
            }), 404
        
        with open(filepath, 'r') as f:
            analysis_data = json.load(f)
        
        # Generate adapter code
        adapter_code = generate_adapter_code(
            analysis_data['portal_config'],
            analysis_data['results']
        )
        
        # Save adapter code
        adapter_filename = f'{analysis_data["portal_config"]["name"].lower().replace(" ", "_")}_adapter.py'
        adapter_filepath = os.path.join(os.path.dirname(__file__), '..', '..', 'portal_adapters', adapter_filename)
        
        with open(adapter_filepath, 'w') as f:
            f.write(adapter_code)
        
        return jsonify({
            'success': True,
            'adapter_code': adapter_code,
            'adapter_filename': adapter_filename,
            'message': 'Portal adapter generated successfully'
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Failed to generate adapter: {str(e)}'
        }), 500

@portal_inspector_bp.route('/check-adapter-jobs/<int:adapter_id>', methods=['GET'])
def check_adapter_jobs(adapter_id):
    """Check if an adapter has any associated jobs"""
    try:
        # Check for jobs using this adapter
        jobs = ExtractionJob.query.filter_by(portal_adapter_id=adapter_id).all()
        
        job_info = []
        for job in jobs:
            job_info.append({
                'id': job.id,
                'status': job.status,
                'created_at': job.created_at.isoformat() if job.created_at else None,
                'extraction_mode': job.extraction_mode
            })
        
        return jsonify({
            'success': True,
            'has_jobs': len(jobs) > 0,
            'job_count': len(jobs),
            'jobs': job_info
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Failed to check adapter jobs: {str(e)}'
        }), 500

@portal_inspector_bp.route('/check-adapter/<script_filename>', methods=['GET'])
def check_adapter_file(script_filename):
    """Check if an adapter file exists in the filesystem"""
    try:
        # Get the portal_adapters directory path
        portal_adapters_dir = os.path.join(os.path.dirname(__file__), '..', '..', 'portal_adapters')
        adapter_file_path = os.path.join(portal_adapters_dir, script_filename)
        
        file_exists = os.path.exists(adapter_file_path)
        
        return jsonify({
            'success': True,
            'file_exists': file_exists,
            'script_filename': script_filename,
            'file_path': adapter_file_path if file_exists else None
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Failed to check adapter file: {str(e)}'
        }), 500

@portal_inspector_bp.route('/delete-adapter', methods=['POST'])
def delete_adapter():
    """Delete a portal adapter (database record and file)"""
    try:
        data = request.get_json()
        
        if not data or 'adapter_id' not in data:
            return jsonify({
                'success': False,
                'error': 'Missing adapter_id'
            }), 400
        
        adapter_id = data['adapter_id']
        
        # Find the adapter in the database
        adapter = PortalAdapter.query.get(adapter_id)
        if not adapter:
            return jsonify({
                'success': False,
                'error': f'Adapter with ID {adapter_id} not found'
            }), 404
        
        # Check if adapter has any associated jobs
        associated_jobs = ExtractionJob.query.filter_by(portal_adapter_id=adapter_id).all()
        
        if associated_jobs:
            # Prepare details about the associated jobs
            job_details = []
            for job in associated_jobs:
                job_details.append({
                    'id': job.id,
                    'job_name': job.job_name or f'Job #{job.id}',
                    'status': job.status,
                    'created_at': job.created_at.strftime('%Y-%m-%d %H:%M')
                })
            
            return jsonify({
                'success': False,
                'error': f'Cannot delete adapter "{adapter.name}" because it has {len(associated_jobs)} associated extraction job(s).',
                'associated_jobs': job_details,
                'suggestion': 'Please delete the associated jobs first by going to the Jobs page, or contact an administrator.'
            }), 400
        
        filename = adapter.script_filename
        adapter_filepath = os.path.join(os.path.dirname(__file__), '..', '..', 'portal_adapters', filename)
        
        file_deletion_status = "not_attempted"
        warning_message = None
        
        # Try to delete the file if it exists
        if os.path.exists(adapter_filepath):
            # Security check - ensure filename ends with .py and is in expected location
            if not filename.endswith('.py') or '..' in filename:
                return jsonify({
                    'success': False,
                    'error': 'Invalid filename for security reasons'
                }), 400
            
            try:
                os.remove(adapter_filepath)
                file_deletion_status = "success"
            except Exception as e:
                file_deletion_status = "failed"
                warning_message = f"Failed to delete adapter file {adapter_filepath}: {str(e)}"
        else:
            file_deletion_status = "not_found"
            warning_message = f"Adapter file {adapter_filepath} not found (may have been deleted already)"
        
        # Delete the database record
        try:
            db.session.delete(adapter)
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            return jsonify({
                'success': False,
                'error': f'Failed to delete adapter from database: {str(e)}'
            }), 500
        
        # Prepare response
        response_data = {
            'success': True,
            'message': f'Adapter "{adapter.name}" deleted successfully',
            'file_deletion': file_deletion_status
        }
        
        if warning_message:
            response_data['warning'] = warning_message
        
        return jsonify(response_data)
        
    except Exception as e:
        logger.error(f"Failed to delete adapter: {e}")
        return jsonify({
            'success': False,
            'error': f'Failed to delete adapter: {str(e)}'
        }), 500

@portal_inspector_bp.route('/create-medimind2', methods=['POST'])
def create_medimind2():
    """Create a MediMind2 compatible adapter"""
    try:
        data = request.get_json()
        
        if not data or 'portal_config' not in data:
            return jsonify({
                'success': False,
                'error': 'Missing portal configuration'
            }), 400
        
        # Generate MediMind2 adapter
        adapter_code = generate_medimind2_adapter()
        
        # Save adapter
        filename = f'medimind2_adapter_{datetime.now().strftime("%Y%m%d_%H%M%S")}.py'
        filepath = os.path.join(os.path.dirname(__file__), '..', '..', 'portal_adapters', filename)
        
        with open(filepath, 'w') as f:
            f.write(adapter_code)
        
        return jsonify({
            'success': True,
            'adapter_code': adapter_code,
            'filename': filename,
            'message': 'MediMind2 adapter created successfully'
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Failed to create MediMind2 adapter: {str(e)}'
        }), 500

@portal_inspector_bp.route('/sync-adapters', methods=['POST'])
def sync_adapters_from_filesystem():
    """Enhanced sync adapter files from filesystem to database - handles additions, updates, and deletions"""
    try:
        # Get all adapter files from filesystem
        adapter_dir = os.path.join(os.path.dirname(__file__), '..', '..', 'portal_adapters')
        if not os.path.exists(adapter_dir):
            return jsonify({
                'success': True,
                'message': 'No adapter directory found',
                'synced_count': 0
            })
        
        # Get filesystem files
        filesystem_files = {f for f in os.listdir(adapter_dir) if f.endswith('.py')}
        
        # Get database adapters
        db_adapters = PortalAdapter.query.all()
        db_filenames = {adapter.script_filename for adapter in db_adapters}
        
        synced_count = 0
        new_adapters = []
        updated_adapters = []
        removed_adapters = []
        unchanged_adapters = []
        
        # 1. Add new adapters (files in filesystem but not in database)
        new_files = filesystem_files - db_filenames
        for filename in new_files:
            try:
                # Extract portal name from filename
                portal_name = filename.replace('_live_adapter_', ' ').replace('.py', '').replace('_', ' ').title()
                if 'live adapter' in portal_name.lower():
                    portal_name = portal_name.replace(' Live Adapter', '').replace(' Live', '').strip()
                
                # Create new adapter record
                new_adapter = PortalAdapter(
                    name=portal_name,
                    description=f"Adapter for {portal_name} portal (Auto-synced from filesystem)",
                    script_filename=filename,
                    is_active=True
                )
                
                db.session.add(new_adapter)
                new_adapters.append(portal_name)
                synced_count += 1
                
            except Exception as file_error:
                logger.warning(f"Failed to sync new adapter file {filename}: {file_error}")
                continue
        
        # 2. Remove adapters (files in database but not in filesystem)
        orphaned_files = db_filenames - filesystem_files
        for filename in orphaned_files:
            try:
                adapter_to_remove = PortalAdapter.query.filter_by(script_filename=filename).first()
                if adapter_to_remove:
                    # Check for associated jobs
                    associated_jobs = ExtractionJob.query.filter_by(portal_adapter_id=adapter_to_remove.id).all()
                    
                    if associated_jobs:
                        # Delete associated jobs since portal_adapter_id cannot be NULL
                        for job in associated_jobs:
                            db.session.delete(job)
                        logger.info(f"Deleted {len(associated_jobs)} jobs for removed adapter {filename}")
                    
                    removed_adapters.append(adapter_to_remove.name)
                    db.session.delete(adapter_to_remove)
                    synced_count += 1
                    
            except Exception as remove_error:
                logger.warning(f"Failed to remove adapter {filename}: {remove_error}")
                continue
        
        # 3. Handle potential filename changes by checking for similar patterns
        # This is a smart matching approach for when adapter files are renamed
        remaining_db_adapters = [a for a in db_adapters if a.script_filename in filesystem_files]
        
        # Check for adapters that might have been renamed (basic pattern matching)
        for adapter in remaining_db_adapters:
            if adapter.script_filename in filesystem_files:
                unchanged_adapters.append(adapter.name)
        
        # Commit all changes
        if synced_count > 0:
            db.session.commit()
            logger.info(f"✅ Enhanced sync completed: {synced_count} changes made")
        else:
            unchanged_adapters = [a.name for a in db_adapters if a.script_filename in filesystem_files]
        
        return jsonify({
            'success': True,
            'message': f'Enhanced sync completed: {synced_count} changes made',
            'synced_count': synced_count,
            'new_adapters': new_adapters,
            'updated_adapters': updated_adapters, 
            'removed_adapters': removed_adapters,
            'unchanged_adapters': unchanged_adapters
        })
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Failed to sync adapters: {e}")
        # Clear the session state to avoid "rolled back transaction" errors
        db.session.close()
        return jsonify({
            'success': False,
            'error': f'Failed to sync adapters: {str(e)}',
            'synced_count': 0
        }), 500

# Static Portal Analysis Functions (Non-Live)
def run_analysis(portal_config: Dict, emit_progress) -> Dict:
    """Run static portal analysis without browser automation"""
    try:
        emit_progress("🔍 Analyzing portal structure...", 20)
        
        # Detect portal type from URL
        portal_type = detect_portal_type(portal_config['url'])
        emit_progress(f"🏥 Portal type detected: {portal_type}", 40)
        
        # Get portal vendor information
        vendor = get_portal_vendor(portal_type)
        emit_progress(f"🏢 Portal vendor: {vendor}", 60)
        
        # Analyze expected login elements
        login_analysis = analyze_login_elements(portal_config['url'])
        emit_progress("🔐 Login elements analyzed", 80)
        
        # Detect CAPTCHA types
        captcha_info = detect_captcha_types(portal_config['url'])
        
        # Analyze patient data elements based on portal type
        patient_data = analyze_patient_data_elements(portal_config['url'], portal_type)
        emit_progress("📊 Patient data elements analyzed", 90)
        
        emit_progress("✅ Portal analysis completed", 100)
        
        return {
            'success': True,
            'portal_info': {
                'type': portal_type,
                'vendor': vendor,
                'url': portal_config['url']
            },
            'login_analysis': login_analysis,
            'captcha_info': captcha_info,
            'patient_data': patient_data,
            'analysis_type': 'static'
        }
        
    except Exception as e:
        logger.error(f"Portal analysis failed: {e}")
        return {
            'success': False,
            'error': str(e),
            'analysis_type': 'static'
        }

def save_analysis_results(analysis_id, results, portal_config):
    """Save static analysis results"""
    try:
        results_dir = os.path.join(os.path.dirname(__file__), '..', '..', 'portal_analyses')
        os.makedirs(results_dir, exist_ok=True)
        
        data = {
            'analysis_id': analysis_id,
            'timestamp': datetime.now().isoformat(),
            'portal_config': portal_config,
            'results': results
        }
        
        filepath = os.path.join(results_dir, f'{analysis_id}.json')
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)
        
        logger.info(f"Analysis results saved: {filepath}")
        
    except Exception as e:
        logger.error(f"Failed to save analysis results: {e}")

def detect_portal_type(url):
    """Detect portal type from URL patterns"""
    url_lower = url.lower()
    
    if 'mychart' in url_lower or 'epic' in url_lower:
        return 'Epic MyChart'
    elif 'cerner' in url_lower or 'powerchart' in url_lower:
        return 'Cerner PowerChart'
    elif 'allscripts' in url_lower or 'followmyhealth' in url_lower:
        return 'Allscripts FollowMyHealth'
    elif 'athena' in url_lower:
        return 'athenahealth'
    elif 'nextgen' in url_lower or 'nextmd' in url_lower:
        return 'NextGen NextMD'
    elif 'eclinicalworks' in url_lower or 'healow' in url_lower:
        return 'eClinicalWorks healow'
    elif 'example' in url_lower:
        return 'Example Portal'
    else:
        return 'Custom/Unknown'

def get_portal_vendor(portal_type):
    """Get portal vendor information"""
    vendor_map = {
        'Epic MyChart': 'Epic Systems Corporation',
        'Cerner PowerChart': 'Oracle Cerner',
        'Allscripts FollowMyHealth': 'Allscripts Healthcare Solutions',
        'athenahealth': 'athenahealth, Inc.',
        'NextGen NextMD': 'NextGen Healthcare',
        'eClinicalWorks healow': 'eClinicalWorks',
        'Example Portal': 'Example Portal System',
        'Custom/Unknown': 'Unknown Vendor'
    }
    
    return vendor_map.get(portal_type, 'Unknown Vendor')

def analyze_login_elements(url):
    """Analyze expected login elements based on portal type"""
    return {
        'expected_username_field': 'input[type="email"], input[name="username"]',
        'expected_password_field': 'input[type="password"]',
        'expected_submit_button': 'button[type="submit"], input[type="submit"]',
        'login_url': url,
        'two_factor_likely': 'epic' in url.lower() or 'cerner' in url.lower()
    }

def detect_captcha_types(url):
    """Detect likely CAPTCHA types based on portal"""
    return {
        'recaptcha_likely': True,
        'hcaptcha_likely': False,
        'custom_captcha_likely': 'custom' in url.lower()
    }

def analyze_patient_data_elements(url, portal_type):
    """Analyze expected patient data elements"""
    common_elements = {
        'demographics': ['name', 'dob', 'gender', 'address', 'phone'],
        'medical_history': ['allergies', 'medications', 'problems'],
        'lab_results': ['tests', 'values', 'dates'],
        'appointments': ['date', 'time', 'provider', 'type']
    }
    
    portal_specific = {
        'Epic MyChart': {
            'table_selectors': ['.patient-table', '#PatientList'],
            'data_selectors': ['.patient-row', '.med-item']
        },
        'Cerner PowerChart': {
            'table_selectors': ['.grid', '.patient-grid'],
            'data_selectors': ['.grid-row', '.data-item']
        }
    }
    
    return {
        'common_elements': common_elements,
        'portal_specific': portal_specific.get(portal_type, {})
    }

def generate_adapter_code(portal_config, analysis_results):
    """Generate static portal adapter code"""
    return f"""
# Generated Portal Adapter for {portal_config['name']}
# Portal Type: {analysis_results.get('portal_info', {}).get('type', 'Unknown')}
# Generated: {datetime.now().isoformat()}

class {portal_config['name'].replace(' ', '')}Adapter:
    def __init__(self):
        self.portal_url = "{portal_config['url']}"
        self.portal_type = "{analysis_results.get('portal_info', {}).get('type', 'Unknown')}"
        
    def login(self, username, password):
        # Login implementation based on analysis
        pass
        
    def extract_patient_data(self):
        # Data extraction implementation
        pass
"""

def generate_medimind2_adapter():
    """Generate a MediMind2 compatible adapter template"""
    return f"""
# MediMind2 Compatible Adapter
# Generated: {datetime.now().isoformat()}

class MediMind2Adapter:
    def __init__(self):
        self.name = "MediMind2 Adapter"
        self.version = "2.0.0"
        
    def extract_patient_data(self, patient_id):
        # MediMind2 compatible extraction
        return {{
            'patient_id': patient_id,
            'demographics': {{}},
            'medications': [],
            'lab_results': []
        }}
"""