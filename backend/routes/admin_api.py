from flask import Blueprint, request, jsonify
from models import db, PortalAdapter, ExtractionJob
from datetime import datetime
import os
from pathlib import Path

admin_bp = Blueprint('admin', __name__)

@admin_bp.route('/adapters', methods=['GET'])
def get_all_adapters():
    """Get all portal adapters (including inactive ones)"""
    try:
        adapters = PortalAdapter.query.order_by(PortalAdapter.created_at.desc()).all()
        return jsonify({
            'success': True,
            'adapters': [adapter.to_dict() for adapter in adapters]
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Failed to fetch adapters: {str(e)}'
        }), 500

@admin_bp.route('/adapters', methods=['POST'])
def create_adapter():
    """Create a new portal adapter"""
    try:
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['name', 'script_filename']
        for field in required_fields:
            if field not in data:
                return jsonify({
                    'success': False,
                    'error': f'Missing required field: {field}'
                }), 400
        
        # Check if name already exists
        existing_adapter = PortalAdapter.query.filter_by(name=data['name']).first()
        if existing_adapter:
            return jsonify({
                'success': False,
                'error': 'Adapter with this name already exists'
            }), 400
        
        # Check if script_filename already exists
        existing_script = PortalAdapter.query.filter_by(script_filename=data['script_filename']).first()
        if existing_script:
            return jsonify({
                'success': False,
                'error': 'Adapter with this script filename already exists'
            }), 400
        
        # Validate that script file exists
        script_path = Path('portal_adapters') / data['script_filename']
        if not script_path.exists():
            return jsonify({
                'success': False,
                'error': f'Script file not found: {script_path}'
            }), 400
        
        # Create new adapter
        adapter = PortalAdapter(
            name=data['name'],
            description=data.get('description', ''),
            script_filename=data['script_filename'],
            is_active=data.get('is_active', True)
        )
        
        db.session.add(adapter)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'adapter': adapter.to_dict()
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': f'Failed to create adapter: {str(e)}'
        }), 500

@admin_bp.route('/adapters/<int:adapter_id>', methods=['PUT'])
def update_adapter(adapter_id):
    """Update an existing portal adapter"""
    try:
        adapter = PortalAdapter.query.get(adapter_id)
        if not adapter:
            return jsonify({
                'success': False,
                'error': 'Adapter not found'
            }), 404
        
        data = request.get_json()
        
        # Update fields if provided
        if 'name' in data:
            # Check if new name conflicts with existing adapter
            existing_adapter = PortalAdapter.query.filter(
                PortalAdapter.name == data['name'],
                PortalAdapter.id != adapter_id
            ).first()
            if existing_adapter:
                return jsonify({
                    'success': False,
                    'error': 'Adapter with this name already exists'
                }), 400
            adapter.name = data['name']
        
        if 'description' in data:
            adapter.description = data['description']
        
        if 'script_filename' in data:
            # Check if new script filename conflicts with existing adapter
            existing_script = PortalAdapter.query.filter(
                PortalAdapter.script_filename == data['script_filename'],
                PortalAdapter.id != adapter_id
            ).first()
            if existing_script:
                return jsonify({
                    'success': False,
                    'error': 'Adapter with this script filename already exists'
                }), 400
            
            # Validate that script file exists
            script_path = Path('portal_adapters') / data['script_filename']
            if not script_path.exists():
                return jsonify({
                    'success': False,
                    'error': f'Script file not found: {script_path}'
                }), 400
            
            adapter.script_filename = data['script_filename']
        
        if 'is_active' in data:
            adapter.is_active = bool(data['is_active'])
        
        adapter.updated_at = datetime.utcnow()
        db.session.commit()
        
        return jsonify({
            'success': True,
            'adapter': adapter.to_dict()
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': f'Failed to update adapter: {str(e)}'
        }), 500

@admin_bp.route('/adapters/<int:adapter_id>', methods=['DELETE'])
def delete_adapter(adapter_id):
    """Delete a portal adapter (hard delete if file doesn't exist, otherwise soft delete)"""
    try:
        adapter = PortalAdapter.query.get(adapter_id)
        if not adapter:
            return jsonify({
                'success': False,
                'error': 'Adapter not found'
            }), 404
        
        # Check if adapter has active jobs
        active_jobs = ExtractionJob.query.filter_by(
            portal_adapter_id=adapter_id
        ).filter(
            ExtractionJob.status.in_(['PENDING_LOGIN', 'LAUNCHING_BROWSER', 'AWAITING_USER_CONFIRMATION', 'EXTRACTING'])
        ).count()
        
        if active_jobs > 0:
            return jsonify({
                'success': False,
                'error': f'Cannot delete adapter with {active_jobs} active jobs. Please wait for jobs to complete or fail.'
            }), 400
        
        # Check if adapter file exists in filesystem
        script_path = Path('portal_adapters') / adapter.script_filename
        file_exists = script_path.exists()
        
        if file_exists:
            # File exists - provide warning that file should be removed first
            return jsonify({
                'success': False,
                'error': f'Cannot delete adapter: File "{adapter.script_filename}" still exists in portal_adapters directory. Please remove the file first or use sync to handle it automatically.',
                'file_exists': True,
                'suggestion': 'Use the "Sync Adapters" feature to automatically handle file deletions.'
            }), 400
        else:
            # File doesn't exist - safe to delete from database
            db.session.delete(adapter)
            db.session.commit()
            
            return jsonify({
                'success': True,
                'message': f'Adapter "{adapter.name}" deleted successfully from database',
                'file_exists': False
            })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': f'Failed to delete adapter: {str(e)}'
        }), 500

@admin_bp.route('/adapters/validate_script/<script_filename>', methods=['GET'])
def validate_adapter_script(script_filename):
    """Validate that an adapter script exists and has required functions"""
    try:
        script_path = Path('portal_adapters') / script_filename
        
        if not script_path.exists():
            return jsonify({
                'success': False,
                'error': 'Script file not found',
                'valid': False
            })
        
        # Try to import and validate the script
        import importlib.util
        spec = importlib.util.spec_from_file_location("adapter_module", script_path)
        adapter_module = importlib.util.module_from_spec(spec)
        
        try:
            spec.loader.exec_module(adapter_module)
        except Exception as import_error:
            return jsonify({
                'success': True,
                'valid': False,
                'error': f'Script import failed: {str(import_error)}'
            })
        
        # Check for required functions
        required_functions = ['extract_single_patient_data', 'extract_all_patients_data']
        missing_functions = []
        
        for func_name in required_functions:
            if not hasattr(adapter_module, func_name):
                missing_functions.append(func_name)
        
        if missing_functions:
            return jsonify({
                'success': True,
                'valid': False,
                'error': f'Missing required functions: {", ".join(missing_functions)}'
            })
        
        return jsonify({
            'success': True,
            'valid': True,
            'message': 'Script is valid and contains all required functions'
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Failed to validate script: {str(e)}'
        }), 500

@admin_bp.route('/adapters/available_scripts', methods=['GET'])
def get_available_scripts():
    """Get list of available adapter scripts in the portal_adapters directory"""
    try:
        portal_adapters_dir = Path('portal_adapters')
        
        if not portal_adapters_dir.exists():
            return jsonify({
                'success': True,
                'scripts': []
            })
        
        # Find all Python files in the directory
        scripts = []
        for script_file in portal_adapters_dir.glob('*.py'):
            if script_file.name.startswith('_'):
                continue  # Skip template files or private files
            
            scripts.append({
                'filename': script_file.name,
                'size': script_file.stat().st_size,
                'modified': datetime.fromtimestamp(script_file.stat().st_mtime).isoformat()
            })
        
        return jsonify({
            'success': True,
            'scripts': sorted(scripts, key=lambda x: x['filename'])
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Failed to get available scripts: {str(e)}'
        }), 500

@admin_bp.route('/adapters/<int:adapter_id>/download', methods=['GET'])
def download_adapter_script(adapter_id):
    """Download the adapter script file"""
    try:
        adapter = PortalAdapter.query.get(adapter_id)
        if not adapter:
            return jsonify({
                'success': False,
                'error': 'Adapter not found'
            }), 404
        
        script_path = Path('portal_adapters') / adapter.script_filename
        
        if not script_path.exists():
            return jsonify({
                'success': False,
                'error': 'Script file not found'
            }), 404
        
        from flask import send_file
        return send_file(
            script_path,
            as_attachment=True,
            download_name=adapter.script_filename,
            mimetype='text/plain'
        )
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Failed to download script: {str(e)}'
        }), 500

@admin_bp.route('/adapters/<int:adapter_id>/view', methods=['GET'])
def view_adapter_script(adapter_id):
    """View the adapter script content"""
    try:
        adapter = PortalAdapter.query.get(adapter_id)
        if not adapter:
            return jsonify({
                'success': False,
                'error': 'Adapter not found'
            }), 404
        
        script_path = Path('portal_adapters') / adapter.script_filename
        
        if not script_path.exists():
            return jsonify({
                'success': False,
                'error': 'Script file not found'
            }), 404
        
        # Read the script content
        with open(script_path, 'r', encoding='utf-8') as f:
            script_content = f.read()
        
        # Return as HTML with syntax highlighting
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>{adapter.name} - Adapter Script</title>
            <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/styles/default.min.css">
            <script src="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/highlight.min.js"></script>
            <script src="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/languages/python.min.js"></script>
            <style>
                body {{ 
                    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; 
                    margin: 0; 
                    padding: 20px; 
                    background-color: #f5f5f5; 
                }}
                .header {{ 
                    background: white; 
                    padding: 20px; 
                    border-radius: 8px; 
                    margin-bottom: 20px; 
                    box-shadow: 0 2px 4px rgba(0,0,0,0.1); 
                }}
                .code-container {{ 
                    background: white; 
                    border-radius: 8px; 
                    overflow: hidden; 
                    box-shadow: 0 2px 4px rgba(0,0,0,0.1); 
                }}
                pre {{ 
                    margin: 0; 
                    padding: 20px; 
                    overflow-x: auto; 
                }}
                .info {{ 
                    color: #666; 
                    font-size: 14px; 
                }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>{adapter.name}</h1>
                <div class="info">
                    <p><strong>Script:</strong> {adapter.script_filename}</p>
                    <p><strong>Description:</strong> {adapter.description or 'No description available'}</p>
                    <p><strong>Status:</strong> {'Active' if adapter.is_active else 'Inactive'}</p>
                </div>
            </div>
            <div class="code-container">
                <pre><code class="language-python">{script_content}</code></pre>
            </div>
            <script>hljs.highlightAll();</script>
        </body>
        </html>
        """
        
        from flask import Response
        return Response(html_content, mimetype='text/html')
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Failed to view script: {str(e)}'
        }), 500

@admin_bp.route('/jobs/<int:job_id>', methods=['DELETE'])
def delete_job(job_id):
    """Delete a job (hard delete from database)"""
    try:
        job = ExtractionJob.query.get(job_id)
        if not job:
            return jsonify({
                'success': False,
                'error': 'Job not found'
            }), 404
        
        # Check if job is currently active
        if job.status in ['PENDING_LOGIN', 'LAUNCHING_BROWSER', 'AWAITING_USER_CONFIRMATION', 'EXTRACTING']:
            return jsonify({
                'success': False,
                'error': 'Cannot delete active job. Please wait for job to complete or fail.'
            }), 400
        
        db.session.delete(job)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Job deleted successfully'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': f'Failed to delete job: {str(e)}'
        }), 500

@admin_bp.route('/adapters/check-file/<script_filename>', methods=['GET'])
def check_adapter_file_exists(script_filename):
    """Check if an adapter file exists in the filesystem"""
    try:
        # Get the portal_adapters directory path
        script_path = Path('portal_adapters') / script_filename
        file_exists = script_path.exists()
        
        return jsonify({
            'success': True,
            'exists': file_exists,
            'script_filename': script_filename,
            'file_path': str(script_path) if file_exists else None
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Failed to check adapter file: {str(e)}'
        }), 500

@admin_bp.route('/adapters/<int:adapter_id>/force-delete', methods=['DELETE'])
def force_delete_adapter(adapter_id):
    """Force delete adapter by deleting all associated jobs first"""
    try:
        adapter = PortalAdapter.query.get(adapter_id)
        if not adapter:
            return jsonify({
                'success': False,
                'error': 'Adapter not found'
            }), 404
        
        # First, delete all associated jobs (since portal_adapter_id cannot be NULL)
        associated_jobs = ExtractionJob.query.filter_by(portal_adapter_id=adapter_id).all()
        job_count = len(associated_jobs)
        
        for job in associated_jobs:
            db.session.delete(job)
        
        # Now delete the adapter
        db.session.delete(adapter)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'Adapter "{adapter.name}" and {job_count} associated job(s) deleted successfully',
            'deleted_jobs': job_count,
            'info': f'Removed {job_count} jobs along with the adapter'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': f'Failed to force delete adapter: {str(e)}'
        }), 500

@admin_bp.route('/adapters/<int:adapter_id>/dependent-jobs', methods=['GET'])
def check_adapter_dependent_jobs(adapter_id):
    """Check if adapter has dependent jobs"""
    try:
        adapter = PortalAdapter.query.get(adapter_id)
        if not adapter:
            return jsonify({
                'success': False,
                'error': 'Adapter not found'
            }), 404
        
        # Count all jobs associated with this adapter
        all_jobs = ExtractionJob.query.filter_by(portal_adapter_id=adapter_id).count()
        
        # Count active jobs
        active_jobs = ExtractionJob.query.filter_by(
            portal_adapter_id=adapter_id
        ).filter(
            ExtractionJob.status.in_(['PENDING_LOGIN', 'LAUNCHING_BROWSER', 'AWAITING_USER_CONFIRMATION', 'EXTRACTING'])
        ).count()
        
        return jsonify({
            'success': True,
            'has_dependencies': all_jobs > 0,
            'job_count': all_jobs,
            'active_job_count': active_jobs,
            'can_delete_safely': active_jobs == 0,
            'message': f'Adapter has {all_jobs} associated jobs ({active_jobs} active)'
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Failed to check adapter dependencies: {str(e)}'
        }), 500 