# WebAutoDash Table Architecture Guide

## 🏗️ Database Structure Overview

The WebAutoDash system uses **provider-separated databases** for complete data isolation. Each provider gets their own database with identical table structures.

### Database Naming Convention
- **System Database**: `webautodash_system` - Central registry of all providers
- **Provider Databases**: `webautodash_{provider_name}` - e.g., `webautodash_gary_wang`

---

## 📊 Table Relationships & Architecture

```
┌─────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   PATIENTS  │    │ EXTRACTION_      │    │ PATIENT_        │
│             │    │ SESSIONS         │    │ EXTRACTIONS     │
│ - id (PK)   │    │                  │    │                 │
│ - prn (UNI) │    │ - id (PK)        │    │ - id (PK)       │
│ - name      │◄───┤ - job_name       │◄───┤ - prn (FK)      │
│ - dob       │    │ - portal_name    │    │ - patient_id    │
│ - demographics  │ │ - target_med     │    │ - session_id    │
└─────────────┘    │ - date_range     │    │ - checksum      │
                   └──────────────────┘    └─────────────────┘
                                                    │
                          ┌─────────────────────────┼─────────────────────────┐
                          │                         │                         │
                          ▼                         ▼                         ▼
                   ┌─────────────┐         ┌─────────────┐         ┌─────────────┐
                   │ MEDICATIONS │         │ DIAGNOSES   │         │ ALLERGIES   │
                   │             │         │             │         │             │
                   │ - id (PK)   │         │ - id (PK)   │         │ - id (PK)   │
                   │ - extract_id│         │ - extract_id│         │ - extract_id│
                   │ - med_name  │         │ - diagnosis │         │ - allergen  │
                   │ - strength  │         │ - code      │         │ - reaction  │
                   │ - sig       │         │ - acuity    │         │ - severity  │
                   └─────────────┘         └─────────────┘         └─────────────┘
                          │
                          ▼
                   ┌─────────────┐         ┌─────────────┐
                   │ HEALTH_     │         │ DATA_       │
                   │ CONCERNS    │         │ CONFLICTS   │
                   │             │         │             │
                   │ - id (PK)   │         │ - id (PK)   │
                   │ - extract_id│         │ - patient_id│
                   │ - concern   │         │ - prn       │
                   │ - category  │         │ - conflict  │
                   │ - status    │         │ - severity  │
                   └─────────────┘         └─────────────┘
```

---

## 🔍 Detailed Table Explanations

### 1. **PATIENTS** (Master Patient Index)
**Purpose**: Central repository of unique patients using PRN as the primary identifier

| Column | Type | Purpose |
|--------|------|---------|
| `id` | INT(PK) | Auto-increment primary key |
| `prn` | VARCHAR(50)(UNIQUE) | **Patient Record Number - UNIQUE IDENTIFIER** |
| `patient_uuid` | VARCHAR(255) | UUID from source system |
| `patient_name` | VARCHAR(255) | Full patient name |
| `first_name` | VARCHAR(100) | First name |
| `last_name` | VARCHAR(100) | Last name |
| `date_of_birth` | DATE | Date of birth |
| `age` | VARCHAR(20) | Age string (e.g., "43 yrs") |
| `gender` | VARCHAR(20) | Patient gender |
| `phone` | VARCHAR(20) | Contact phone |
| `email` | VARCHAR(100) | Email address |
| `address` | TEXT | Full address |

**Key Points**:
- PRN is the **unique patient identifier** across all extractions
- One patient = One PRN, regardless of how many times they're extracted
- Demographics can be updated if conflicts are detected

---

### 2. **EXTRACTION_SESSIONS** (Job History)
**Purpose**: Track each JSON file processing session with metadata

| Column | Type | Purpose |
|--------|------|---------|
| `id` | INT(PK) | Session identifier |
| `job_id` | INT | WebAutoDash job ID |
| `job_name` | VARCHAR(255) | Human-readable job name |
| `portal_name` | VARCHAR(255) | Source portal (e.g., "Epic MyChart") |
| `extraction_mode` | ENUM | 'SINGLE_PATIENT' or 'ALL_PATIENTS' |
| `target_medication` | VARCHAR(255) | Medication being searched for |
| `start_date` | DATE | **Search date range start** |
| `end_date` | DATE | **Search date range end** |
| `extracted_at` | TIMESTAMP | When extraction was performed |
| `results_filename` | VARCHAR(500) | Original JSON filename |
| `total_patients_found` | INT | Patients found in this session |

**Key Points**:
- Each JSON file = One extraction session
- Date range is crucial for conflict detection
- Multiple sessions can target the same medication with different date ranges

---

### 3. **PATIENT_EXTRACTIONS** (Patient-Session Links)
**Purpose**: Link patients to extraction sessions and detect duplicates

| Column | Type | Purpose |
|--------|------|---------|
| `id` | INT(PK) | Link identifier |
| `prn` | VARCHAR(50) | Patient Record Number |
| `patient_id` | INT(FK) | Reference to patients table |
| `extraction_session_id` | INT(FK) | Reference to extraction_sessions |
| `filter_medication_name` | VARCHAR(500) | Medication that matched this patient |
| `filter_start_date` | DATE | **Medication date range start** |
| `filter_stop_date` | DATE | **Medication date range end** |
| `data_checksum` | VARCHAR(64) | **SHA-256 hash of patient data** |
| `processing_status` | ENUM | 'pending', 'processed', 'failed', 'conflict' |

**Unique Constraint**: `(prn, extraction_session_id)` - Prevents duplicate patient in same session

**Key Points**:
- **Duplicate Detection**: Same PRN + same session = duplicate (blocked)
- **Conflict Detection**: Same PRN + different sessions + different checksum = conflict
- Checksum includes: medications, diagnoses, allergies, health_concerns for the date range

---

### 4. **MEDICATIONS** (Patient Medications)
**Purpose**: Store all medication data extracted for patients

| Column | Type | Purpose |
|--------|------|---------|
| `id` | INT(PK) | Medication record ID |
| `patient_extraction_id` | INT(FK) | Links to patient_extractions |
| `medication_type` | ENUM | 'active', 'historical', 'current' |
| `medication_name` | VARCHAR(500) | Full medication name |
| `medication_strength` | VARCHAR(100) | Dosage/strength |
| `sig` | TEXT | Prescription instructions |
| `start_date` | VARCHAR(50) | When medication started |
| `stop_date` | VARCHAR(50) | When medication stopped |
| `dates` | VARCHAR(100) | Date range string |
| `diagnosis` | VARCHAR(500) | Associated diagnosis |

**Key Points**:
- All medications for a patient extraction are stored
- Used in checksum calculation for conflict detection
- Date ranges help identify overlapping medications

---

### 5. **DIAGNOSES** (Patient Diagnoses)
**Purpose**: Store all diagnosis/condition data

| Column | Type | Purpose |
|--------|------|---------|
| `id` | INT(PK) | Diagnosis record ID |
| `patient_extraction_id` | INT(FK) | Links to patient_extractions |
| `diagnosis_type` | ENUM | 'current', 'historical' |
| `diagnosis_text` | VARCHAR(500) | Diagnosis description |
| `diagnosis_code` | VARCHAR(50) | ICD/diagnostic code |
| `acuity` | VARCHAR(50) | Severity/acuity |
| `start_date` | VARCHAR(50) | Diagnosis start date |
| `stop_date` | VARCHAR(50) | Diagnosis end date |

**Key Points**:
- Includes current and historical diagnoses
- Part of checksum calculation
- Date-based filtering for conflict detection

---

### 6. **ALLERGIES** (Patient Allergies)
**Purpose**: Store patient allergy information

| Column | Type | Purpose |
|--------|------|---------|
| `id` | INT(PK) | Allergy record ID |
| `patient_extraction_id` | INT(FK) | Links to patient_extractions |
| `allergy_type` | ENUM | 'drug', 'food', 'environmental' |
| `allergy_name` | VARCHAR(255) | Allergy name |
| `allergen` | VARCHAR(255) | Specific allergen |
| `reaction` | VARCHAR(255) | Patient reaction |
| `severity` | VARCHAR(50) | Severity level |

**Key Points**:
- Critical for patient safety
- Included in conflict detection
- Categorized by allergy type

---

### 7. **HEALTH_CONCERNS** (Patient Health Notes)
**Purpose**: Store health concerns, notes, and observations

| Column | Type | Purpose |
|--------|------|---------|
| `id` | INT(PK) | Health concern ID |
| `patient_extraction_id` | INT(FK) | Links to patient_extractions |
| `concern_type` | ENUM | 'active', 'inactive', 'note' |
| `concern_text` | TEXT | Health concern description |
| `concern_category` | VARCHAR(100) | Category/type of concern |
| `status` | VARCHAR(50) | Current status |
| `priority` | VARCHAR(50) | Priority level |
| `start_date` | VARCHAR(50) | When concern started |
| `end_date` | VARCHAR(50) | When concern resolved |

**Key Points**:
- Free-text health observations
- Includes clinical notes
- Part of comprehensive patient picture

---

### 8. **DATA_CONFLICTS** (Conflict Tracking)
**Purpose**: Track when patient data changes between extractions

| Column | Type | Purpose |
|--------|------|---------|
| `id` | INT(PK) | Conflict record ID |
| `patient_id` | INT(FK) | Patient involved |
| `prn` | VARCHAR(50) | Patient Record Number |
| `conflict_type` | ENUM | Type of conflict detected |
| `extraction_session_id_1` | INT(FK) | First session |
| `extraction_session_id_2` | INT(FK) | Second session |
| `field_name` | VARCHAR(100) | Field that changed |
| `old_value` | TEXT | Previous value |
| `new_value` | TEXT | New value |
| `conflict_description` | TEXT | Human-readable description |
| `severity` | ENUM | 'low', 'medium', 'high', 'critical' |
| `status` | ENUM | 'unresolved', 'reviewing', 'resolved' |

**Conflict Types**:
- `demographic_mismatch`: Patient demographics changed
- `medication_conflict`: Medication data differs for same date range
- `extraction_duplicate`: Attempted duplicate extraction
- `data_changed`: General data change detected

---

## 🔍 Conflict Detection Logic

### Current Implementation Issues (Your Concerns)

**You mentioned**: *"I want to check differences in only (medications, PRN, diagnoses, health concerns, allergies) in same date range not on UUID"*

### Current Checksum Calculation
The system currently creates a checksum from:
```python
# This includes ALL data which may not be what you want
checksum_data = {
    'patient_uuid': patient_data.get('patient_uuid'),
    'medications': medications_data,
    'diagnoses': diagnoses_data, 
    'allergies': allergies_data,
    'health_concerns': health_concerns_data
}
```

### **Recommended Fix**: Date-Range Based Conflict Detection

The system should compare data for **overlapping date ranges only**:

1. **Same PRN** ✅ (Already implemented)
2. **Overlapping Date Ranges** ❌ (Needs implementation)
3. **Compare Only**: medications, diagnoses, allergies, health_concerns ✅ (Partially implemented)
4. **Exclude UUID from comparison** ❌ (Currently included)

### Improved Conflict Detection Algorithm:

```python
def detect_conflicts(new_extraction, existing_extractions):
    """
    Compare new extraction with existing ones for same PRN
    Only compare data in overlapping date ranges
    """
    for existing in existing_extractions:
        # Check if date ranges overlap
        if date_ranges_overlap(new_extraction.date_range, existing.date_range):
            # Filter data to overlapping period only
            new_data = filter_data_by_date_range(new_extraction, overlap_range)
            old_data = filter_data_by_date_range(existing, overlap_range)
            
            # Compare only medical data (exclude UUID)
            medical_data_changed = compare_medical_data(new_data, old_data)
            
            if medical_data_changed:
                create_conflict_record(differences)
```

---

## 🚀 Automatic Population System

### Current JSON File Monitoring

The system automatically populates tables when JSON files are saved:

1. **File Watcher**: `json_file_monitor.py` monitors `Results/` directory
2. **Automatic Processing**: New JSON files trigger immediate processing
3. **Provider Detection**: Folder structure determines provider
4. **Data Extraction**: JSON content is parsed and stored

### How to Enable Automatic Population:

```bash
# Start monitoring for new JSON files
python json_file_monitor.py monitor

# Check current status
python json_file_monitor.py status
```

### JSON Processing Flow:

```
JSON File Saved → File Detected → Provider Identified → Database Created/Used → Data Processed → Conflicts Checked → Tables Populated
```

---

## 🧹 Database Cleanup & Management

### Clean All Data (Keep Structure):
```bash
python cleanup_database.py --clean-all-data
```

### Clean Specific Provider:
```bash
python cleanup_database.py --provider "gary_wang" --clean-data
```

### Complete System Reset:
```bash
python cleanup_database.py --reset-system
```

### View Current Statistics:
```bash
python cleanup_database.py --stats
```

---

## 📋 Querying Patient Data

### Get Complete Patient Record:
```bash
python patient_data_query.py --prn "MH167307" --provider "gary_wang"
```

### Filter by Date Range:
```bash
python patient_data_query.py --prn "MH167307" --provider "gary_wang" --date-start "2020-01-01" --date-end "2023-12-31"
```

### List All Patients:
```bash
python patient_data_query.py --provider "gary_wang" --list-patients
```

### View Conflicts:
```bash
python patient_data_query.py --provider "gary_wang" --conflicts
```

---

## 🎯 Key Benefits of This Architecture

1. **Provider Isolation**: Complete data separation between providers
2. **PRN-Based Identity**: Consistent patient identification across extractions
3. **Conflict Detection**: Automatic detection of data changes
4. **Audit Trail**: Complete history of all extractions
5. **Scalability**: Easy to add new providers
6. **Data Integrity**: Foreign key constraints ensure referential integrity

---

## 🔧 Next Steps for Improvement

1. **Fix Conflict Detection**: Implement date-range based comparison
2. **Exclude UUID**: Remove UUID from conflict detection
3. **Enhanced Filtering**: Better date range overlap detection
4. **Performance Optimization**: Add indexes for common queries
5. **Data Validation**: Add more robust data validation rules

This architecture provides a solid foundation for managing multi-provider patient data with proper isolation and conflict detection. 