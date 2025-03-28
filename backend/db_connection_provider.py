"""
WebAutoDash Provider-Based Database Connection System
Creates separate databases for each provider to ensure data isolation
"""

import os
import re
import mysql.connector
from mysql.connector import Error
from dotenv import load_dotenv
import hashlib
import json
import logging
from datetime import datetime
from typing import Optional, Dict, Any, List

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"), override=True)

class ProviderDatabaseManager:
    """
    Manages provider-specific databases with complete data isolation
    Each provider gets their own database: webautodash_gary_wang, webautodash_john_doe, etc.
    """
    
    def __init__(self):
        # Use the same pattern as x_voice project
        def _make_config(prefix: str):
            return {
                "host":     os.getenv(f"{prefix}_HOST", "localhost"),
                "port":     int(os.getenv(f"{prefix}_PORT", "3306")),
                "user":     os.getenv(f"{prefix}_USER", ""),
                "password": os.getenv(f"{prefix}_PASSWORD", ""),
                "charset": "utf8mb4",
                "autocommit": False,
                "connection_timeout": 30
            }
        
        self.mysql_config = _make_config("WEBAUTODASH_DB")
        
        self.database_prefix = os.getenv("DATABASE_PREFIX", "webautodash_")
        self.system_database = os.getenv("DEFAULT_DATABASE", "webautodash_system")
        
        # Cache for database connections
        self.connections = {}
        
        # Initialize system database
        self._initialize_system_database()
    
    def sanitize_provider_name(self, provider_name: str) -> str:
        """
        Sanitize provider name for use as database name
        
        Args:
            provider_name: Raw provider name (e.g., "Dr. Gary Wang")
            
        Returns:
            Sanitized name safe for database use (e.g., "gary_wang")
        """
        if not provider_name:
            return "unknown_provider"
        
        # Convert to lowercase and replace spaces/special chars with underscores
        sanitized = re.sub(r'[^\w\s-]', '', provider_name.lower())
        sanitized = re.sub(r'[\s-]+', '_', sanitized)
        
        # Remove leading/trailing underscores and limit length
        sanitized = sanitized.strip('_')[:50]
        
        return sanitized if sanitized else "unknown_provider"
    
    def get_provider_database_name(self, provider_name: str) -> str:
        """
        Get the database name for a specific provider
        
        Args:
            provider_name: Provider name
            
        Returns:
            Database name (e.g., "webautodash_gary_wang")
        """
        sanitized_name = self.sanitize_provider_name(provider_name)
        return f"{self.database_prefix}{sanitized_name}"
    
    def _get_system_connection(self) -> mysql.connector.MySQLConnection:
        """Get connection to MySQL server (without specific database)"""
        try:
            config = self.mysql_config.copy()
            # Remove database to connect to MySQL server
            config.pop('database', None)
            
            conn = mysql.connector.connect(**config)
            if conn.is_connected():
                logger.info(f"Connected to MySQL server @ {config['host']}:{config['port']}")
                return conn
            else:
                raise Error("Connection failed")
        except Error as err:
            logger.error(f"MySQL server connection error: {err}")
            raise
    
    def _initialize_system_database(self):
        """Initialize the system database for tracking providers"""
        try:
            conn = self._get_system_connection()
            cursor = conn.cursor()
            
            # Create system database
            cursor.execute(f"CREATE DATABASE IF NOT EXISTS {self.system_database} CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
            cursor.execute(f"USE {self.system_database}")
            
            # Create providers tracking table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS providers (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    provider_name VARCHAR(255) NOT NULL,
                    sanitized_name VARCHAR(100) NOT NULL UNIQUE,
                    database_name VARCHAR(150) NOT NULL UNIQUE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_extraction TIMESTAMP NULL,
                    total_extractions INT DEFAULT 0,
                    total_patients INT DEFAULT 0,
                    status ENUM('active', 'inactive') DEFAULT 'active',
                    INDEX idx_provider_name (provider_name),
                    INDEX idx_sanitized_name (sanitized_name)
                ) ENGINE=InnoDB COMMENT='Tracks all providers and their databases'
            """)
            
            # Create system logs table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS system_logs (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    log_level ENUM('DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL') NOT NULL,
                    component VARCHAR(100) NOT NULL,
                    message TEXT NOT NULL,
                    provider_name VARCHAR(255) NULL,
                    database_name VARCHAR(150) NULL,
                    details JSON NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    INDEX idx_log_level (log_level),
                    INDEX idx_component (component),
                    INDEX idx_provider_name (provider_name),
                    INDEX idx_created_at (created_at)
                ) ENGINE=InnoDB COMMENT='System-wide logs and monitoring'
            """)
            
            conn.commit()
            logger.info(f"System database '{self.system_database}' initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize system database: {e}")
            raise
        finally:
            if 'conn' in locals() and conn.is_connected():
                cursor.close()
                conn.close()
    
    def register_provider(self, provider_name: str) -> Dict[str, str]:
        """
        Register a new provider and create their database
        
        Args:
            provider_name: Provider name from JSON data
            
        Returns:
            Provider information including database name
        """
        sanitized_name = self.sanitize_provider_name(provider_name)
        database_name = self.get_provider_database_name(provider_name)
        
        try:
            # Connect to system database
            conn = self._get_system_connection()
            cursor = conn.cursor()
            cursor.execute(f"USE {self.system_database}")
            
            # Check if provider already exists
            cursor.execute("SELECT database_name FROM providers WHERE sanitized_name = %s", (sanitized_name,))
            existing = cursor.fetchone()
            
            if existing:
                logger.info(f"Provider '{provider_name}' already registered with database: {existing[0]}")
                return {
                    'provider_name': provider_name,
                    'sanitized_name': sanitized_name,
                    'database_name': existing[0],
                    'status': 'existing'
                }
            
            # Register new provider
            cursor.execute("""
                INSERT INTO providers (provider_name, sanitized_name, database_name)
                VALUES (%s, %s, %s)
            """, (provider_name, sanitized_name, database_name))
            
            conn.commit()
            
            # Create provider database
            self._create_provider_database(database_name)
            
            logger.info(f"New provider '{provider_name}' registered with database: {database_name}")
            
            return {
                'provider_name': provider_name,
                'sanitized_name': sanitized_name,
                'database_name': database_name,
                'status': 'created'
            }
            
        except Exception as e:
            logger.error(f"Failed to register provider '{provider_name}': {e}")
            raise
        finally:
            if conn.is_connected():
                cursor.close()
                conn.close()
    
    def _create_provider_database(self, database_name: str):
        """
        Create a complete database for a provider with all necessary tables
        
        Args:
            database_name: Name of the database to create
        """
        try:
            conn = self._get_system_connection()
            cursor = conn.cursor()
            
            # Create database
            cursor.execute(f"CREATE DATABASE IF NOT EXISTS {database_name} CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
            cursor.execute(f"USE {database_name}")
            
            # Create all tables for this provider
            self._create_provider_tables(cursor)
            
            conn.commit()
            logger.info(f"Provider database '{database_name}' created successfully")
            
        except Exception as e:
            logger.error(f"Failed to create provider database '{database_name}': {e}")
            raise
        finally:
            if conn.is_connected():
                cursor.close()
                conn.close()
    
    def _create_provider_tables(self, cursor):
        """Create all necessary tables for a provider database"""
        
        # 1. Patients table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS patients (
                id INT AUTO_INCREMENT PRIMARY KEY,
                prn VARCHAR(50) UNIQUE NOT NULL COMMENT 'Patient Record Number - Primary unique identifier',
                patient_uuid VARCHAR(255) COMMENT 'EHR system UUID - can change between sessions',
                patient_name VARCHAR(255) NOT NULL,
                first_name VARCHAR(100),
                last_name VARCHAR(100), 
                date_of_birth DATE,
                age VARCHAR(20) COMMENT 'Stored as text like "58 yrs"',
                gender VARCHAR(20),
                phone VARCHAR(20),
                email VARCHAR(100),
                address TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                
                INDEX idx_prn (prn),
                INDEX idx_patient_uuid (patient_uuid),
                INDEX idx_patient_name (patient_name),
                INDEX idx_date_of_birth (date_of_birth)
            ) ENGINE=InnoDB COMMENT='Patient demographics with PRN as primary identifier'
        """)
        
        # 2. Extraction sessions table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS extraction_sessions (
                id INT AUTO_INCREMENT PRIMARY KEY,
                job_id INT COMMENT 'Original WebAutoDash job ID',
                job_name VARCHAR(255),
                portal_name VARCHAR(255),
                extraction_mode ENUM('SINGLE_PATIENT', 'ALL_PATIENTS') NOT NULL,
                target_medication VARCHAR(255) NOT NULL,
                start_date DATE NOT NULL,
                end_date DATE NOT NULL,
                extracted_at TIMESTAMP,
                results_filename VARCHAR(500),
                provider_directory VARCHAR(255),
                total_patients_found INT DEFAULT 0,
                successful_extractions INT DEFAULT 0,
                failed_extractions INT DEFAULT 0,
                conflicts_detected INT DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                
                INDEX idx_target_medication (target_medication),
                INDEX idx_date_range (start_date, end_date),
                INDEX idx_extraction_mode (extraction_mode),
                INDEX idx_extracted_at (extracted_at)
            ) ENGINE=InnoDB COMMENT='Tracks each extraction job/session for this provider'
        """)
        
        # 3. Patient extractions table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS patient_extractions (
                id INT AUTO_INCREMENT PRIMARY KEY,
                prn VARCHAR(50) NOT NULL,
                patient_id INT NOT NULL,
                extraction_session_id INT NOT NULL,
                patient_uuid VARCHAR(255),
                
                filter_medication_name VARCHAR(500),
                filter_medication_strength VARCHAR(100),
                filter_start_date DATE,
                filter_stop_date DATE,
                filter_last_seen DATE,
                filter_provider VARCHAR(255),
                
                summary_page_url TEXT,
                extraction_method VARCHAR(100),
                found_at TIMESTAMP,
                data_checksum VARCHAR(64) COMMENT 'SHA256 hash for change detection',
                processing_status ENUM('pending', 'processed', 'failed', 'conflict') DEFAULT 'pending',
                error_message TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                
                FOREIGN KEY (patient_id) REFERENCES patients(id) ON DELETE CASCADE,
                FOREIGN KEY (extraction_session_id) REFERENCES extraction_sessions(id) ON DELETE CASCADE,
                
                UNIQUE KEY unique_prn_session (prn, extraction_session_id),
                INDEX idx_prn_session (prn, extraction_session_id),
                INDEX idx_filter_medication (filter_medication_name),
                INDEX idx_processing_status (processing_status),
                INDEX idx_data_checksum (data_checksum)
            ) ENGINE=InnoDB COMMENT='Links patients to extraction sessions with metadata'
        """)
        
        # 4. Medications table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS medications (
                id INT AUTO_INCREMENT PRIMARY KEY,
                patient_extraction_id INT NOT NULL,
                medication_type ENUM('active', 'historical', 'current') NOT NULL,
                row_index INT,
                medication_name VARCHAR(500),
                medication_strength VARCHAR(100),
                sig TEXT COMMENT 'Dosage instructions',
                start_date VARCHAR(50) COMMENT 'Various formats in source data',
                stop_date VARCHAR(50),
                dates VARCHAR(100) COMMENT 'Raw date string from source',
                diagnosis VARCHAR(500),
                extraction_method VARCHAR(100),
                extracted_at TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                
                FOREIGN KEY (patient_extraction_id) REFERENCES patient_extractions(id) ON DELETE CASCADE,
                
                INDEX idx_patient_extraction_id (patient_extraction_id),
                INDEX idx_medication_name (medication_name),
                INDEX idx_medication_type (medication_type),
                INDEX idx_medication_strength (medication_strength)
            ) ENGINE=InnoDB COMMENT='Patient medications from extractions'
        """)
        
        # 5. Diagnoses table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS diagnoses (
                id INT AUTO_INCREMENT PRIMARY KEY,
                patient_extraction_id INT NOT NULL,
                diagnosis_type ENUM('current', 'historical') NOT NULL,
                row_index INT,
                diagnosis_text VARCHAR(500),
                diagnosis_code VARCHAR(50) COMMENT 'ICD-10 or other codes',
                acuity VARCHAR(50),
                start_date VARCHAR(50),
                stop_date VARCHAR(50),
                extraction_method VARCHAR(100),
                extracted_at TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                
                FOREIGN KEY (patient_extraction_id) REFERENCES patient_extractions(id) ON DELETE CASCADE,
                
                INDEX idx_patient_extraction_id (patient_extraction_id),
                INDEX idx_diagnosis_text (diagnosis_text),
                INDEX idx_diagnosis_type (diagnosis_type),
                INDEX idx_diagnosis_code (diagnosis_code)
            ) ENGINE=InnoDB COMMENT='Patient diagnoses from extractions'
        """)
        
        # 6. Allergies table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS allergies (
                id INT AUTO_INCREMENT PRIMARY KEY,
                patient_extraction_id INT NOT NULL,
                allergy_type ENUM('drug', 'food', 'environmental') NOT NULL,
                allergy_name VARCHAR(255),
                allergen VARCHAR(255),
                reaction VARCHAR(255),
                severity VARCHAR(50),
                notes TEXT,
                extraction_method VARCHAR(100),
                extracted_at TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                
                FOREIGN KEY (patient_extraction_id) REFERENCES patient_extractions(id) ON DELETE CASCADE,
                
                INDEX idx_patient_extraction_id (patient_extraction_id),
                INDEX idx_allergy_type (allergy_type),
                INDEX idx_allergy_name (allergy_name),
                INDEX idx_allergen (allergen)
            ) ENGINE=InnoDB COMMENT='Patient allergies from extractions'
        """)
        
        # 7. Health concerns table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS health_concerns (
                id INT AUTO_INCREMENT PRIMARY KEY,
                patient_extraction_id INT NOT NULL,
                concern_type ENUM('active', 'inactive', 'note') NOT NULL,
                concern_text TEXT,
                concern_category VARCHAR(100),
                status VARCHAR(50),
                priority VARCHAR(50),
                start_date VARCHAR(50),
                end_date VARCHAR(50),
                notes TEXT,
                extraction_method VARCHAR(100),
                extracted_at TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                
                FOREIGN KEY (patient_extraction_id) REFERENCES patient_extractions(id) ON DELETE CASCADE,
                
                INDEX idx_patient_extraction_id (patient_extraction_id),
                INDEX idx_concern_type (concern_type),
                INDEX idx_status (status),
                INDEX idx_priority (priority)
            ) ENGINE=InnoDB COMMENT='Patient health concerns from extractions'
        """)
        
        # 8. Data conflicts table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS data_conflicts (
                id INT AUTO_INCREMENT PRIMARY KEY,
                patient_id INT NOT NULL,
                prn VARCHAR(50) NOT NULL,
                conflict_type ENUM('demographic_mismatch', 'medication_conflict', 'extraction_duplicate', 'data_changed') NOT NULL,
                extraction_session_id_1 INT COMMENT 'Original extraction',
                extraction_session_id_2 INT COMMENT 'Conflicting extraction',
                field_name VARCHAR(100),
                old_value TEXT,
                new_value TEXT,
                conflict_description TEXT,
                severity ENUM('low', 'medium', 'high', 'critical') DEFAULT 'medium',
                status ENUM('unresolved', 'reviewing', 'resolved', 'false_positive') DEFAULT 'unresolved',
                detected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                reviewed_by VARCHAR(100),
                reviewed_at TIMESTAMP NULL,
                resolution_notes TEXT,
                
                FOREIGN KEY (patient_id) REFERENCES patients(id) ON DELETE CASCADE,
                FOREIGN KEY (extraction_session_id_1) REFERENCES extraction_sessions(id) ON DELETE CASCADE,
                FOREIGN KEY (extraction_session_id_2) REFERENCES extraction_sessions(id) ON DELETE CASCADE,
                
                INDEX idx_patient_conflicts (patient_id),
                INDEX idx_prn_conflicts (prn),
                INDEX idx_conflict_status (status),
                INDEX idx_conflict_type (conflict_type),
                INDEX idx_severity (severity)
            ) ENGINE=InnoDB COMMENT='Tracks data conflicts and mismatches for review'
        """)

        # 9. Comprehensive Patient Records table - organized by date ranges
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS comprehensive_patient_records (
                id INT AUTO_INCREMENT PRIMARY KEY,
                prn VARCHAR(50) NOT NULL,
                patient_id INT NOT NULL,
                patient_name VARCHAR(255) NOT NULL,
                date_of_birth DATE,
                gender VARCHAR(20),
                age VARCHAR(20),
                
                -- Date range for this comprehensive record
                date_range_start DATE NOT NULL,
                date_range_end DATE NOT NULL,
                target_medication VARCHAR(255),
                
                -- JSON fields for comprehensive medical data
                all_medications JSON COMMENT 'Complete medications list for this date range',
                all_diagnoses JSON COMMENT 'Complete diagnoses list for this date range',
                all_allergies JSON COMMENT 'Complete allergies list for this date range',
                all_health_concerns JSON COMMENT 'Complete health concerns list for this date range',
                
                -- Metadata
                extraction_session_id INT NOT NULL,
                data_checksum VARCHAR(64) COMMENT 'Checksum for conflict detection',
                record_status ENUM('active', 'superseded', 'conflict') DEFAULT 'active',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                
                FOREIGN KEY (patient_id) REFERENCES patients(id) ON DELETE CASCADE,
                FOREIGN KEY (extraction_session_id) REFERENCES extraction_sessions(id) ON DELETE CASCADE,
                
                UNIQUE KEY unique_prn_date_range (prn, date_range_start, date_range_end, target_medication),
                INDEX idx_prn_comprehensive (prn),
                INDEX idx_patient_comprehensive (patient_id),
                INDEX idx_date_range_comprehensive (date_range_start, date_range_end),
                INDEX idx_target_medication_comprehensive (target_medication),
                INDEX idx_record_status (record_status),
                INDEX idx_data_checksum_comprehensive (data_checksum)
            ) ENGINE=InnoDB COMMENT='Comprehensive patient records organized by date ranges with all medical data'
        """)
    
    def get_provider_connection(self, provider_name: str) -> mysql.connector.MySQLConnection:
        """
        Get database connection for a specific provider
        
        Args:
            provider_name: Provider name
            
        Returns:
            MySQL connection to provider's database
        """
        # Register provider if not exists (creates database if needed)
        provider_info = self.register_provider(provider_name)
        database_name = provider_info['database_name']
        
        try:
            config = self.mysql_config.copy()
            config['database'] = database_name
            
            conn = mysql.connector.connect(**config)
            if conn.is_connected():
                logger.debug(f"Connected to provider database: {database_name}")
                return conn
            else:
                raise Error("Connection failed")
                
        except Error as err:
            logger.error(f"Provider database connection error for {database_name}: {err}")
            raise
    
    def list_providers(self) -> List[Dict[str, Any]]:
        """Get list of all registered providers"""
        try:
            conn = self._get_system_connection()
            cursor = conn.cursor(dictionary=True)
            cursor.execute(f"USE {self.system_database}")
            
            cursor.execute("""
                SELECT provider_name, sanitized_name, database_name, 
                       created_at, last_extraction, total_extractions, 
                       total_patients, status
                FROM providers
                ORDER BY provider_name
            """)
            
            return cursor.fetchall()
            
        except Exception as e:
            logger.error(f"Failed to list providers: {e}")
            return []
        finally:
            if conn.is_connected():
                cursor.close()
                conn.close()
    
    def log_system_event(self, level: str, component: str, message: str, 
                        provider_name: str = None, details: Dict = None):
        """Log system events to central logging"""
        try:
            conn = self._get_system_connection()
            cursor = conn.cursor()
            cursor.execute(f"USE {self.system_database}")
            
            database_name = None
            if provider_name:
                database_name = self.get_provider_database_name(provider_name)
            
            cursor.execute("""
                INSERT INTO system_logs (
                    log_level, component, message, provider_name, 
                    database_name, details
                ) VALUES (%s, %s, %s, %s, %s, %s)
            """, (
                level, component, message, provider_name,
                database_name, json.dumps(details) if details else None
            ))
            
            conn.commit()
            
        except Exception as e:
            logger.error(f"Failed to log system event: {e}")
        finally:
            if conn.is_connected():
                cursor.close()
                conn.close()

# Global instance
provider_db_manager = ProviderDatabaseManager()

def get_provider_connection(provider_name: str) -> mysql.connector.MySQLConnection:
    """
    Get database connection for a specific provider (legacy compatibility)
    
    Args:
        provider_name: Provider name from JSON data
        
    Returns:
        MySQL connection to provider's dedicated database
    """
    return provider_db_manager.get_provider_connection(provider_name)

def calculate_data_checksum(patient_data: dict) -> str:
    """
    Calculate comprehensive checksum for patient data to detect changes
    
    Args:
        patient_data: Complete patient data from JSON extraction
        
    Returns:
        SHA256 hexdigest of normalized patient data
    """
    try:
        demographics = patient_data.get('demographics_printable', {})
        
        # Create normalized data structure for checksum
        checksum_data = {
            'demographics': {
                'name': demographics.get('patient_name', '').strip().lower(),
                'dob': demographics.get('date_of_birth', ''),
                'gender': demographics.get('gender', '').lower(),
                'age': demographics.get('age', '')
            },
            'medications': {
                'count': len(patient_data.get('all_medications', [])),
                'items': sorted([
                    {
                        'name': med.get('medication_name', '').strip().lower(),
                        'type': med.get('medication_type', ''),
                        'sig': med.get('sig', '').strip()
                    }
                    for med in patient_data.get('all_medications', [])
                ], key=lambda x: x['name'])
            },
            'diagnoses': {
                'count': len(patient_data.get('all_diagnoses', [])),
                'items': sorted([
                    {
                        'text': diag.get('diagnosis_text', '').strip().lower(),
                        'type': diag.get('diagnosis_type', ''),
                        'acuity': diag.get('acuity', '')
                    }
                    for diag in patient_data.get('all_diagnoses', [])
                ], key=lambda x: x['text'])
            },
            'allergies': {
                'count': len(patient_data.get('all_allergies', [])),
                'items': sorted([
                    str(allergy).strip().lower()
                    for allergy in patient_data.get('all_allergies', [])
                ])
            },
            'health_concerns': {
                'count': len(patient_data.get('all_health_concerns', [])),
                'items': sorted([
                    str(concern).strip().lower()
                    for concern in patient_data.get('all_health_concerns', [])
                ])
            }
        }
        
        # Convert to JSON string and calculate hash
        checksum_string = json.dumps(checksum_data, sort_keys=True, separators=(',', ':'))
        return hashlib.sha256(checksum_string.encode('utf-8')).hexdigest()
        
    except Exception as e:
        logger.error(f"Error calculating checksum: {e}")
        return hashlib.sha256(str(patient_data).encode('utf-8')).hexdigest()

# Test the connection on import
try:
    logger.info("Testing provider database manager initialization...")
    test_providers = provider_db_manager.list_providers()
    logger.info(f"Provider database manager initialized successfully. Found {len(test_providers)} existing providers.")
except Exception as e:
    logger.error(f"Provider database manager initialization failed: {e}") 