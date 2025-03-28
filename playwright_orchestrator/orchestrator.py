import asyncio
import threading
import logging
import json
import importlib.util
import sys
import os
from pathlib import Path
from playwright.async_api import async_playwright
from datetime import datetime
from typing import Dict, Optional, Any

# Get absolute paths
SCRIPT_DIR = Path(__file__).parent.absolute()
PROJECT_ROOT = SCRIPT_DIR.parent
BACKEND_DIR = PROJECT_ROOT / "backend"

# Ensure logs directory exists
LOGS_DIR = PROJECT_ROOT / "logs"
LOGS_DIR.mkdir(exist_ok=True)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOGS_DIR / 'orchestrator.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Add paths to Python path
paths_to_add = [str(PROJECT_ROOT), str(BACKEND_DIR)]
for path in paths_to_add:
    if path not in sys.path:
        sys.path.insert(0, path)

logger.info(f"🔧 Script dir: {SCRIPT_DIR}")
logger.info(f"🔧 Project root: {PROJECT_ROOT}")
logger.info(f"🔧 Backend dir: {BACKEND_DIR}")
logger.info(f"🔧 Python path: {sys.path[:3]}...")

# Import results storage module
try:
    from backend.results_storage import results_storage
    RESULTS_STORAGE_AVAILABLE = True
    logger.info("✅ Results storage module loaded successfully")
except Exception as e:
    logger.warning(f"⚠️ Failed to load results storage: {e}")
    RESULTS_STORAGE_AVAILABLE = False
    results_storage = None

# Dynamic import of Flask components
def load_flask_components():
    """Dynamically load Flask components without causing import issues"""
    try:
        logger.info("🔄 Attempting to load Flask components...")
        
        # Method 1: Try direct import with path manipulation
        original_cwd = os.getcwd()
        try:
            os.chdir(BACKEND_DIR)
            
            # Import app.py as a module
            app_spec = importlib.util.spec_from_file_location("app", BACKEND_DIR / "app.py")
            app_module = importlib.util.module_from_spec(app_spec)
            sys.modules["app"] = app_module  # Add to sys.modules to prevent reimport
            app_spec.loader.exec_module(app_module)
            
            # Import models.py as a module  
            models_spec = importlib.util.spec_from_file_location("models", BACKEND_DIR / "models.py")
            models_module = importlib.util.module_from_spec(models_spec)
            sys.modules["models"] = models_module  # Add to sys.modules
            models_spec.loader.exec_module(models_module)
            
            create_app = app_module.create_app
            db = models_module.db
            ExtractionJob = models_module.ExtractionJob
            
            logger.info("✅ Flask components loaded successfully via dynamic import")
            return create_app, db, ExtractionJob, True
            
        finally:
            os.chdir(original_cwd)
            
    except Exception as e:
        logger.warning(f"⚠️ Failed to load Flask components: {e}")
        logger.info("📝 Continuing without Flask - status updates will be logged only")
        return None, None, None, False

# Load Flask components
create_app, db, ExtractionJob, FLASK_AVAILABLE = load_flask_components()

def _get_browser_args():
    """Get browser arguments for different environments"""
    base_args = [
        '--no-sandbox', 
        '--disable-dev-shm-usage', 
        '--disable-gpu',
        '--start-maximized',
        '--disable-background-timer-throttling',
        '--disable-renderer-backgrounding',
        '--disable-backgrounding-occluded-windows',
        '--disable-features=TranslateUI',
        '--no-first-run'
    ]
    
    # Additional args for headless environments
    if os.environ.get('SSH_CONNECTION') or os.environ.get('SSH_CLIENT'):
        base_args.extend([
            '--disable-extensions',
            '--disable-plugins'
        ])
    
    return base_args

class PlaywrightJobRunner:
    """Handles individual job execution with Playwright"""
    
    def __init__(self, job_id: int, target_url: str, adapter_script_path: str, 
                 mode: str, patient_identifier: Optional[str], job_parameters: Dict, app_context_factory):
        self.job_id = job_id
        self.target_url = target_url
        self.adapter_script_path = adapter_script_path
        self.mode = mode
        self.patient_identifier = patient_identifier
        self.job_parameters = job_parameters or {}
        self.app_context_factory = app_context_factory
        self.login_confirmed_event = threading.Event()
        self.browser = None
        self.page = None
        
        logger.info(f"🔧 JobRunner initialized for job {job_id}")
        logger.info(f"   📍 Target: {target_url}")
        logger.info(f"   🔌 Adapter: {adapter_script_path}")
        logger.info(f"   🎯 Mode: {mode}")
        logger.info(f"   📋 Parameters: {job_parameters}")

    def signal_login(self):
        """Signal that user has confirmed login"""
        logger.info(f"✅ Login confirmation received for job {self.job_id}")
        self.login_confirmed_event.set()

    async def _wait_for_confirmation(self):
        """Wait for login confirmation"""
        logger.info(f"⏳ Waiting for user to complete login for job {self.job_id}...")
        
        max_wait_time = 600  # 10 minutes
        elapsed_time = 0
        
        while not self.login_confirmed_event.is_set() and elapsed_time < max_wait_time:
            try:
                await self.page.bring_to_front()
                await self.page.evaluate("window.focus()")
                await asyncio.sleep(5)
                elapsed_time += 5
                
                if elapsed_time % 60 == 0:
                    remaining = (max_wait_time - elapsed_time) // 60
                    logger.info(f"🕐 Still waiting... {remaining} minutes remaining")
                
            except Exception as e:
                logger.warning(f"Error keeping browser alive: {e}")
                await asyncio.sleep(1)
                elapsed_time += 1
        
        if elapsed_time >= max_wait_time:
            raise Exception(f"Timeout: Login not confirmed within {max_wait_time // 60} minutes")

    def _update_job_status(self, status: str, error_message: str = None, extracted_data: Any = None):
        """Update job status in database and save results to JSON file with proper transaction handling"""
        if not FLASK_AVAILABLE:
            logger.info(f"📝 Job {self.job_id} status: {status}" + (f" - {error_message}" if error_message else ""))
            return
        
        logger.info(f"🔄 Starting database update for job {self.job_id}: status={status}, has_data={extracted_data is not None}")
        
        # Variables to track what needs to be done
        json_filepath = None
        database_success = False
        json_success = False
        
        try:
            app = create_app()
            with app.app_context():
                # Start database transaction
                logger.info(f"🔄 Starting database transaction for job {self.job_id}")
                
                job = ExtractionJob.query.filter_by(id=self.job_id).first()
                if not job:
                    raise Exception(f"Job {self.job_id} not found in database")
                
                # Update basic job fields
                job.status = status
                job.updated_at = datetime.utcnow()
                if error_message:
                    job.error_message = error_message
                
                # Handle extracted data
                if extracted_data is not None:
                    logger.info(f"📊 Processing extracted data for job {self.job_id}")
                    
                    # Create structured format for database (same as JSON file)
                    structured_data = {
                        'extraction_metadata': {
                            'job_id': job.id,
                            'job_name': job.job_name or f'job_{job.id}',
                            'extraction_mode': job.extraction_mode or 'ALL_PATIENTS',
                            'provider_name': job.doctor_name or 'unknown_provider',
                            'portal_name': job.adapter.name if job.adapter else self.adapter_script_path.replace('.py', ''),
                            'target_url': job.target_url or '',
                            'patient_identifier': getattr(job, 'input_patient_identifier', '') or '',
                            'medication': getattr(job, 'medication', '') or '',
                            'start_date': str(getattr(job, 'start_date', '')) if getattr(job, 'start_date', '') else '',
                            'end_date': str(getattr(job, 'end_date', '')) if getattr(job, 'end_date', '') else '',
                            'extracted_at': datetime.utcnow().isoformat(),
                            'results_filename': 'database_stored',
                            'provider_directory': (job.doctor_name or 'unknown_provider').lower().replace(' ', '_')
                        },
                        'extraction_results': extracted_data
                    }
                    
                    # Validate and serialize structured data for database
                    try:
                        json_data = json.dumps(structured_data, default=str)
                        logger.info(f"✅ Structured data serialization successful: {len(json_data)} characters")
                        job.raw_extracted_data_json = json_data
                    except Exception as json_error:
                        raise Exception(f"Failed to serialize structured data: {json_error}")
                    
                    # Extract and validate parameters from the extracted data
                    if isinstance(extracted_data, list) and len(extracted_data) > 0:
                        logger.info(f"🔍 Extracting parameters from {len(extracted_data)} patient records")
                        
                        first_patient = extracted_data[0]
                        if 'extraction_summary' in first_patient and 'parameters_used' in first_patient['extraction_summary']:
                            params = first_patient['extraction_summary']['parameters_used']
                            logger.info(f"📋 Found parameters: {list(params.keys())}")
                            
                            # Update database fields with extracted parameters
                            if 'doctor_name' in params and params['doctor_name']:
                                job.doctor_name = params['doctor_name']
                                logger.info(f"✅ Updated doctor_name: {params['doctor_name']}")
                                
                            if 'medication' in params and params['medication']:
                                job.medication = params['medication']
                                logger.info(f"✅ Updated medication: {params['medication']}")
                                
                            if 'start_date' in params and params['start_date']:
                                # Convert date string to Python date object
                                try:
                                    date_str = params['start_date']
                                    if isinstance(date_str, str) and date_str.strip():
                                        # Handle MM/DD/YYYY format
                                        if '/' in date_str:
                                            parsed_date = datetime.strptime(date_str, '%m/%d/%Y').date()
                                            job.start_date = parsed_date
                                            logger.info(f"✅ Updated start_date: {date_str} -> {parsed_date}")
                                        else:
                                            logger.warning(f"⚠️ Invalid start_date format: {date_str}")
                                except Exception as date_error:
                                    logger.error(f"❌ Failed to parse start_date '{params['start_date']}': {date_error}")
                                    
                            if 'stop_date' in params and params['stop_date']:
                                # Convert date string to Python date object
                                try:
                                    date_str = params['stop_date']
                                    if isinstance(date_str, str) and date_str.strip():
                                        # Handle MM/DD/YYYY format
                                        if '/' in date_str:
                                            parsed_date = datetime.strptime(date_str, '%m/%d/%Y').date()
                                            job.end_date = parsed_date
                                            logger.info(f"✅ Updated end_date: {date_str} -> {parsed_date}")
                                        else:
                                            logger.warning(f"⚠️ Invalid end_date format: {date_str}")
                                except Exception as date_error:
                                    logger.error(f"❌ Failed to parse end_date '{params['stop_date']}': {date_error}")
                        else:
                            logger.warning(f"⚠️ No extraction_summary found in first patient record")
                    
                    # Save to JSON file BEFORE committing database transaction
                    if RESULTS_STORAGE_AVAILABLE and status == 'COMPLETED':
                        logger.info(f"💾 Attempting to save results to JSON file for job {self.job_id}")
                        
                        try:
                            # Prepare job data for results_storage
                            job_data = {
                                'id': job.id,
                                'job_name': job.job_name or f'job_{job.id}',
                                'extraction_mode': job.extraction_mode or 'ALL_PATIENTS',
                                'doctor_name': job.doctor_name or 'unknown_provider',
                                'adapter_name': job.adapter.name if job.adapter else self.adapter_script_path.replace('.py', ''),
                                'target_url': job.target_url or '',
                                'input_patient_identifier': getattr(job, 'patient_identifier', ''),
                                'medication': getattr(job, 'medication', ''),
                                'start_date': str(getattr(job, 'start_date', '')) if getattr(job, 'start_date', '') else '',
                                'end_date': str(getattr(job, 'end_date', '')) if getattr(job, 'end_date', '') else '',
                                'created_at': job.created_at,
                                'updated_at': job.updated_at
                            }
                            
                            logger.info(f"📋 Job data prepared: provider={job_data['doctor_name']}, medication={job_data['medication']}")
                            
                            # Save results to JSON file
                            json_filepath = results_storage.save_results(job_data, extracted_data)
                            json_success = True
                            
                            # Update job with saved filepath
                            job.results_file_path = json_filepath
                            
                            logger.info(f"✅ Results saved to JSON file: {json_filepath}")
                            
                        except Exception as storage_error:
                            error_msg = f"Failed to save results to JSON file: {storage_error}"
                            logger.error(f"❌ {error_msg}")
                            logger.error(f"🔧 Storage error details: {repr(storage_error)}")
                            
                            # For completed jobs, JSON saving failure should not fail the entire job
                            # but we should log it prominently
                            if status == 'COMPLETED':
                                logger.warning(f"⚠️ Job {self.job_id} completed successfully but JSON saving failed")
                                logger.warning(f"⚠️ Data is safely stored in database but no file was created")
                            else:
                                # For non-completed jobs, we might want to propagate the error
                                raise Exception(f"JSON saving failed: {storage_error}")
                    else:
                        if not RESULTS_STORAGE_AVAILABLE:
                            logger.warning(f"⚠️ Results storage not available - skipping JSON file creation")
                        elif status != 'COMPLETED':
                            logger.info(f"ℹ️ Skipping JSON file creation for non-completed status: {status}")
                
                # Commit the database transaction
                logger.info(f"💾 Committing database transaction for job {self.job_id}")
                db.session.commit()
                database_success = True
                
                # Final success logging
                log_msg = f"📊 Job {self.job_id} database update successful: status={status}"
                if extracted_data is not None:
                    data_size = len(job.raw_extracted_data_json) if job.raw_extracted_data_json else 0
                    log_msg += f", data_size={data_size} chars"
                if json_filepath:
                    log_msg += f", json_file='{json_filepath}'"
                logger.info(log_msg)
                
        except Exception as e:
            error_msg = f"Failed to update job {self.job_id} status: {str(e)}"
            logger.error(f"❌ {error_msg}")
            logger.error(f"🔧 Error details: {repr(e)}")
            
            # Rollback database transaction if it was started
            try:
                if 'db' in locals():
                    db.session.rollback()
                    logger.info(f"🔄 Database transaction rolled back for job {self.job_id}")
            except Exception as rollback_error:
                logger.error(f"❌ Failed to rollback transaction: {rollback_error}")
            
            # Clean up JSON file if it was created but database failed
            if json_success and json_filepath and not database_success:
                try:
                    import os
                    if os.path.exists(json_filepath):
                        os.remove(json_filepath)
                        logger.info(f"🧹 Cleaned up JSON file after database failure: {json_filepath}")
                except Exception as cleanup_error:
                    logger.error(f"❌ Failed to clean up JSON file: {cleanup_error}")
            
            # Re-raise the exception to ensure the caller knows about the failure
            raise Exception(error_msg) from e

    def _load_adapter_module(self):
        """Load the adapter module"""
        try:
            # Look for adapter in portal_adapters directory
            adapter_path = PROJECT_ROOT / "portal_adapters" / self.adapter_script_path
            
            if not adapter_path.exists():
                raise FileNotFoundError(f"Adapter not found: {adapter_path}")
            
            logger.info(f"📁 Loading adapter from: {adapter_path}")
            
            # Load adapter module
            spec = importlib.util.spec_from_file_location("adapter_module", adapter_path)
            adapter_module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(adapter_module)
            
            # Check for available functions in priority order
            available_functions = []
            
            # Check for new start_job function (preferred)
            if hasattr(adapter_module, 'start_job'):
                available_functions.append('start_job')
                logger.info(f"✅ Found start_job() function (preferred)")
            
            # Check for legacy functions
            if hasattr(adapter_module, 'extract_single_patient_data'):
                available_functions.append('extract_single_patient_data')
                logger.info(f"✅ Found extract_single_patient_data() function")
                
            if hasattr(adapter_module, 'extract_all_patients_data'):
                available_functions.append('extract_all_patients_data')
                logger.info(f"✅ Found extract_all_patients_data() function")
            
            # Verify we have at least one compatible function
            if not available_functions:
                raise AttributeError(f"Adapter missing required functions. Expected: start_job, extract_single_patient_data, or extract_all_patients_data")
            
            # For legacy compatibility, check if we have the specific function for the mode
            if 'start_job' not in available_functions:
                required_function = 'extract_single_patient_data' if self.mode == 'SINGLE_PATIENT' else 'extract_all_patients_data'
                if required_function not in available_functions:
                    raise AttributeError(f"Adapter missing {required_function} function for mode {self.mode}")
            
            logger.info(f"✅ Adapter loaded successfully: {self.adapter_script_path}")
            logger.info(f"📋 Available functions: {', '.join(available_functions)}")
            
            return adapter_module
            
        except Exception as e:
            logger.error(f"❌ Failed to load adapter: {str(e)}")
            raise

    def _prepare_adapter_config(self):
        """Prepare configuration for adapter with better error handling"""
        adapter_config = {}
        
        # Ensure job_parameters is a dictionary
        if not self.job_parameters:
            self.job_parameters = {}
        
        if not isinstance(self.job_parameters, dict):
            logger.warning(f"Invalid job_parameters type: {type(self.job_parameters)}, using empty dict")
            self.job_parameters = {}
        
        # Extract parameters with validation - these are REQUIRED for the adapter
        doctor_name = self.job_parameters.get('doctor_name', '')
        medication = self.job_parameters.get('medication', '')
        start_date = self.job_parameters.get('start_date', '')
        stop_date = self.job_parameters.get('stop_date', '')
        
        # Add parameters - the adapter expects these fields even if empty
        adapter_config['doctor_name'] = doctor_name.strip() if isinstance(doctor_name, str) else ''
        adapter_config['medication'] = medication.strip() if isinstance(medication, str) else ''
        adapter_config['start_date'] = start_date.strip() if isinstance(start_date, str) else ''
        adapter_config['stop_date'] = stop_date.strip() if isinstance(stop_date, str) else ''
        
        # Handle extraction mode and patient targeting
        if self.mode == 'SINGLE_PATIENT':
            adapter_config['extraction_mode'] = 'Target Patient by Name'
            
            # Handle patient identifier
            patient_id = None
            if self.patient_identifier and isinstance(self.patient_identifier, str) and self.patient_identifier.strip():
                patient_id = self.patient_identifier.strip()
            else:
                # Try to get from job_parameters
                target_name = self.job_parameters.get('target_patient_name', '')
                if target_name and isinstance(target_name, str) and target_name.strip():
                    patient_id = target_name.strip()
            
            if patient_id:
                adapter_config['patient_identifier'] = patient_id
                adapter_config['target_patient_name'] = patient_id
                adapter_config['input_patient_identifier'] = patient_id  # Alternative name some adapters might expect
            else:
                logger.warning("⚠️ Single patient mode but no patient identifier provided")
                adapter_config['patient_identifier'] = ''
                adapter_config['target_patient_name'] = ''
                adapter_config['input_patient_identifier'] = ''
        else:
            adapter_config['extraction_mode'] = 'All Patients'
            adapter_config['patient_identifier'] = ''
        
        # Add metadata
        adapter_config['job_id'] = self.job_id
        adapter_config['target_url'] = self.target_url
        adapter_config['mode'] = self.mode
        
        # Log configuration for debugging
        logger.info(f"📋 Adapter configuration prepared:")
        for key, value in adapter_config.items():
            if key in ['doctor_name', 'medication', 'extraction_mode', 'target_patient_name']:
                logger.info(f"   {key}: '{value}'" if value else f"   {key}: <empty>")
        
        # Validation warnings
        if not adapter_config.get('doctor_name'):
            logger.warning("⚠️ No doctor_name provided - this may be required by the adapter")
        if not adapter_config.get('medication'):
            logger.warning("⚠️ No medication provided - this may be required by the adapter")
        if not adapter_config.get('start_date'):
            logger.warning("⚠️ No start_date provided - this may be required by the adapter")
        if not adapter_config.get('stop_date'):
            logger.warning("⚠️ No stop_date provided - this may be required by the adapter")
        
        return adapter_config

    async def run_job(self):
        """Main job execution method"""
        try:
            logger.info(f"🚀 Starting job {self.job_id} execution")
            
            # Step 1: Launch browser
            self._update_job_status('LAUNCHING_BROWSER')
            
            async with async_playwright() as p:
                try:
                    # Launch browser in headed mode for manual login
                    self.browser = await p.chromium.launch(
                        headless=False,
                        args=_get_browser_args()
                    )
                    
                    context = await self.browser.new_context(
                        viewport={'width': 1200, 'height': 800}
                    )
                    self.page = await context.new_page()
                    
                    # Set window title and focus
                    await self.page.evaluate(f"""
                        document.title = 'WebAutoDash - Job {self.job_id} - Please Login Here';
                    """)
                    await self.page.bring_to_front()
                    await self.page.evaluate("window.focus()")
                    
                    logger.info(f"✅ Browser launched successfully for job {self.job_id}")
                    
                except Exception as browser_error:
                    error_msg = f"Browser launch failed: {str(browser_error)}"
                    
                    # Add helpful error messages for common issues
                    if "display" in str(browser_error).lower():
                        error_msg += "\n\n🔧 Display issue detected. Try:"
                        error_msg += "\n1. ssh -X username@hostname (for X11 forwarding)"
                        error_msg += "\n2. export DISPLAY=:0.0 (if running locally)"
                        error_msg += "\n3. Setup VNC server for remote access"
                    
                    logger.error(f"❌ {error_msg}")
                    self._update_job_status('FAILED', error_message=error_msg)
                    return
                
                # Step 2: Navigate to target URL
                try:
                    logger.info(f"🔄 Navigating to: {self.target_url}")
                    await self.page.goto(self.target_url, wait_until='domcontentloaded', timeout=30000)
                    await self.page.bring_to_front()
                    await self.page.evaluate("window.focus()")
                    logger.info(f"✅ Navigation successful")
                except Exception as nav_error:
                    raise Exception(f"Navigation failed: {str(nav_error)}")
                
                # Step 3: Wait for login confirmation
                self._update_job_status('AWAITING_USER_CONFIRMATION')
                logger.info(f"👤 Please log in to the portal and click 'Confirm Login' in WebAutoDash")
                
                await asyncio.sleep(2)  # Brief pause
                await self._wait_for_confirmation()
                
                # Step 4: Execute data extraction
                self._update_job_status('EXTRACTING')
                logger.info(f"🔧 Starting data extraction for job {self.job_id}")
                
                # Load adapter and prepare config
                adapter_module = self._load_adapter_module()
                adapter_config = self._prepare_adapter_config()
                
                # Execute extraction - TRY start_job() FIRST, then fall back to old functions
                try:
                    logger.info(f"🔧 Attempting to use start_job() function...")
                    
                    # Check if adapter has start_job function
                    if hasattr(adapter_module, 'start_job'):
                        logger.info(f"✅ Found start_job() function, using it with job_parameters")
                        
                        # Call start_job with both page and job_parameters
                        result = await adapter_module.start_job(self.page, adapter_config)
                        
                        logger.info(f"✅ start_job() completed successfully")
                    
                    else:
                        logger.info(f"⚠️ start_job() not found, falling back to legacy functions")
                        
                        # Fall back to legacy extraction functions
                        if self.mode == 'SINGLE_PATIENT':
                            logger.info(f"👤 Extracting single patient: {self.patient_identifier}")
                            
                            if hasattr(adapter_module, 'extract_single_patient_data'):
                                result = await adapter_module.extract_single_patient_data(
                                    self.page, self.patient_identifier, config=adapter_config
                                )
                            else:
                                raise AttributeError("Adapter missing extract_single_patient_data function")
                                
                        elif self.mode == 'ALL_PATIENTS':
                            logger.info("🏥 Extracting all patients")
                            
                            if hasattr(adapter_module, 'extract_all_patients_data'):
                                result = await adapter_module.extract_all_patients_data(
                                    self.page, config=adapter_config
                                )
                            else:
                                raise AttributeError("Adapter missing extract_all_patients_data function")
                                
                        else:
                            raise ValueError(f"Unknown extraction mode: {self.mode}")
                    
                    # Log extraction results
                    if isinstance(result, list) and len(result) > 0:
                        successful_count = len([r for r in result if r.get('extraction_status') == 'complete'])
                        
                        logger.info(f"📊 EXTRACTION COMPLETED:")
                        logger.info(f"   👥 Patients processed: {len(result)}")
                        logger.info(f"   ✅ Successful extractions: {successful_count}")
                        
                        if successful_count > 0:
                            # Count extracted data
                            totals = {
                                'medications': sum(len(r.get('all_medications', [])) for r in result),
                                'diagnoses': sum(len(r.get('all_diagnoses', [])) for r in result),
                                'health_concerns': sum(len(r.get('all_health_concerns', [])) for r in result),
                                'allergies': sum(len(r.get('all_allergies', [])) for r in result)
                            }
                            
                            for data_type, count in totals.items():
                                if count > 0:
                                    logger.info(f"   📋 {data_type.title()}: {count}")
                    
                    # Validate extraction results before marking as completed
                    if result is None:
                        raise Exception("Adapter returned None - extraction failed")
                    
                    if isinstance(result, list) and len(result) == 0:
                        raise Exception("Adapter returned empty list - no data extracted")
                    
                    # Validate result structure for proper data
                    if isinstance(result, list):
                        valid_records = [r for r in result if r.get('extraction_status') == 'complete']
                        if len(valid_records) == 0:
                            logger.warning(f"⚠️ No successful extractions found in {len(result)} records")
                            logger.warning(f"⚠️ This may indicate an extraction issue")
                    
                    # Mark job as completed
                    logger.info(f"✅ Data extraction completed successfully for job {self.job_id}")
                    logger.info(f"📊 Calling _update_job_status with {len(result) if isinstance(result, list) else 'non-list'} records")
                    
                    self._update_job_status('COMPLETED', extracted_data=result)
                    
                    # Keep browser open for user review
                    logger.info("⏳ Keeping browser open for 30 seconds to review results...")
                    logger.info("💡 You can review the extracted data before the browser closes automatically")
                    await asyncio.sleep(30)
                    
                except Exception as adapter_error:
                    error_msg = f"Adapter execution failed: {str(adapter_error)}"
                    logger.error(f"❌ {error_msg}")
                    logger.error(f"🔧 Error details: {repr(adapter_error)}")
                    
                    # More specific error handling
                    if "missing 1 required positional argument" in str(adapter_error):
                        error_msg += f"\n\n🔧 Function signature mismatch detected."
                        error_msg += f"\n💡 The adapter function expects different parameters than provided."
                        error_msg += f"\n📋 Job parameters: {adapter_config}"
                        error_msg += f"\n🎯 Mode: {self.mode}"
                    
                    self._update_job_status('FAILED', error_message=error_msg)
                    
                    # Keep browser open longer for debugging
                    logger.info("⏳ Keeping browser open for 60 seconds for debugging...")
                    logger.info("🔍 Check the browser window for any visible errors")
                    await asyncio.sleep(60)
                    raise
                
        except Exception as e:
            error_msg = f"Job execution failed: {str(e)}"
            logger.error(f"❌ Job {self.job_id}: {error_msg}")
            self._update_job_status('FAILED', error_message=error_msg)
            
            # Keep browser open for debugging
            try:
                if self.page:
                    logger.info("⏳ Keeping browser open for 90 seconds for debugging...")
                    await asyncio.sleep(90)
            except:
                pass
        
        finally:
            # Cleanup browser resources
            try:
                if self.page:
                    await self.page.close()
                if self.browser:
                    await self.browser.close()
                logger.info(f"🧹 Browser cleanup completed for job {self.job_id}")
            except Exception as cleanup_error:
                logger.error(f"❌ Cleanup failed for job {self.job_id}: {str(cleanup_error)}")


class PlaywrightSessionManager:
    """Singleton manager for all active Playwright sessions"""
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super(PlaywrightSessionManager, cls).__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if not self._initialized:
            self.active_jobs: Dict[int, PlaywrightJobRunner] = {}
            self.job_threads: Dict[int, threading.Thread] = {}
            self._initialized = True
            logger.info("🔧 PlaywrightSessionManager initialized")
    
    def start_job(self, job_id: int, target_url: str, adapter_script_path: str, 
                  mode: str, patient_identifier: Optional[str], job_parameters: Dict, app_context_factory) -> bool:
        """Start a new extraction job"""
        try:
            if job_id in self.active_jobs:
                logger.warning(f"⚠️ Job {job_id} is already running")
                return False
            
            # Create job runner
            job_runner = PlaywrightJobRunner(
                job_id, target_url, adapter_script_path, mode, patient_identifier, job_parameters, app_context_factory
            )
            
            # Create thread for async execution
            def run_async_job():
                try:
                    asyncio.run(job_runner.run_job())
                finally:
                    # Remove from active jobs when done
                    with self._lock:
                        self.active_jobs.pop(job_id, None)
                        self.job_threads.pop(job_id, None)
            
            job_thread = threading.Thread(target=run_async_job, name=f"Job-{job_id}")
            
            # Store references
            self.active_jobs[job_id] = job_runner
            self.job_threads[job_id] = job_thread
            
            # Start the job thread
            job_thread.start()
            logger.info(f"🚀 Started job {job_id} in thread {job_thread.name}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to start job {job_id}: {str(e)}")
            return False
    
    def signal_login_confirmed(self, job_id: int) -> bool:
        """Signal that user has confirmed login for a job"""
        try:
            with self._lock:
                if job_id in self.active_jobs:
                    self.active_jobs[job_id].signal_login()
                    logger.info(f"✅ Login confirmation signaled for job {job_id}")
                    return True
                else:
                    logger.warning(f"⚠️ Job {job_id} not found in active jobs")
                    return False
        except Exception as e:
            logger.error(f"❌ Failed to signal login confirmation for job {job_id}: {str(e)}")
            return False
    
    def get_active_jobs(self) -> Dict[int, str]:
        """Get list of currently active job IDs"""
        with self._lock:
            return {job_id: "ACTIVE" for job_id in self.active_jobs.keys()}
    
    def is_job_active(self, job_id: int) -> bool:
        """Check if a job is currently active"""
        with self._lock:
            return job_id in self.active_jobs

# Log initialization status
logger.info(f"🔧 Orchestrator initialized")
logger.info(f"📊 Flask available: {FLASK_AVAILABLE}")
logger.info(f"📁 Portal adapters directory: {PROJECT_ROOT / 'portal_adapters'}")