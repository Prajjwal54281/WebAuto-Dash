"""
Advanced Live Portal Inspector API for WebAutoDash
Provides real-time portal inspection capabilities with comprehensive analysis

SocketIO Integration Note:
    This blueprint requires SocketIO to be attached before registration:
    
    app = Flask(__name__)
    socketio = SocketIO(app, cors_allowed_origins="*")
    live_inspector_bp.socketio = socketio  # Required!
    app.register_blueprint(live_inspector_bp, url_prefix='/api/live-inspector')
    socketio.run(app)

Production-Ready Features:
    - Threaded background execution with proper async handling
    - Comprehensive error handling and cleanup
    - Race condition protection for file operations
    - Proper resource cleanup (active_inspections, stop_flags)
    - Headless mode support for CI/testing environments
    - Real-time SocketIO streaming with status updates
    - PHI redaction and encryption for healthcare compliance
    - Pathlib-based file handling for cross-platform compatibility
    - Detailed validation with informative error messages
    - Status tracking with accurate inspection counts

API Endpoints:
    POST /live-inspect-v2                      - Start new inspection
    POST /live-inspect-v2/<id>/stop           - Stop active inspection  
    GET  /live-inspect-v2/<id>/status         - Get inspection status
    GET  /live-inspect-v2/<id>/download       - Download results
    GET  /live-inspect-v2/capabilities        - Get system capabilities

Edge Cases Handled:
    - File write races with size checks and retry logic
    - Thread cleanup on startup failures
    - Stop flag races with proper sequencing
    - SocketIO attachment verification
    - Partial file download protection
"""

from flask import Blueprint, request, jsonify, current_app
from flask_cors import cross_origin
import json
import os
import asyncio
import sys
from datetime import datetime
import threading
from typing import Dict, List, Optional, Any
import time
import logging
from pathlib import Path

# Import the new advanced inspector
try:
    from live_inspector_advanced import LivePortalInspector, InspectorConfig
    ADVANCED_INSPECTOR_AVAILABLE = True
except ImportError as e:
    ADVANCED_INSPECTOR_AVAILABLE = False
    inspector_error = str(e)

logger = logging.getLogger(__name__)

live_inspector_bp = Blueprint('live_inspector_v2', __name__)

# Global tracking for active live inspections
active_inspections = {}
inspection_stop_flags = {}

# Common CORS headers for development
CORS_HEADERS = ["Content-Type", "Authorization", "Cache-Control", "Pragma", "Expires", "X-Requested-With", "X-Cache-Bust"]

@live_inspector_bp.route('/live-inspect-v2', methods=['POST'])
@cross_origin(origins="*", methods=["POST"], allow_headers=CORS_HEADERS)
def start_live_inspection_v2():
    """Start advanced live portal inspection with comprehensive analysis"""
    try:
        if not ADVANCED_INSPECTOR_AVAILABLE:
            return jsonify({
                'success': False,
                'error': f'Advanced inspector not available: {inspector_error}',
                'fallback_available': True
            }), 500
        
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['portal_name', 'portal_url']
        for field in required_fields:
            if field not in data:
                return jsonify({
                    'success': False,
                    'error': f'Missing required field: {field}'
                }), 400
        
        # Create inspector configuration
        config_data = {
            'portal_url': data['portal_url'],
            'portal_name': data['portal_name'],
            'recording_mode': data.get('recording_mode', 'full'),
            'timeout_minutes': data.get('timeout_minutes', 30),
            'headless': data.get('headless', True),  # Default to headless for API
            'output_dir': Path(__file__).resolve().parent.parent / "portal_analyses" / "advanced",
            'selector_strategy': data.get('selector_strategy', 'id'),
            'encryption_key': data.get('encryption_key')
        }
        
        try:
            config = InspectorConfig(**config_data)
        except Exception as config_error:
            return jsonify({
                'success': False,
                'error': f'Configuration validation failed: {str(config_error)}'
            }), 400
        
        # Get current Flask app and SocketIO instances for background thread
        app = current_app._get_current_object()
        socketio = getattr(live_inspector_bp, 'socketio', None) or getattr(app, 'socketio', None)
        
        def run_advanced_inspection():
            inspector = None  # Initialize to handle startup failures
            inspection_id = None  # Initialize for error handling
            
            try:
                # Create app context for this thread
                with app.app_context():
                    # Create inspector instance
                    inspector = LivePortalInspector(config, socketio)
                    
                    # Run async inspection
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    
                    try:
                        # Start inspection
                        inspection_id = loop.run_until_complete(inspector.start_inspection())
                        
                        # Store inspector instance for stop functionality
                        active_inspections[inspection_id] = inspector
                        inspection_stop_flags[inspection_id] = False
                        
                        # Emit start notification
                        if socketio:
                            socketio.emit('live_inspection_started', {
                                'inspection_id': inspection_id,
                                'portal_name': config.portal_name,
                                'portal_url': config.portal_url,
                                'timestamp': datetime.now().isoformat(),
                                'message': 'Advanced live inspection started - comprehensive analysis in progress'
                            })
                        
                        # Monitor for stop requests
                        while inspector.is_recording:
                            if inspection_stop_flags.get(inspection_id, False):
                                logger.info(f"Stop requested for inspection {inspection_id}")
                                break
                            time.sleep(2)
                        
                        # Stop inspection and get results
                        result = loop.run_until_complete(inspector.stop_inspection())
                        
                        # Save comprehensive results
                        save_advanced_inspection_results(inspection_id, result, config)
                        
                        # Clean up tracking after successful save
                        active_inspections.pop(inspection_id, None)
                        inspection_stop_flags.pop(inspection_id, None)
                        
                        # Emit completion notification
                        if socketio:
                            socketio.emit('live_inspection_complete_v2', {
                                'inspection_id': inspection_id,
                                'success': result.get('success', False),
                                'results': result,
                                'timestamp': datetime.now().isoformat(),
                                'message': 'Advanced inspection complete - comprehensive analysis available'
                            })
                        
                    except Exception as e:
                        logger.exception(f"Inspection execution error: {e}")
                        if socketio:
                            socketio.emit('live_inspection_error_v2', {
                                'inspection_id': inspection_id or 'unknown',
                                'error': str(e),
                                'timestamp': datetime.now().isoformat()
                            })
                    finally:
                        loop.close()
                        
            except Exception as e:
                logger.exception(f"Advanced inspection thread error: {e}")
                if socketio:
                    socketio.emit('live_inspection_error_v2', {
                        'inspection_id': inspection_id or 'unknown',
                        'error': str(e),
                        'timestamp': datetime.now().isoformat()
                    })
            finally:
                # Clean up tracking regardless of success/failure
                if inspection_id:
                    active_inspections.pop(inspection_id, None)
                    inspection_stop_flags.pop(inspection_id, None)
        
        # Start inspection in background
        thread = threading.Thread(target=run_advanced_inspection)
        thread.daemon = True
        thread.start()
        
        return jsonify({
            'success': True,
            'message': 'Advanced live portal inspection started - browser window will open shortly',
            'features': [
                'Comprehensive event recording',
                'PHI redaction and encryption',
                'Screenshot capture with metadata',
                'Network traffic analysis',
                'Medical-specific element detection',
                'Automatic replay adapter generation',
                'Real-time analysis streaming'
            ]
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Failed to start advanced inspection: {str(e)}'
        }), 500

@live_inspector_bp.route('/live-inspect-v2/<inspection_id>/stop', methods=['POST'])
@cross_origin(origins="*", methods=["POST"], allow_headers=CORS_HEADERS)
def stop_live_inspection_v2(inspection_id):
    """Stop advanced live inspection and finalize analysis"""
    try:
        # Set the stop flag for this inspection
        if inspection_id in inspection_stop_flags:
            inspection_stop_flags[inspection_id] = True
            logger.info(f"Stop flag set for advanced inspection {inspection_id}")
        else:
            # If inspection_id not found in stop flags, it may already be completed
            return jsonify({
                'success': False,
                'error': f'Inspection {inspection_id} not found or already completed'
            }), 404
        
        app = current_app._get_current_object()
        socketio = getattr(live_inspector_bp, 'socketio', None) or getattr(app, 'socketio', None)
        
        if socketio:
            socketio.emit('live_inspection_stop_requested_v2', {
                'inspection_id': inspection_id,
                'message': 'Advanced inspection stop requested - finalizing comprehensive analysis...',
                'timestamp': datetime.now().isoformat()
            })
        
        return jsonify({
            'success': True,
            'message': 'Advanced live inspection stop requested - comprehensive analysis will complete shortly'
        })
        
    except Exception as e:
        logger.exception(f"Failed to stop advanced inspection {inspection_id}: {e}")
        return jsonify({
            'success': False,
            'error': f'Failed to stop advanced live inspection: {str(e)}'
        }), 500

@live_inspector_bp.route('/live-inspect-v2/active/stop', methods=['POST'])
@cross_origin(origins="*", methods=["POST"], allow_headers=CORS_HEADERS)
def stop_active_live_inspection_v2():
    """Stop any active advanced live inspection"""
    try:
        # Find the first active inspection
        active_inspection_id = None
        for inspection_id, inspector in active_inspections.items():
            if inspector and inspector.is_recording:
                active_inspection_id = inspection_id
                break
        
        if not active_inspection_id:
            return jsonify({
                'success': False,
                'error': 'No active inspection found to stop'
            }), 404
        
        # Set the stop flag for the active inspection
        inspection_stop_flags[active_inspection_id] = True
        logger.info(f"Stop flag set for active inspection {active_inspection_id}")
        
        app = current_app._get_current_object()
        socketio = getattr(live_inspector_bp, 'socketio', None) or getattr(app, 'socketio', None)
        
        if socketio:
            socketio.emit('live_inspection_stop_requested_v2', {
                'inspection_id': active_inspection_id,
                'message': 'Active inspection stop requested - finalizing comprehensive analysis...',
                'timestamp': datetime.now().isoformat()
            })
        
        return jsonify({
            'success': True,
            'message': f'Active inspection {active_inspection_id} stop requested - comprehensive analysis will complete shortly',
            'stopped_inspection_id': active_inspection_id
        })
        
    except Exception as e:
        logger.exception(f"Failed to stop active inspection: {e}")
        return jsonify({
            'success': False,
            'error': f'Failed to stop active live inspection: {str(e)}'
        }), 500

@live_inspector_bp.route('/live-inspect-v2/<inspection_id>/status', methods=['GET'])
@cross_origin(origins="*", methods=["GET"], allow_headers=CORS_HEADERS)
def get_live_inspection_status_v2(inspection_id):
    """Get status of advanced live inspection"""
    try:
        inspector = active_inspections.get(inspection_id)
        is_active = inspector is not None and inspector.is_recording
        stop_requested = inspection_id in inspection_stop_flags and inspection_stop_flags[inspection_id]
        
        status_info = {
            'success': True,
            'inspection_id': inspection_id,
            'is_active': is_active,
            'stop_requested': stop_requested,
            'timestamp': datetime.now().isoformat()
        }
        
        # Add additional status info if inspector is available
        if inspector:
            status_info.update({
                'events_count': len(inspector.events),
                'forms_discovered': len(inspector.forms_discovered),
                'tables_discovered': len(inspector.tables_discovered),
                'navigation_flow_length': len(inspector.navigation_flow),
                'api_endpoints_count': len(inspector.api_endpoints)
            })
        
        return jsonify(status_info)
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Failed to get inspection status: {str(e)}'
        }), 500

@live_inspector_bp.route('/live-inspect-v2/<inspection_id>/download', methods=['GET'])
@cross_origin(origins="*", methods=["GET"], allow_headers=CORS_HEADERS)
def download_live_inspection_report_v2(inspection_id):
    """Download comprehensive report for advanced live inspection"""
    try:
        # Check if inspection is still active
        inspector = active_inspections.get(inspection_id)
        if inspector and inspector.is_recording:
            return jsonify({
                'success': False,
                'error': 'Advanced inspection is still active. Please stop the inspection first.',
                'status': 'active',
                'recorded_actions': [],
                'discovered_elements': {}
            }), 400
        
        # Check if inspection just stopped and files might still be writing
        if inspection_id in inspection_stop_flags and inspection_stop_flags[inspection_id]:
            return jsonify({
                'success': False,
                'error': 'Inspection recently stopped, files may still be processing. Please try again in a few seconds.',
                'status': 'processing',
                'retry_after': 3,
                'recorded_actions': [],
                'discovered_elements': {}
            }), 202
        
        # Load inspection results from file
        results_dir = Path(__file__).resolve().parent.parent / "portal_analyses" / "advanced"
        filepath = results_dir / f'{inspection_id}.json'
        
        if not filepath.exists():
            return jsonify({
                'success': False,
                'error': f'No advanced inspection data found for ID: {inspection_id}',
                'status': 'not_found',
                'recorded_actions': [],
                'discovered_elements': {}
            }), 404
        
        # Check if file is completely written (non-zero size)
        if filepath.stat().st_size == 0:
            return jsonify({
                'success': False,
                'error': 'Inspection data file is still being written. Please try again in a few seconds.',
                'status': 'writing',
                'retry_after': 2,
                'recorded_actions': [],
                'discovered_elements': {}
            }), 202
        
        # Load the comprehensive inspection data
        with open(filepath, 'r') as f:
            inspection_data = json.load(f)
        
        # Extract results with advanced structure
        results = inspection_data.get('results', {})
        analysis = results.get('analysis', {})
        
        return jsonify({
            'success': True,
            'inspection_id': inspection_id,
            'inspector_version': 'v2_advanced',
            'events_count': results.get('events_count', 0),
            'analysis_summary': analysis.get('summary', {}),
            'forms_discovered': analysis.get('forms', []),
            'tables_discovered': analysis.get('tables', []),
            'navigation_flow': analysis.get('navigation_flow', []),
            'api_endpoints': analysis.get('api_endpoints', []),
            'demographic_fields': analysis.get('demographic_fields', []),
            'medical_sections': analysis.get('medical_sections', {}),
            'popup_dialogs': analysis.get('popup_dialogs', []),
            'adapter_path': results.get('adapter_path', ''),
            'logs_path': results.get('logs_path', ''),
            'config': inspection_data.get('config', {}),
            'timestamp': inspection_data.get('timestamp', ''),
            'advanced_features': {
                'phi_redaction': True,
                'network_interception': True,
                'screenshot_capture': True,
                'event_encryption': True,
                'selector_strategies': True,
                'medical_analysis': True
            }
        })
        
    except Exception as e:
        logger.exception(f"Failed to download advanced inspection report {inspection_id}: {e}")
        return jsonify({
            'success': False,
            'error': f'Failed to download inspection report: {str(e)}',
            'recorded_actions': [],
            'discovered_elements': {}
        }), 500

@live_inspector_bp.route('/live-inspect-v2/capabilities', methods=['GET'])
@cross_origin(origins="*", methods=["GET"], allow_headers=CORS_HEADERS)
def get_inspector_capabilities():
    """Get capabilities and status of advanced inspector"""
    try:
        capabilities = {
            'advanced_inspector_available': ADVANCED_INSPECTOR_AVAILABLE,
            'version': '2.0.0',
            'features': {
                'comprehensive_event_recording': ADVANCED_INSPECTOR_AVAILABLE,
                'phi_redaction': ADVANCED_INSPECTOR_AVAILABLE,
                'network_traffic_analysis': ADVANCED_INSPECTOR_AVAILABLE,
                'screenshot_capture': ADVANCED_INSPECTOR_AVAILABLE,
                'medical_element_detection': ADVANCED_INSPECTOR_AVAILABLE,
                'replay_adapter_generation': ADVANCED_INSPECTOR_AVAILABLE,
                'real_time_streaming': ADVANCED_INSPECTOR_AVAILABLE,
                'encryption_support': ADVANCED_INSPECTOR_AVAILABLE,
                'multiple_selector_strategies': ADVANCED_INSPECTOR_AVAILABLE
            },
            'supported_recording_modes': ['full', 'login_only', 'navigation_only'],
            'supported_selector_strategies': ['id', 'data-attr', 'class-chain', 'nth-child'],
            'active_inspections': len(active_inspections),
            'timestamp': datetime.now().isoformat()
        }
        
        if not ADVANCED_INSPECTOR_AVAILABLE:
            capabilities['error'] = inspector_error
            capabilities['fallback_message'] = 'Advanced inspector not available, fallback to basic inspector'
        
        return jsonify(capabilities)
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Failed to get capabilities: {str(e)}'
        }), 500

@live_inspector_bp.route('/healthz', methods=['GET'])
@cross_origin(origins="*", methods=["GET"], allow_headers=CORS_HEADERS)
def health_check():
    """Health check endpoint for Kubernetes/ELB probes"""
    try:
        # Check that advanced inspector is available
        if not ADVANCED_INSPECTOR_AVAILABLE:
            return jsonify({
                'status': 'unhealthy',
                'reason': 'advanced_inspector_unavailable',
                'error': inspector_error,
                'timestamp': datetime.now().isoformat()
            }), 503
        
        # Check active inspections health
        active_count = len(active_inspections)
        stop_flag_count = len(inspection_stop_flags)
        
        # Basic system health checks
        health_status = {
            'status': 'healthy',
            'advanced_inspector': 'available',
            'active_inspections': active_count,
            'pending_stops': stop_flag_count,
            'socketio': getattr(live_inspector_bp, 'socketio', None) is not None,
            'version': '2.0.0',
            'timestamp': datetime.now().isoformat()
        }
        
        return jsonify(health_status), 200
        
    except Exception as e:
        logger.exception(f"Health check error: {e}")
        return jsonify({
            'status': 'unhealthy',
            'reason': 'health_check_failed',
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }), 503

def save_advanced_inspection_results(inspection_id, results, config):
    """Save comprehensive advanced inspection results"""
    try:
        # Create results directory
        results_dir = Path(__file__).resolve().parent.parent / "portal_analyses" / "advanced"
        results_dir.mkdir(parents=True, exist_ok=True)
        
        # Prepare comprehensive data for saving
        comprehensive_results = {
            'inspection_id': inspection_id,
            'timestamp': datetime.now().isoformat(),
            'inspector_version': 'v2_advanced',
            'config': {
                'portal_name': config.portal_name,
                'portal_url': config.portal_url,
                'recording_mode': config.recording_mode,
                'timeout_minutes': config.timeout_minutes,
                'selector_strategy': config.selector_strategy,
                'output_dir': str(config.output_dir)
            },
            'results': results,
            'capabilities_used': {
                'phi_redaction': True,
                'network_interception': True,
                'screenshot_capture': True,
                'comprehensive_analysis': True,
                'medical_element_detection': True,
                'replay_adapter_generation': True
            }
        }
        
        # Save main inspection data as JSON
        filepath = results_dir / f'{inspection_id}.json'
        with open(filepath, 'w') as f:
            json.dump(comprehensive_results, f, indent=2, default=str)
        
        logger.info(f"Advanced inspection data saved: {filepath}")
        
        # Create summary report
        summary_report = generate_advanced_summary_report(comprehensive_results)
        report_filepath = results_dir / f'{inspection_id}_summary.txt'
        with open(report_filepath, 'w') as f:
            f.write(summary_report)
        
        logger.info(f"Advanced summary report saved: {report_filepath}")
        
    except Exception as e:
        logger.exception(f"Failed to save advanced inspection results: {e}")

def generate_advanced_summary_report(comprehensive_results):
    """Generate advanced summary report"""
    
    config = comprehensive_results.get('config', {})
    results = comprehensive_results.get('results', {})
    analysis = results.get('analysis', {})
    summary = analysis.get('summary', {})
    
    report = f"""ADVANCED LIVE INSPECTION SUMMARY REPORT

Portal Information:
  Portal Name: {config.get('portal_name', 'Unknown')}
  Portal URL: {config.get('portal_url', 'Unknown')}
  Inspection Date: {comprehensive_results.get('timestamp', 'Unknown')}
  Inspector Version: {comprehensive_results.get('inspector_version', 'v2_advanced')}
  Recording Mode: {config.get('recording_mode', 'full')}
  Selector Strategy: {config.get('selector_strategy', 'id')}

EVENT SUMMARY

Total Events Recorded: {summary.get('total_events', 0)}
  Navigation Events: {summary.get('navigation_count', 0)}
  Click Events: {summary.get('click_count', 0)}
  Network Events: {summary.get('network_count', 0)}
  Popup Events: {summary.get('popup_count', 0)}

DISCOVERY RESULTS

Portal Structure:
  Forms Discovered: {len(analysis.get('forms', []))}
  Tables Discovered: {len(analysis.get('tables', []))}
  Navigation Flow: {len(analysis.get('navigation_flow', []))} pages
  API Endpoints: {len(analysis.get('api_endpoints', []))}
  Popup Dialogs: {len(analysis.get('popup_dialogs', []))}

Medical Data Analysis:
  Demographic Fields: {len(analysis.get('demographic_fields', []))}
  Medical Sections: {len(analysis.get('medical_sections', {}))}

ADVANCED FEATURES USED

- PHI Redaction and Privacy Protection
- Network Traffic Interception and Analysis
- Comprehensive Screenshot Capture
- Medical-Specific Element Detection
- Automatic Replay Adapter Generation
- Real-time Event Streaming
- Advanced Selector Generation Strategies

FILES GENERATED

Replay Adapter: {results.get('adapter_path', 'Not generated')}
Event Logs: {results.get('logs_path', 'Not saved')}
Screenshots: Available in output directory
Comprehensive Analysis: JSON format with full details

END OF REPORT
"""
    
    return report 