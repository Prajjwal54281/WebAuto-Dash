#!/usr/bin/env python3
"""
WebAutoDash MySQL Provider Database Setup Script
Initializes the provider-based database system with complete separation
"""

import sys
import os
import json
import logging
from datetime import datetime
from pathlib import Path

# Add current directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from db_connection_provider import provider_db_manager, ProviderDatabaseManager
from data_processor_provider import provider_processor
from json_file_monitor import file_monitor

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('setup_mysql.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

class MySQLSetupManager:
    """Manages the complete setup process for provider-based MySQL system"""
    
    def __init__(self):
        self.setup_results = {
            'started_at': datetime.now(),
            'steps_completed': [],
            'errors': [],
            'providers_discovered': [],
            'databases_created': [],
            'warnings': []
        }
    
    def run_complete_setup(self):
        """Run the complete setup process"""
        logger.info("="*80)
        logger.info("WebAutoDash MySQL Provider Database Setup")
        logger.info("="*80)
        
        try:
            # Step 1: Test MySQL Connection
            self._test_mysql_connection()
            
            # Step 2: Initialize System Database
            self._initialize_system_database()
            
            # Step 3: Discover Existing Providers
            self._discover_existing_providers()
            
            # Step 4: Process Existing JSON Files
            self._process_existing_files()
            
            # Step 5: Setup File Monitoring
            self._setup_file_monitoring()
            
            # Step 6: Generate Setup Report
            self._generate_setup_report()
            
            logger.info("✅ Setup completed successfully!")
            return True
            
        except Exception as e:
            logger.error(f"❌ Setup failed: {str(e)}")
            self.setup_results['errors'].append(str(e))
            return False
    
    def _test_mysql_connection(self):
        """Test MySQL connection with provided credentials"""
        logger.info("Step 1: Testing MySQL Connection...")
        
        try:
            # Test system connection
            conn = provider_db_manager._get_system_connection()
            if conn.is_connected():
                cursor = conn.cursor()
                cursor.execute("SELECT VERSION()")
                version = cursor.fetchone()[0]
                logger.info(f"✅ MySQL connection successful! Version: {version}")
                logger.info(f"   Host: {provider_db_manager.mysql_config['host']}")
                logger.info(f"   Port: {provider_db_manager.mysql_config['port']}")
                logger.info(f"   User: {provider_db_manager.mysql_config['user']}")
                
                self.setup_results['steps_completed'].append('mysql_connection_test')
                cursor.close()
                conn.close()
            else:
                raise Exception("Failed to connect to MySQL")
                
        except Exception as e:
            error_msg = f"MySQL connection failed: {str(e)}"
            logger.error(f"❌ {error_msg}")
            self.setup_results['errors'].append(error_msg)
            raise
    
    def _initialize_system_database(self):
        """Initialize the system database and tables"""
        logger.info("Step 2: Initializing System Database...")
        
        try:
            # System database is automatically created during ProviderDatabaseManager init
            logger.info(f"✅ System database '{provider_db_manager.system_database}' initialized")
            
            # Test system database functionality
            providers = provider_db_manager.list_providers()
            logger.info(f"   Found {len(providers)} existing providers in system")
            
            self.setup_results['steps_completed'].append('system_database_init')
            
        except Exception as e:
            error_msg = f"System database initialization failed: {str(e)}"
            logger.error(f"❌ {error_msg}")
            self.setup_results['errors'].append(error_msg)
            raise
    
    def _discover_existing_providers(self):
        """Discover existing providers from Results directory structure"""
        logger.info("Step 3: Discovering Existing Providers...")
        
        results_dir = Path("../Results")  # Relative to backend directory
        if not results_dir.exists():
            results_dir = Path("Results")  # Alternative path
        
        if not results_dir.exists():
            warning_msg = "Results directory not found - no existing providers to discover"
            logger.warning(f"⚠️  {warning_msg}")
            self.setup_results['warnings'].append(warning_msg)
            self.setup_results['steps_completed'].append('provider_discovery')
            return
        
        try:
            discovered_providers = []
            
            # Look for provider directories
            for provider_dir in results_dir.iterdir():
                if provider_dir.is_dir() and not provider_dir.name.startswith('.'):
                    provider_name = provider_dir.name
                    
                    # Count JSON files in this provider directory
                    json_files = list(provider_dir.glob("*.json"))
                    
                    if json_files:
                        logger.info(f"   📁 Found provider: {provider_name} ({len(json_files)} JSON files)")
                        discovered_providers.append({
                            'name': provider_name,
                            'directory': str(provider_dir),
                            'json_files': len(json_files)
                        })
                        
                        # Register provider (creates database if needed)
                        provider_info = provider_db_manager.register_provider(provider_name)
                        self.setup_results['databases_created'].append(provider_info['database_name'])
                        logger.info(f"     🗄️  Database created: {provider_info['database_name']}")
            
            self.setup_results['providers_discovered'] = discovered_providers
            logger.info(f"✅ Discovered {len(discovered_providers)} providers")
            self.setup_results['steps_completed'].append('provider_discovery')
            
        except Exception as e:
            error_msg = f"Provider discovery failed: {str(e)}"
            logger.error(f"❌ {error_msg}")
            self.setup_results['errors'].append(error_msg)
            raise
    
    def _process_existing_files(self):
        """Process all existing JSON files"""
        logger.info("Step 4: Processing Existing JSON Files...")
        
        try:
            # Change to parent directory to access Results folder correctly
            original_cwd = os.getcwd()
            parent_dir = Path("..").resolve()
            
            if (parent_dir / "Results").exists():
                os.chdir(parent_dir)
                logger.info(f"   Changed working directory to: {os.getcwd()}")
            
            # Set up file monitor with correct Results directory
            results_dir = "Results" if Path("Results").exists() else "../Results"
            file_monitor.results_directory = Path(results_dir)
            
            # Process all existing files
            logger.info("   Processing all existing JSON files...")
            file_monitor.process_existing_files()
            
            # Get processing statistics
            status = file_monitor.get_monitoring_status()
            logger.info(f"✅ File processing completed:")
            logger.info(f"   📄 Files processed: {status['statistics']['files_processed']}")
            logger.info(f"   ❌ Processing errors: {status['statistics']['processing_errors']}")
            logger.info(f"   👥 Providers discovered: {status['statistics']['providers_count']}")
            
            # Change back to original directory
            os.chdir(original_cwd)
            
            self.setup_results['steps_completed'].append('existing_files_processed')
            
        except Exception as e:
            error_msg = f"Existing file processing failed: {str(e)}"
            logger.error(f"❌ {error_msg}")
            self.setup_results['errors'].append(error_msg)
            # Don't raise - this is not critical for setup
    
    def _setup_file_monitoring(self):
        """Setup automatic file monitoring"""
        logger.info("Step 5: Setting Up File Monitoring...")
        
        try:
            # Note: We don't start monitoring automatically during setup
            # User will need to start it manually or through the application
            
            logger.info("✅ File monitoring system is ready")
            logger.info("   To start monitoring: python json_file_monitor.py monitor")
            logger.info("   To check status: python json_file_monitor.py status")
            
            self.setup_results['steps_completed'].append('file_monitoring_setup')
            
        except Exception as e:
            error_msg = f"File monitoring setup failed: {str(e)}"
            logger.error(f"❌ {error_msg}")
            self.setup_results['errors'].append(error_msg)
            # Don't raise - this is not critical for setup
    
    def _generate_setup_report(self):
        """Generate comprehensive setup report"""
        logger.info("Step 6: Generating Setup Report...")
        
        try:
            # Get comprehensive statistics
            provider_stats = provider_processor.get_provider_statistics()
            system_providers = provider_db_manager.list_providers()
            
            # Create detailed report
            report = {
                'setup_summary': {
                    'completed_at': datetime.now().isoformat(),
                    'duration': str(datetime.now() - self.setup_results['started_at']),
                    'success': len(self.setup_results['errors']) == 0,
                    'steps_completed': self.setup_results['steps_completed'],
                    'errors': self.setup_results['errors'],
                    'warnings': self.setup_results['warnings']
                },
                'database_configuration': {
                    'mysql_host': provider_db_manager.mysql_config['host'],
                    'mysql_port': provider_db_manager.mysql_config['port'],
                    'mysql_user': provider_db_manager.mysql_config['user'],
                    'system_database': provider_db_manager.system_database,
                    'database_prefix': provider_db_manager.database_prefix
                },
                'providers_setup': {
                    'total_providers': len(system_providers),
                    'databases_created': self.setup_results['databases_created'],
                    'provider_details': system_providers
                },
                'statistics': provider_stats,
                'next_steps': [
                    "Start file monitoring: python json_file_monitor.py monitor",
                    "Check provider statistics: python json_file_monitor.py status",
                    "Process new files: They will be automatically detected and processed",
                    "Review conflicts: Check data_conflicts table in each provider database"
                ]
            }
            
            # Save report to file
            report_file = f"setup_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(report_file, 'w') as f:
                json.dump(report, f, indent=2, default=str)
            
            logger.info(f"✅ Setup report saved to: {report_file}")
            
            # Print summary
            logger.info("\n" + "="*80)
            logger.info("📊 SETUP SUMMARY")
            logger.info("="*80)
            logger.info(f"✅ Success: {report['setup_summary']['success']}")
            logger.info(f"⏱️  Duration: {report['setup_summary']['duration']}")
            logger.info(f"🗄️  Databases Created: {len(self.setup_results['databases_created'])}")
            logger.info(f"👥 Providers Setup: {len(system_providers)}")
            
            if self.setup_results['errors']:
                logger.info(f"❌ Errors: {len(self.setup_results['errors'])}")
                for error in self.setup_results['errors']:
                    logger.error(f"   • {error}")
            
            if self.setup_results['warnings']:
                logger.info(f"⚠️  Warnings: {len(self.setup_results['warnings'])}")
                for warning in self.setup_results['warnings']:
                    logger.warning(f"   • {warning}")
            
            logger.info("\n🎯 NEXT STEPS:")
            for step in report['next_steps']:
                logger.info(f"   • {step}")
            
            logger.info("="*80)
            
            self.setup_results['steps_completed'].append('setup_report_generated')
            
        except Exception as e:
            error_msg = f"Setup report generation failed: {str(e)}"
            logger.error(f"❌ {error_msg}")
            self.setup_results['errors'].append(error_msg)
            # Don't raise - this is not critical

def main():
    """Main setup function"""
    print("WebAutoDash MySQL Provider Database Setup")
    print("="*50)
    
    # Check if setup should be interactive
    if len(sys.argv) > 1 and sys.argv[1] == "--auto":
        print("Running automatic setup...")
        interactive = False
    else:
        # Ask for confirmation
        response = input("\nThis will set up provider-separated MySQL databases for WebAutoDash.\n"
                        "Continue? (y/N): ").lower().strip()
        
        if response != 'y':
            print("Setup cancelled.")
            return False
        
        interactive = True
    
    # Run setup
    setup_manager = MySQLSetupManager()
    success = setup_manager.run_complete_setup()
    
    if success:
        print("\n🎉 Setup completed successfully!")
        
        if interactive:
            print("\nWould you like to start file monitoring now? (y/N): ", end="")
            if input().lower().strip() == 'y':
                print("Starting file monitoring...")
                file_monitor.start_monitoring()
                print("File monitoring started! Press Ctrl+C to stop.")
                try:
                    while True:
                        import time
                        time.sleep(60)
                        status = file_monitor.get_monitoring_status()
                        print(f"📊 Monitoring status: {status['statistics']}")
                except KeyboardInterrupt:
                    print("\nStopping file monitoring...")
                    file_monitor.stop_monitoring()
                    print("File monitoring stopped.")
        
        return True
    else:
        print("\n❌ Setup failed. Check the logs for details.")
        return False

if __name__ == "__main__":
    main() 