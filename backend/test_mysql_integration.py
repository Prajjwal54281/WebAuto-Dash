#!/usr/bin/env python3
"""
Test MySQL Provider Integration for WebAutoDash
Comprehensive testing of the provider-based database system
"""

import os
import sys
import json
import tempfile
import logging
from datetime import datetime, date
from pathlib import Path

# Add current directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from db_connection_provider import provider_db_manager, calculate_data_checksum
from data_processor_provider import provider_processor
from json_file_monitor import file_monitor

# Setup test logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MySQLIntegrationTester:
    """Comprehensive testing of MySQL provider integration"""
    
    def __init__(self):
        self.test_results = []
        self.test_data = self._create_test_data()
    
    def run_all_tests(self):
        """Run all integration tests"""
        logger.info("="*80)
        logger.info("WebAutoDash MySQL Integration Tests")
        logger.info("="*80)
        
        tests = [
            self.test_mysql_connection,
            self.test_provider_registration,
            self.test_database_creation,
            self.test_patient_creation,
            self.test_extraction_processing,
            self.test_duplicate_detection,
            self.test_conflict_detection,
            self.test_data_checksum,
            self.test_file_processing,
            self.test_provider_separation
        ]
        
        passed = 0
        failed = 0
        
        for test in tests:
            try:
                logger.info(f"\n🧪 Running: {test.__name__}")
                result = test()
                if result:
                    logger.info(f"✅ PASSED: {test.__name__}")
                    passed += 1
                else:
                    logger.error(f"❌ FAILED: {test.__name__}")
                    failed += 1
                self.test_results.append({'test': test.__name__, 'passed': result})
            except Exception as e:
                logger.error(f"💥 ERROR in {test.__name__}: {str(e)}")
                self.test_results.append({'test': test.__name__, 'passed': False, 'error': str(e)})
                failed += 1
        
        # Print summary
        logger.info("\n" + "="*80)
        logger.info("TEST SUMMARY")
        logger.info("="*80)
        logger.info(f"✅ Passed: {passed}")
        logger.info(f"❌ Failed: {failed}")
        logger.info(f"📊 Total: {passed + failed}")
        logger.info(f"🎯 Success Rate: {(passed/(passed+failed)*100):.1f}%")
        
        return passed, failed
    
    def test_mysql_connection(self):
        """Test basic MySQL connectivity"""
        try:
            conn = provider_db_manager._get_system_connection()
            if conn.is_connected():
                cursor = conn.cursor()
                cursor.execute("SELECT 1")
                result = cursor.fetchone()
                cursor.close()
                conn.close()
                return result[0] == 1
            return False
        except Exception as e:
            logger.error(f"MySQL connection test failed: {e}")
            return False
    
    def test_provider_registration(self):
        """Test provider registration and database name generation"""
        try:
            test_providers = [
                "Dr. Gary Wang",
                "John Doe MD",
                "Test Provider",
                "Provider-With-Special/Chars!"
            ]
            
            for provider in test_providers:
                provider_info = provider_db_manager.register_provider(provider)
                
                # Verify registration response
                if not all(key in provider_info for key in ['provider_name', 'sanitized_name', 'database_name']):
                    logger.error(f"Invalid provider registration response for {provider}")
                    return False
                
                # Verify database name format
                expected_db = f"webautodash_{provider_db_manager.sanitize_provider_name(provider)}"
                if provider_info['database_name'] != expected_db:
                    logger.error(f"Database name mismatch for {provider}: {provider_info['database_name']} != {expected_db}")
                    return False
                
                logger.info(f"   Provider '{provider}' -> Database '{provider_info['database_name']}'")
            
            return True
        except Exception as e:
            logger.error(f"Provider registration test failed: {e}")
            return False
    
    def test_database_creation(self):
        """Test database and table creation"""
        try:
            test_provider = "Test Provider Database"
            provider_info = provider_db_manager.register_provider(test_provider)
            
            # Get connection to provider database
            conn = provider_db_manager.get_provider_connection(test_provider)
            cursor = conn.cursor()
            
            # Test that all required tables exist
            required_tables = [
                'patients', 'extraction_sessions', 'patient_extractions',
                'medications', 'diagnoses', 'allergies', 'health_concerns', 'data_conflicts'
            ]
            
            cursor.execute("SHOW TABLES")
            existing_tables = [table[0] for table in cursor.fetchall()]
            
            for table in required_tables:
                if table not in existing_tables:
                    logger.error(f"Required table '{table}' not found in {provider_info['database_name']}")
                    return False
            
            logger.info(f"   All {len(required_tables)} required tables found")
            
            cursor.close()
            conn.close()
            return True
            
        except Exception as e:
            logger.error(f"Database creation test failed: {e}")
            return False
    
    def test_patient_creation(self):
        """Test patient record creation"""
        try:
            test_provider = "Test Provider Patients"
            patient_data = self.test_data['sample_patient']
            
            # Process patient
            result = provider_processor._get_or_create_patient(patient_data, test_provider)
            
            if not isinstance(result, int) or result <= 0:
                logger.error(f"Invalid patient ID returned: {result}")
                return False
            
            # Verify patient was created
            conn = provider_db_manager.get_provider_connection(test_provider)
            cursor = conn.cursor(dictionary=True)
            
            prn = patient_data['demographics_printable']['prn']
            cursor.execute("SELECT * FROM patients WHERE prn = %s", (prn,))
            patient_record = cursor.fetchone()
            
            if not patient_record:
                logger.error(f"Patient with PRN {prn} not found in database")
                return False
            
            # Verify patient data
            if patient_record['patient_name'] != patient_data['demographics_printable']['patient_name']:
                logger.error("Patient name mismatch")
                return False
            
            logger.info(f"   Patient created with ID: {result}, PRN: {prn}")
            
            cursor.close()
            conn.close()
            return True
            
        except Exception as e:
            logger.error(f"Patient creation test failed: {e}")
            return False
    
    def test_extraction_processing(self):
        """Test complete extraction processing"""
        try:
            # Create test JSON file
            test_data = self.test_data['sample_extraction']
            
            with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
                json.dump(test_data, f, indent=2)
                test_file_path = f.name
            
            try:
                # Process the file
                result = provider_processor.process_json_file(test_file_path)
                
                if not result['success']:
                    logger.error(f"Extraction processing failed: {result.get('error')}")
                    return False
                
                # Verify results
                if result['patients_processed'] != len(test_data['extraction_results']):
                    logger.error(f"Patient count mismatch: {result['patients_processed']} != {len(test_data['extraction_results'])}")
                    return False
                
                logger.info(f"   Processed {result['patients_processed']} patients for provider {result['provider_name']}")
                
                return True
                
            finally:
                # Clean up test file
                os.unlink(test_file_path)
        
        except Exception as e:
            logger.error(f"Extraction processing test failed: {e}")
            return False
    
    def test_duplicate_detection(self):
        """Test duplicate extraction detection"""
        try:
            test_provider = "Test Provider Duplicates"
            patient_data = self.test_data['sample_patient']
            
            # Create extraction session
            metadata = self.test_data['sample_extraction']['extraction_metadata']
            session_id = provider_processor._create_extraction_session(
                metadata, "test_duplicate.json", test_provider
            )
            
            # Create first extraction
            patient_id = provider_processor._get_or_create_patient(patient_data, test_provider)
            extraction_id1 = provider_processor._create_patient_extraction(
                patient_id, session_id, patient_data, metadata, test_provider
            )
            
            # Create second session with same metadata
            session_id2 = provider_processor._create_extraction_session(
                metadata, "test_duplicate2.json", test_provider
            )
            
            # Check for existing extraction (should find the first one)
            prn = patient_data['demographics_printable']['prn']
            existing = provider_processor._check_existing_extraction(
                prn, session_id2, metadata, patient_data, test_provider
            )
            
            if not existing:
                logger.error("Failed to detect existing extraction")
                return False
            
            if existing['id'] != extraction_id1:
                logger.error(f"Wrong existing extraction detected: {existing['id']} != {extraction_id1}")
                return False
            
            logger.info(f"   Successfully detected duplicate extraction")
            
            return True
            
        except Exception as e:
            logger.error(f"Duplicate detection test failed: {e}")
            return False
    
    def test_conflict_detection(self):
        """Test data conflict detection"""
        try:
            # Create two versions of patient data with different information
            patient_data1 = self.test_data['sample_patient'].copy()
            patient_data2 = self.test_data['sample_patient'].copy()
            
            # Modify second version to create conflict
            patient_data2['demographics_printable']['patient_name'] = "Different Name"
            patient_data2['all_medications'].append({
                'medication_name': 'New Medication',
                'medication_type': 'active'
            })
            
            # Calculate checksums
            checksum1 = calculate_data_checksum(patient_data1)
            checksum2 = calculate_data_checksum(patient_data2)
            
            if checksum1 == checksum2:
                logger.error("Checksums should be different for modified data")
                return False
            
            logger.info(f"   Conflict detection working: different checksums generated")
            
            return True
            
        except Exception as e:
            logger.error(f"Conflict detection test failed: {e}")
            return False
    
    def test_data_checksum(self):
        """Test data checksum calculation"""
        try:
            patient_data = self.test_data['sample_patient']
            
            # Calculate checksum multiple times - should be consistent
            checksum1 = calculate_data_checksum(patient_data)
            checksum2 = calculate_data_checksum(patient_data)
            
            if checksum1 != checksum2:
                logger.error("Checksum calculation is not consistent")
                return False
            
            # Modify data slightly
            modified_data = patient_data.copy()
            modified_data['patient_name'] = "Modified Name"
            
            checksum3 = calculate_data_checksum(modified_data)
            
            if checksum1 == checksum3:
                logger.error("Checksum should change when data is modified")
                return False
            
            logger.info(f"   Checksum calculation is consistent and sensitive to changes")
            
            return True
            
        except Exception as e:
            logger.error(f"Data checksum test failed: {e}")
            return False
    
    def test_file_processing(self):
        """Test JSON file processing through monitor"""
        try:
            # Create temporary results directory structure
            with tempfile.TemporaryDirectory() as temp_dir:
                results_dir = Path(temp_dir) / "Results"
                provider_dir = results_dir / "test_provider"
                provider_dir.mkdir(parents=True)
                
                # Create test JSON file
                test_file = provider_dir / "test_extraction.json"
                with open(test_file, 'w') as f:
                    json.dump(self.test_data['sample_extraction'], f, indent=2)
                
                # Set up file monitor with test directory
                original_dir = file_monitor.results_directory
                file_monitor.results_directory = results_dir
                
                try:
                    # Process files
                    file_monitor.process_existing_files()
                    
                    # Check processing results
                    status = file_monitor.get_monitoring_status()
                    
                    if status['statistics']['files_processed'] < 1:
                        logger.error("No files were processed")
                        return False
                    
                    logger.info(f"   Successfully processed files through monitor")
                    
                    return True
                    
                finally:
                    # Restore original directory
                    file_monitor.results_directory = original_dir
        
        except Exception as e:
            logger.error(f"File processing test failed: {e}")
            return False
    
    def test_provider_separation(self):
        """Test that provider data is properly separated"""
        try:
            # Create data for two different providers
            provider1 = "Provider One"
            provider2 = "Provider Two"
            
            patient_data1 = self.test_data['sample_patient'].copy()
            patient_data1['demographics_printable']['prn'] = 'TEST001'
            patient_data1['demographics_printable']['patient_name'] = 'Patient One'
            
            patient_data2 = self.test_data['sample_patient'].copy()
            patient_data2['demographics_printable']['prn'] = 'TEST002'
            patient_data2['demographics_printable']['patient_name'] = 'Patient Two'
            
            # Create patients in different provider databases
            patient_id1 = provider_processor._get_or_create_patient(patient_data1, provider1)
            patient_id2 = provider_processor._get_or_create_patient(patient_data2, provider2)
            
            # Verify patients are in separate databases
            conn1 = provider_db_manager.get_provider_connection(provider1)
            cursor1 = conn1.cursor()
            cursor1.execute("SELECT COUNT(*) FROM patients")
            count1 = cursor1.fetchone()[0]
            cursor1.close()
            conn1.close()
            
            conn2 = provider_db_manager.get_provider_connection(provider2)
            cursor2 = conn2.cursor()
            cursor2.execute("SELECT COUNT(*) FROM patients")
            count2 = cursor2.fetchone()[0]
            cursor2.close()
            conn2.close()
            
            # Each provider should have at least their test patient
            if count1 < 1 or count2 < 1:
                logger.error(f"Provider separation failed: Provider1 has {count1} patients, Provider2 has {count2} patients")
                return False
            
            # Verify patients are not visible across providers
            conn1 = provider_db_manager.get_provider_connection(provider1)
            cursor1 = conn1.cursor()
            cursor1.execute("SELECT prn FROM patients WHERE prn = 'TEST002'")
            cross_patient = cursor1.fetchone()
            cursor1.close()
            conn1.close()
            
            if cross_patient:
                logger.error("Patient data leaked between providers")
                return False
            
            logger.info(f"   Provider separation verified: Provider1={count1} patients, Provider2={count2} patients")
            
            return True
            
        except Exception as e:
            logger.error(f"Provider separation test failed: {e}")
            return False
    
    def _create_test_data(self):
        """Create sample test data for testing"""
        return {
            'sample_patient': {
                'patient_id': 'test-uuid-12345',
                'patient_name': 'Test Patient',
                'demographics_printable': {
                    'prn': 'TEST123',
                    'patient_name': 'Test Patient',
                    'date_of_birth': '1965-03-15',
                    'age': '58 yrs',
                    'gender': 'Male'
                },
                'filter_medication_name': 'Test Medication',
                'filter_start_date': '2023-01-01',
                'filter_stop_date': '2023-12-31',
                'all_medications': [
                    {
                        'medication_name': 'Test Medication 10mg',
                        'medication_type': 'active',
                        'sig': 'Take once daily'
                    }
                ],
                'all_diagnoses': [
                    {
                        'diagnosis_text': 'Test Condition (M10.079)',
                        'diagnosis_type': 'current'
                    }
                ],
                'all_allergies': ['Test Allergy'],
                'all_health_concerns': ['Test Health Concern']
            },
            'sample_extraction': {
                'extraction_metadata': {
                    'job_id': 12345,
                    'job_name': 'Test Extraction Job',
                    'portal_name': 'Test Portal',
                    'extraction_mode': 'ALL_PATIENTS',
                    'medication': 'Test Medication',
                    'start_date': '2023-01-01',
                    'end_date': '2023-12-31',
                    'provider_name': 'Test Provider',
                    'extracted_at': datetime.now().isoformat()
                },
                'extraction_results': [
                    # Will be filled with sample_patient data
                ]
            }
        }

def main():
    """Run all tests"""
    if len(sys.argv) > 1 and sys.argv[1] == "--quick":
        print("Running quick tests only...")
        tester = MySQLIntegrationTester()
        # Just run basic connectivity tests
        tests = [
            tester.test_mysql_connection,
            tester.test_provider_registration,
            tester.test_data_checksum
        ]
        passed = 0
        failed = 0
        for test in tests:
            try:
                if test():
                    passed += 1
                else:
                    failed += 1
            except:
                failed += 1
        
        print(f"Quick test results: {passed} passed, {failed} failed")
        return passed > 0 and failed == 0
    
    else:
        print("Running comprehensive MySQL integration tests...")
        tester = MySQLIntegrationTester()
        passed, failed = tester.run_all_tests()
        return failed == 0

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 