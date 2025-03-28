# WebAutoDash MySQL Provider Integration

## 🎯 Overview

This MySQL integration provides **complete provider separation** for WebAutoDash patient data. Each provider gets their own dedicated database, ensuring:

- **🔒 Data Isolation**: Each provider's patients are completely separate
- **🛡️ Security**: No risk of data mixing between providers  
- **📈 Scalability**: Easy to add new providers
- **⚖️ Compliance**: Better for HIPAA/privacy requirements
- **🔍 Conflict Detection**: Automatic detection of data changes and duplicates

## 🗄️ Database Architecture

### Provider Separation Model
```
MySQL Server
├── webautodash_system (master database)
│   ├── providers (tracks all providers)
│   └── system_logs (system-wide logging)
├── webautodash_gary_wang (Gary Wang's data)
│   ├── patients, medications, diagnoses, etc.
├── webautodash_john_doe (John Doe's data)
│   ├── patients, medications, diagnoses, etc.
└── webautodash_[provider_name] (each provider gets own DB)
```

### Key Features

1. **PRN-Based Identification**: Uses Patient Record Number (PRN) as primary unique identifier
2. **Checksum Validation**: Detects data changes between extractions
3. **Duplicate Prevention**: Prevents redundant data for same patient/medication/dates
4. **Conflict Resolution**: Alerts when same patient data differs between extractions
5. **Automatic Processing**: Monitors Results folder and processes new JSON files

## 🚀 Quick Start

### Step 1: Install Dependencies
```bash
cd Projects/WebAutoDash/backend
pip install -r requirements_mysql.txt
```

### Step 2: Configure Environment
The system uses your existing MySQL credentials:
- **Host**: localhost
- **User**: root  
- **Password**: Jetson@123
- **Port**: 3306

### Step 3: Run Setup
```bash
python setup_mysql_provider_db.py
```

This will:
- Test MySQL connection
- Create system database
- Discover existing providers from Results folder
- Create provider databases
- Process existing JSON files
- Set up monitoring system

### Step 4: Start Monitoring (Optional)
```bash
python json_file_monitor.py monitor
```

## 📊 How It Works - Complete Flow

### Data Processing Flow
```
JSON File Created → Provider Detection → PRN Extraction → Duplicate Check → Database Storage → Conflict Detection → Alerts
```

### Detailed Steps

1. **JSON File Detection**: New files in `Results/[provider_name]/` are automatically detected
2. **Provider Registration**: Provider databases created automatically (e.g., `webautodash_gary_wang`)
3. **PRN Extraction**: Patient Record Number extracted from `demographics_printable.prn`
4. **Duplicate Detection**: Checks for same PRN + medication + date range
5. **Data Storage**: Patient demographics and medical data stored in provider's database
6. **Conflict Detection**: Checksums detect if patient data changed between extractions
7. **Alert Generation**: Notifications for conflicts or data mismatches

## 🗃️ Database Schema

### Core Tables (per provider database)

#### `patients` - Patient Demographics
- `prn` (PRIMARY) - Patient Record Number (unique identifier)
- `patient_uuid` - EHR system UUID (can change)
- `patient_name`, `first_name`, `last_name`
- `date_of_birth`, `age`, `gender`
- Demographics with PRN as primary identifier

#### `extraction_sessions` - Extraction Jobs
- Tracks each extraction job/session
- `target_medication`, `start_date`, `end_date`
- `extraction_mode` (SINGLE_PATIENT, ALL_PATIENTS)
- Job metadata and statistics

#### `patient_extractions` - Patient-Session Links
- Links patients to extraction sessions
- `prn`, `patient_id`, `extraction_session_id`
- `data_checksum` for change detection
- Filter criteria and processing status

#### `medications` - Patient Medications
- `medication_name`, `medication_strength`, `sig`
- `medication_type` (active, historical, current)
- Start/stop dates and diagnoses

#### `diagnoses` - Patient Diagnoses  
- `diagnosis_text`, `diagnosis_code` (ICD-10)
- `diagnosis_type` (current, historical)
- Acuity and date information

#### `allergies` - Patient Allergies
- `allergy_type` (drug, food, environmental)
- `allergen`, `reaction`, `severity`

#### `health_concerns` - Health Concerns
- `concern_type` (active, inactive, note)
- `concern_text`, `status`, `priority`

#### `data_conflicts` - Conflict Tracking
- Automatic conflict detection and logging
- `conflict_type`, `severity`, `status`
- Old vs new values for review

## 🔄 Duplicate & Conflict Handling

### Duplicate Detection Logic
```python
# Same PRN + Same Medication + Same Date Range = Potential Duplicate
if existing_extraction_found:
    if data_checksum_matches:
        # Skip duplicate - identical data
        log_duplicate()
    else:
        # Create conflict record - data changed
        log_conflict()
        create_new_extraction()
```

### Conflict Types
1. **Demographic Mismatch**: Patient name/info differs for same PRN
2. **Medication Conflict**: Different medications for same patient/dates
3. **Data Changed**: Same extraction criteria but different medical data
4. **Extraction Duplicate**: Identical data extracted multiple times

## 📁 File Structure
```
Projects/WebAutoDash/backend/
├── webautodash.env                 # MySQL configuration
├── db_connection_provider.py       # Provider database manager
├── data_processor_provider.py      # JSON data processor
├── json_file_monitor.py           # File monitoring system
├── setup_mysql_provider_db.py     # Setup script
├── test_mysql_integration.py      # Test suite
├── requirements_mysql.txt         # Dependencies
└── README_MySQL_Integration.md    # This file
```

## 🛠️ Usage Examples

### Process Single JSON File
```python
from data_processor_provider import provider_processor

result = provider_processor.process_json_file('Results/gary_wang/extraction.json')
print(f"Processed {result['patients_processed']} patients for {result['provider_name']}")
```

### Get Provider Statistics
```python
from data_processor_provider import provider_processor

# All providers
stats = provider_processor.get_provider_statistics()

# Specific provider  
stats = provider_processor.get_provider_statistics('gary_wang')
print(f"Total patients: {stats['total_patients']}")
```

### Monitor Results Folder
```python
from json_file_monitor import file_monitor

# Start monitoring
file_monitor.start_monitoring(check_interval=10)  # Check every 10 seconds

# Process existing files once
file_monitor.process_existing_files()

# Get status
status = file_monitor.get_monitoring_status()
```

### Manual Provider Database Access
```python
from db_connection_provider import get_provider_connection

# Get connection to specific provider's database
conn = get_provider_connection('gary_wang')
cursor = conn.cursor()

# Query provider's data
cursor.execute("SELECT COUNT(*) FROM patients")
patient_count = cursor.fetchone()[0]
print(f"Gary Wang has {patient_count} patients")
```

## 🔧 Command Line Tools

### Setup System
```bash
python setup_mysql_provider_db.py              # Interactive setup
python setup_mysql_provider_db.py --auto       # Automatic setup
```

### File Monitoring
```bash
python json_file_monitor.py monitor    # Start continuous monitoring
python json_file_monitor.py process    # Process existing files once
python json_file_monitor.py status     # Show current status
```

### Testing
```bash
python test_mysql_integration.py       # Run full test suite
python test_mysql_integration.py --quick  # Quick connectivity tests
```

## 📊 Monitoring & Alerts

### System Logs
All activities are logged in `webautodash_system.system_logs`:
- File processing events
- Provider registrations
- Conflict detections
- Error conditions

### Conflict Alerts
When conflicts are detected:
1. Record saved in `data_conflicts` table
2. System log entry created
3. Processing continues with new data
4. Manual review recommended

### Performance Monitoring
```python
# Get comprehensive statistics
from json_file_monitor import file_monitor
status = file_monitor.get_provider_summary()

print(f"Total providers: {status['provider_database_statistics']['total_providers']}")
print(f"Files processed: {status['monitoring_status']['statistics']['files_processed']}")
print(f"Conflicts detected: {status['monitoring_status']['statistics']['conflicts_detected']}")
```

## 🚨 Troubleshooting

### Common Issues

1. **MySQL Connection Failed**
   ```bash
   # Check MySQL is running
   sudo systemctl status mysql
   
   # Test connection manually
   mysql -u root -p -h localhost
   ```

2. **Provider Database Not Created**
   ```python
   # Force provider registration
   from db_connection_provider import provider_db_manager
   provider_db_manager.register_provider('provider_name')
   ```

3. **JSON Processing Errors**
   ```bash
   # Check JSON file structure
   python -m json.tool Results/provider/file.json
   
   # Run single file test
   python test_mysql_integration.py --quick
   ```

4. **Duplicate/Conflict Issues**
   ```sql
   -- Check conflicts for a provider
   USE webautodash_gary_wang;
   SELECT * FROM data_conflicts WHERE status = 'unresolved';
   
   -- Check duplicate extractions
   SELECT prn, COUNT(*) as extraction_count 
   FROM patient_extractions 
   GROUP BY prn 
   HAVING extraction_count > 1;
   ```

### Log Locations
- Setup logs: `setup_mysql.log`
- System logs: `webautodash_system.system_logs` table
- File monitor cache: `processed_files_cache.json`

## 🔐 Security Considerations

1. **Provider Isolation**: Each provider has separate database - no cross-contamination
2. **PRN-Based Identity**: Uses medical record numbers, not names for identification
3. **Checksum Validation**: Detects unauthorized data changes
4. **Audit Trail**: Complete logging of all operations
5. **Access Control**: MySQL user permissions control database access

## 📈 Performance Tips

1. **Batch Processing**: Process multiple files together when possible
2. **Monitoring Interval**: Adjust `check_interval` based on file frequency
3. **Database Indexing**: Tables are pre-indexed on common query fields
4. **Connection Pooling**: Reuse database connections where possible

## 🔄 Future Enhancements

- **Email Alerts**: Automatic email notifications for conflicts
- **Web Dashboard**: Real-time monitoring interface  
- **Data Export**: Export provider data to various formats
- **Advanced Analytics**: Patient trend analysis and reporting
- **Backup Automation**: Automated database backups per provider

## 📞 Support

For issues or questions:
1. Check the troubleshooting section
2. Run the test suite: `python test_mysql_integration.py`
3. Review system logs in `webautodash_system.system_logs`
4. Check file monitor status: `python json_file_monitor.py status` 