"""
WebAutoDash JSON File Monitor
Automatically detects and processes new JSON extraction files with provider separation
"""

import os
import time
import json
import logging
from pathlib import Path
from threading import Thread
from typing import Dict, Set, Any
import hashlib
from datetime import datetime

from data_processor_provider import provider_processor
from db_connection_provider import provider_db_manager

logger = logging.getLogger(__name__)

class JSONFileMonitor:
    """
    Monitors the Results directory for new JSON files and automatically processes them
    Maintains provider separation and prevents duplicate processing
    """
    
    def __init__(self, results_directory: str = "Results"):
        self.results_directory = Path(results_directory)
        self.processed_files = set()
        self.processed_files_cache_file = "processed_files_cache.json"
        self.monitoring = False
        self.monitor_thread = None
        
        # Load previously processed files
        self._load_processed_files_cache()
        
        # Stats
        self.stats = {
            'monitoring_started': None,
            'files_detected': 0,
            'files_processed': 0,
            'processing_errors': 0,
            'providers_discovered': set(),
            'last_activity': None
        }
    
    def start_monitoring(self, check_interval: int = 10):
        """
        Start monitoring the Results directory for new JSON files
        
        Args:
            check_interval: Seconds between directory checks
        """
        if self.monitoring:
            logger.warning("File monitor is already running")
            return
        
        self.monitoring = True
        self.stats['monitoring_started'] = datetime.now()
        
        # Start monitoring thread
        self.monitor_thread = Thread(target=self._monitor_loop, args=(check_interval,), daemon=True)
        self.monitor_thread.start()
        
        logger.info(f"JSON file monitoring started for directory: {self.results_directory}")
        provider_db_manager.log_system_event('INFO', 'FileMonitor', 
                                           f'Started monitoring {self.results_directory}')
    
    def stop_monitoring(self):
        """Stop the file monitoring"""
        if not self.monitoring:
            logger.warning("File monitor is not running")
            return
        
        self.monitoring = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=5)
        
        self._save_processed_files_cache()
        
        logger.info("JSON file monitoring stopped")
        provider_db_manager.log_system_event('INFO', 'FileMonitor', 'Stopped monitoring')
    
    def _monitor_loop(self, check_interval: int):
        """Main monitoring loop that runs in background thread"""
        logger.info(f"File monitor loop started with {check_interval}s interval")
        
        while self.monitoring:
            try:
                self._scan_and_process_files()
                time.sleep(check_interval)
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
                provider_db_manager.log_system_event('ERROR', 'FileMonitor', 
                                                   f'Monitor loop error: {str(e)}')
                time.sleep(check_interval)
    
    def _scan_and_process_files(self):
        """Scan for new JSON files and process them"""
        if not self.results_directory.exists():
            logger.warning(f"Results directory does not exist: {self.results_directory}")
            return
        
        # Get all JSON files in provider subdirectories
        json_files = self._find_json_files()
        
        # Filter out already processed files
        new_files = [f for f in json_files if self._get_file_signature(f) not in self.processed_files]
        
        if new_files:
            logger.info(f"Found {len(new_files)} new JSON files to process")
            self.stats['files_detected'] += len(new_files)
            self.stats['last_activity'] = datetime.now()
            
            for json_file in new_files:
                self._process_single_file(json_file)
    
    def _find_json_files(self) -> list:
        """Find all JSON files in provider subdirectories"""
        json_files = []
        
        try:
            # Look for provider directories
            for provider_dir in self.results_directory.iterdir():
                if provider_dir.is_dir():
                    # Look for JSON files in each provider directory
                    for json_file in provider_dir.glob("*.json"):
                        json_files.append(json_file)
            
            return json_files
        
        except Exception as e:
            logger.error(f"Error scanning for JSON files: {e}")
            return []
    
    def _process_single_file(self, json_file: Path):
        """Process a single JSON file"""
        file_signature = self._get_file_signature(json_file)
        
        try:
            logger.info(f"Processing new file: {json_file}")
            
            # Process the file using provider processor
            result = provider_processor.process_json_file(str(json_file))
            
            if result['success']:
                # Mark as processed
                self.processed_files.add(file_signature)
                self.stats['files_processed'] += 1
                self.stats['providers_discovered'].add(result['provider_name'])
                
                logger.info(f"Successfully processed {json_file}: "
                           f"Provider={result['provider_name']}, "
                           f"Patients={result['patients_processed']}, "
                           f"Database={result['database_name']}")
                
                provider_db_manager.log_system_event('INFO', 'FileProcessor', 
                                                   f'Successfully processed {json_file.name}',
                                                   result['provider_name'],
                                                   {
                                                       'patients_processed': result['patients_processed'],
                                                       'session_id': result['session_id'],
                                                       'file_path': str(json_file)
                                                   })
                
                # Check for conflicts and notify if any found
                if result.get('processing_results'):
                    conflicts = [r for r in result['processing_results'] if r.get('conflict_detected')]
                    if conflicts:
                        self._handle_conflicts_detected(conflicts, result['provider_name'], json_file)
            
            else:
                # Processing failed
                self.stats['processing_errors'] += 1
                error_msg = f"Failed to process {json_file}: {result.get('error', 'Unknown error')}"
                logger.error(error_msg)
                
                provider_db_manager.log_system_event('ERROR', 'FileProcessor', error_msg, 
                                                   None, {'file_path': str(json_file)})
        
        except Exception as e:
            self.stats['processing_errors'] += 1
            error_msg = f"Exception processing {json_file}: {str(e)}"
            logger.error(error_msg)
            
            provider_db_manager.log_system_event('ERROR', 'FileProcessor', error_msg,
                                               None, {'file_path': str(json_file), 'exception': type(e).__name__})
    
    def _handle_conflicts_detected(self, conflicts: list, provider_name: str, json_file: Path):
        """Handle detected data conflicts by logging and potentially alerting"""
        conflict_count = len(conflicts)
        logger.warning(f"Data conflicts detected in {json_file}: {conflict_count} conflicts")
        
        # Log detailed conflict information
        for conflict in conflicts:
            if conflict.get('conflict_detected'):
                provider_db_manager.log_system_event('WARNING', 'ConflictAlert',
                                                   f"Data conflict detected for patient {conflict.get('prn')}",
                                                   provider_name,
                                                   {
                                                       'conflict_id': conflict.get('conflict_id'),
                                                       'file_source': str(json_file),
                                                       'extraction_id': conflict.get('extraction_id')
                                                   })
        
        # Here you could add email alerts, Slack notifications, etc.
        # For now, just comprehensive logging
    
    def _get_file_signature(self, file_path: Path) -> str:
        """Get unique signature for a file (path + modification time + size)"""
        try:
            stat = file_path.stat()
            signature_data = f"{file_path}:{stat.st_mtime}:{stat.st_size}"
            return hashlib.md5(signature_data.encode()).hexdigest()
        except Exception as e:
            logger.error(f"Error getting file signature for {file_path}: {e}")
            return str(file_path)
    
    def _load_processed_files_cache(self):
        """Load previously processed files from cache"""
        cache_file = Path(self.processed_files_cache_file)
        if cache_file.exists():
            try:
                with open(cache_file, 'r') as f:
                    data = json.load(f)
                    self.processed_files = set(data.get('processed_files', []))
                    logger.info(f"Loaded {len(self.processed_files)} processed files from cache")
            except Exception as e:
                logger.error(f"Error loading processed files cache: {e}")
                self.processed_files = set()
        else:
            self.processed_files = set()
    
    def _save_processed_files_cache(self):
        """Save processed files to cache"""
        try:
            cache_data = {
                'processed_files': list(self.processed_files),
                'last_updated': datetime.now().isoformat(),
                'stats': {
                    'total_files_processed': len(self.processed_files),
                    'monitoring_started': self.stats['monitoring_started'].isoformat() if self.stats['monitoring_started'] else None
                }
            }
            
            with open(self.processed_files_cache_file, 'w') as f:
                json.dump(cache_data, f, indent=2)
                
            logger.debug(f"Saved {len(self.processed_files)} processed files to cache")
        
        except Exception as e:
            logger.error(f"Error saving processed files cache: {e}")
    
    def force_reprocess_file(self, file_path: str):
        """Force reprocessing of a specific file (removes from processed cache)"""
        file_path = Path(file_path)
        file_signature = self._get_file_signature(file_path)
        
        if file_signature in self.processed_files:
            self.processed_files.remove(file_signature)
            logger.info(f"Removed {file_path} from processed cache - will be reprocessed on next scan")
        else:
            logger.info(f"File {file_path} was not in processed cache")
    
    def process_existing_files(self):
        """Process all existing JSON files in the Results directory (one-time operation)"""
        logger.info("Starting one-time processing of all existing JSON files...")
        
        json_files = self._find_json_files()
        
        if not json_files:
            logger.info("No JSON files found in Results directory")
            return
        
        logger.info(f"Found {len(json_files)} JSON files to process")
        
        for json_file in json_files:
            self._process_single_file(json_file)
        
        self._save_processed_files_cache()
        
        logger.info(f"Completed processing {len(json_files)} files. "
                   f"Processed: {self.stats['files_processed']}, "
                   f"Errors: {self.stats['processing_errors']}")
    
    def get_monitoring_status(self) -> Dict[str, Any]:
        """Get current monitoring status and statistics"""
        providers_discovered = list(self.stats['providers_discovered'])
        
        return {
            'monitoring_active': self.monitoring,
            'results_directory': str(self.results_directory),
            'processed_files_count': len(self.processed_files),
            'statistics': {
                'monitoring_started': self.stats['monitoring_started'].isoformat() if self.stats['monitoring_started'] else None,
                'files_detected': self.stats['files_detected'],
                'files_processed': self.stats['files_processed'],
                'processing_errors': self.stats['processing_errors'],
                'providers_discovered': providers_discovered,
                'providers_count': len(providers_discovered),
                'last_activity': self.stats['last_activity'].isoformat() if self.stats['last_activity'] else None
            }
        }
    
    def get_provider_summary(self) -> Dict[str, Any]:
        """Get summary of all discovered providers"""
        provider_stats = provider_processor.get_provider_statistics()
        monitoring_status = self.get_monitoring_status()
        
        return {
            'monitoring_status': monitoring_status,
            'provider_database_statistics': provider_stats,
            'system_overview': {
                'total_providers_discovered': len(self.stats['providers_discovered']),
                'provider_list': list(self.stats['providers_discovered']),
                'databases_created': [f"webautodash_{provider_db_manager.sanitize_provider_name(p)}" 
                                    for p in self.stats['providers_discovered']]
            }
        }

# Global instance
file_monitor = JSONFileMonitor()

def start_monitoring(check_interval: int = 10):
    """Start file monitoring (legacy compatibility)"""
    file_monitor.start_monitoring(check_interval)

def stop_monitoring():
    """Stop file monitoring (legacy compatibility)"""
    file_monitor.stop_monitoring()

def process_all_existing_files():
    """Process all existing files once (legacy compatibility)"""
    file_monitor.process_existing_files()

def get_monitoring_status():
    """Get monitoring status (legacy compatibility)"""
    return file_monitor.get_monitoring_status()

if __name__ == "__main__":
    # Command line interface for testing
    import sys
    
    if len(sys.argv) > 1:
        command = sys.argv[1]
        
        if command == "monitor":
            print("Starting file monitoring...")
            file_monitor.start_monitoring()
            try:
                while True:
                    time.sleep(60)
                    status = file_monitor.get_monitoring_status()
                    print(f"Status: {status['statistics']}")
            except KeyboardInterrupt:
                print("\nStopping monitor...")
                file_monitor.stop_monitoring()
        
        elif command == "process":
            print("Processing all existing files...")
            file_monitor.process_existing_files()
            print("Processing complete!")
        
        elif command == "status":
            status = file_monitor.get_provider_summary()
            print(json.dumps(status, indent=2, default=str))
        
        else:
            print("Usage: python json_file_monitor.py [monitor|process|status]")
    
    else:
        print("JSON File Monitor for WebAutoDash")
        print("Usage: python json_file_monitor.py [monitor|process|status]")
        print("  monitor - Start continuous monitoring")
        print("  process - Process all existing files once")
        print("  status  - Show current status") 