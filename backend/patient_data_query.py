#!/usr/bin/env python3
"""
Patient Data Query System
========================
Comprehensive script to fetch all patient medical data including:
- Demographics
- Medications (active, historical, current)
- Diagnoses (current, historical) 
- Health Concerns (active, inactive, notes)
- Allergies (drug, food, environmental)
- Data conflicts and extraction history

Usage Examples:
    python patient_data_query.py --prn "MH167307" --provider "gary_wang"
    python patient_data_query.py --patient-name "Melissa Gonzalez" --provider "gary_wang"
    python patient_data_query.py --provider "gary_wang" --list-patients
    python patient_data_query.py --provider "gary_wang" --conflicts
"""

import argparse
import sys
import json
from datetime import datetime
from typing import Dict, List, Optional, Any

import mysql.connector
from dotenv import load_dotenv
import os

# Setup
load_dotenv('.env', override=True)

class PatientDataQuery:
    """Patient data query and analysis system"""
    
    def __init__(self):
        """Initialize database connection"""
        self.config = {
            'host': os.getenv('WEBAUTODASH_DB_HOST', '128.205.221.54'),
            'port': int(os.getenv('WEBAUTODASH_DB_PORT', 3306)),
            'user': os.getenv('WEBAUTODASH_DB_USER', 'xvoice_user'),
            'password': os.getenv('WEBAUTODASH_DB_PASSWORD', 'Jetson@123')
        }
    
    def get_connection(self, database: str):
        """Get database connection"""
        config = self.config.copy()
        config['database'] = database
        return mysql.connector.connect(**config)
    
    def get_provider_database(self, provider_name: str) -> str:
        """Convert provider name to database name"""
        return f"webautodash_{provider_name.lower().replace(' ', '_')}"
    
    def get_patient_demographics(self, database: str, prn: str = None, patient_name: str = None) -> Optional[Dict]:
        """Get patient demographics by PRN or name"""
        conn = self.get_connection(database)
        cursor = conn.cursor(dictionary=True)
        
        try:
            if prn:
                query = "SELECT * FROM patients WHERE prn = %s"
                cursor.execute(query, (prn,))
            elif patient_name:
                query = "SELECT * FROM patients WHERE patient_name LIKE %s"
                cursor.execute(query, (f"%{patient_name}%",))
            else:
                return None
            
            result = cursor.fetchone()
            return result
            
        finally:
            cursor.close()
            conn.close()
    
    def get_patient_extractions(self, database: str, prn: str) -> List[Dict]:
        """Get all extraction sessions for a patient"""
        conn = self.get_connection(database)
        cursor = conn.cursor(dictionary=True)
        
        try:
            query = """
            SELECT pe.*, es.job_name, es.portal_name, es.target_medication, 
                   es.start_date, es.end_date, es.extracted_at
            FROM patient_extractions pe
            JOIN extraction_sessions es ON pe.extraction_session_id = es.id
            WHERE pe.prn = %s
            ORDER BY es.extracted_at DESC
            """
            cursor.execute(query, (prn,))
            return cursor.fetchall()
            
        finally:
            cursor.close()
            conn.close()
    
    def get_patient_medications(self, database: str, prn: str, date_range: tuple = None) -> List[Dict]:
        """Get all medications for a patient"""
        conn = self.get_connection(database)
        cursor = conn.cursor(dictionary=True)
        
        try:
            base_query = """
            SELECT m.*, pe.extraction_session_id, es.target_medication as session_medication,
                   es.start_date as session_start, es.end_date as session_end,
                   es.extracted_at, es.job_name
            FROM medications m
            JOIN patient_extractions pe ON m.patient_extraction_id = pe.id
            JOIN extraction_sessions es ON pe.extraction_session_id = es.id
            WHERE pe.prn = %s
            """
            
            params = [prn]
            
            if date_range:
                base_query += " AND es.start_date >= %s AND es.end_date <= %s"
                params.extend(date_range)
            
            base_query += " ORDER BY m.medication_type, m.created_at DESC"
            
            cursor.execute(base_query, params)
            return cursor.fetchall()
            
        finally:
            cursor.close()
            conn.close()
    
    def get_patient_diagnoses(self, database: str, prn: str, date_range: tuple = None) -> List[Dict]:
        """Get all diagnoses for a patient"""
        conn = self.get_connection(database)
        cursor = conn.cursor(dictionary=True)
        
        try:
            base_query = """
            SELECT d.*, pe.extraction_session_id, es.start_date as session_start, 
                   es.end_date as session_end, es.extracted_at, es.job_name
            FROM diagnoses d
            JOIN patient_extractions pe ON d.patient_extraction_id = pe.id
            JOIN extraction_sessions es ON pe.extraction_session_id = es.id
            WHERE pe.prn = %s
            """
            
            params = [prn]
            
            if date_range:
                base_query += " AND es.start_date >= %s AND es.end_date <= %s"
                params.extend(date_range)
            
            base_query += " ORDER BY d.diagnosis_type, d.created_at DESC"
            
            cursor.execute(base_query, params)
            return cursor.fetchall()
            
        finally:
            cursor.close()
            conn.close()
    
    def get_patient_allergies(self, database: str, prn: str, date_range: tuple = None) -> List[Dict]:
        """Get all allergies for a patient"""
        conn = self.get_connection(database)
        cursor = conn.cursor(dictionary=True)
        
        try:
            base_query = """
            SELECT a.*, pe.extraction_session_id, es.start_date as session_start,
                   es.end_date as session_end, es.extracted_at, es.job_name
            FROM allergies a
            JOIN patient_extractions pe ON a.patient_extraction_id = pe.id
            JOIN extraction_sessions es ON pe.extraction_session_id = es.id
            WHERE pe.prn = %s
            """
            
            params = [prn]
            
            if date_range:
                base_query += " AND es.start_date >= %s AND es.end_date <= %s"
                params.extend(date_range)
            
            base_query += " ORDER BY a.allergy_type, a.created_at DESC"
            
            cursor.execute(base_query, params)
            return cursor.fetchall()
            
        finally:
            cursor.close()
            conn.close()
    
    def get_patient_health_concerns(self, database: str, prn: str, date_range: tuple = None) -> List[Dict]:
        """Get all health concerns for a patient"""
        conn = self.get_connection(database)
        cursor = conn.cursor(dictionary=True)
        
        try:
            base_query = """
            SELECT hc.*, pe.extraction_session_id, es.start_date as session_start,
                   es.end_date as session_end, es.extracted_at, es.job_name
            FROM health_concerns hc
            JOIN patient_extractions pe ON hc.patient_extraction_id = pe.id
            JOIN extraction_sessions es ON pe.extraction_session_id = es.id
            WHERE pe.prn = %s
            """
            
            params = [prn]
            
            if date_range:
                base_query += " AND es.start_date >= %s AND es.end_date <= %s"
                params.extend(date_range)
            
            base_query += " ORDER BY hc.concern_type, hc.created_at DESC"
            
            cursor.execute(base_query, params)
            return cursor.fetchall()
            
        finally:
            cursor.close()
            conn.close()
    
    def get_patient_conflicts(self, database: str, prn: str) -> List[Dict]:
        """Get all data conflicts for a patient"""
        conn = self.get_connection(database)
        cursor = conn.cursor(dictionary=True)
        
        try:
            query = """
            SELECT dc.*, p.patient_name,
                   es1.job_name as session1_name, es1.extracted_at as session1_time,
                   es2.job_name as session2_name, es2.extracted_at as session2_time
            FROM data_conflicts dc
            JOIN patients p ON dc.patient_id = p.id
            LEFT JOIN extraction_sessions es1 ON dc.extraction_session_id_1 = es1.id
            LEFT JOIN extraction_sessions es2 ON dc.extraction_session_id_2 = es2.id
            WHERE dc.prn = %s
            ORDER BY dc.detected_at DESC
            """
            
            cursor.execute(query, (prn,))
            return cursor.fetchall()
            
        finally:
            cursor.close()
            conn.close()
    
    def get_comprehensive_patient_data(self, provider: str, prn: str = None, 
                                     patient_name: str = None, date_range: tuple = None) -> Dict[str, Any]:
        """Get complete patient medical data"""
        database = self.get_provider_database(provider)
        
        # Get patient demographics first
        demographics = self.get_patient_demographics(database, prn, patient_name)
        if not demographics:
            return {'error': 'Patient not found'}
        
        patient_prn = demographics['prn']
        
        # Get all medical data
        result = {
            'patient_info': demographics,
            'extractions': self.get_patient_extractions(database, patient_prn),
            'medications': self.get_patient_medications(database, patient_prn, date_range),
            'diagnoses': self.get_patient_diagnoses(database, patient_prn, date_range),
            'allergies': self.get_patient_allergies(database, patient_prn, date_range),
            'health_concerns': self.get_patient_health_concerns(database, patient_prn, date_range),
            'conflicts': self.get_patient_conflicts(database, patient_prn),
            'summary': {
                'total_extractions': 0,
                'total_medications': 0,
                'total_diagnoses': 0,
                'total_allergies': 0,
                'total_health_concerns': 0,
                'total_conflicts': 0
            }
        }
        
        # Generate summary
        result['summary']['total_extractions'] = len(result['extractions'])
        result['summary']['total_medications'] = len(result['medications'])
        result['summary']['total_diagnoses'] = len(result['diagnoses'])
        result['summary']['total_allergies'] = len(result['allergies'])
        result['summary']['total_health_concerns'] = len(result['health_concerns'])
        result['summary']['total_conflicts'] = len(result['conflicts'])
        
        return result
    
    def list_patients(self, provider: str, limit: int = 50) -> List[Dict]:
        """List all patients for a provider"""
        database = self.get_provider_database(provider)
        conn = self.get_connection(database)
        cursor = conn.cursor(dictionary=True)
        
        try:
            query = """
            SELECT p.*, 
                   COUNT(DISTINCT pe.extraction_session_id) as total_extractions,
                   COUNT(DISTINCT m.id) as total_medications,
                   COUNT(DISTINCT d.id) as total_diagnoses,
                   COUNT(DISTINCT dc.id) as total_conflicts
            FROM patients p
            LEFT JOIN patient_extractions pe ON p.prn = pe.prn
            LEFT JOIN medications m ON pe.id = m.patient_extraction_id
            LEFT JOIN diagnoses d ON pe.id = d.patient_extraction_id
            LEFT JOIN data_conflicts dc ON p.prn = dc.prn
            GROUP BY p.id
            ORDER BY p.patient_name
            LIMIT %s
            """
            
            cursor.execute(query, (limit,))
            return cursor.fetchall()
            
        finally:
            cursor.close()
            conn.close()
    
    def get_provider_conflicts(self, provider: str) -> List[Dict]:
        """Get all conflicts for a provider"""
        database = self.get_provider_database(provider)
        conn = self.get_connection(database)
        cursor = conn.cursor(dictionary=True)
        
        try:
            query = """
            SELECT dc.*, p.patient_name,
                   es1.job_name as session1_name, es1.extracted_at as session1_time,
                   es2.job_name as session2_name, es2.extracted_at as session2_time
            FROM data_conflicts dc
            JOIN patients p ON dc.patient_id = p.id
            LEFT JOIN extraction_sessions es1 ON dc.extraction_session_id_1 = es1.id
            LEFT JOIN extraction_sessions es2 ON dc.extraction_session_id_2 = es2.id
            ORDER BY dc.detected_at DESC
            """
            
            cursor.execute(query)
            return cursor.fetchall()
            
        finally:
            cursor.close()
            conn.close()

def format_datetime(dt):
    """Format datetime for display"""
    if dt is None:
        return "N/A"
    if isinstance(dt, datetime):
        return dt.strftime("%Y-%m-%d %H:%M:%S")
    return str(dt)

def print_patient_summary(data: Dict[str, Any]):
    """Print formatted patient summary"""
    patient = data['patient_info']
    summary = data['summary']
    
    print(f"\n{'='*80}")
    print(f"PATIENT MEDICAL RECORD")
    print(f"{'='*80}")
    
    # Demographics
    print(f"📋 PATIENT INFORMATION:")
    print(f"   PRN: {patient['prn']}")
    print(f"   Name: {patient['patient_name']}")
    print(f"   DOB: {patient['date_of_birth']} (Age: {patient['age']})")
    print(f"   Gender: {patient['gender']}")
    print(f"   UUID: {patient['patient_uuid']}")
    
    # Summary statistics
    print(f"\n📊 MEDICAL DATA SUMMARY:")
    print(f"   Extraction Sessions: {summary['total_extractions']}")
    print(f"   Medications: {summary['total_medications']}")
    print(f"   Diagnoses: {summary['total_diagnoses']}")
    print(f"   Allergies: {summary['total_allergies']}")
    print(f"   Health Concerns: {summary['total_health_concerns']}")
    print(f"   Data Conflicts: {summary['total_conflicts']}")
    
    # Extraction sessions
    if data['extractions']:
        print(f"\n🔍 EXTRACTION SESSIONS:")
        for ext in data['extractions'][:5]:  # Show latest 5
            print(f"   • {ext['job_name']} ({ext['portal_name']})")
            print(f"     Target: {ext['filter_medication_name']}")
            print(f"     Date Range: {ext['filter_start_date']} to {ext['filter_stop_date']}")
            print(f"     Extracted: {format_datetime(ext['extracted_at'])}")
    
    # Medications by type
    if data['medications']:
        print(f"\n💊 MEDICATIONS:")
        for med_type in ['active', 'current', 'historical']:
            meds = [m for m in data['medications'] if m['medication_type'] == med_type]
            if meds:
                print(f"   {med_type.upper()} ({len(meds)}):")
                for med in meds[:3]:  # Show first 3 of each type
                    print(f"     • {med['medication_name']}")
                    if med['medication_strength']:
                        print(f"       Strength: {med['medication_strength']}")
                    if med['sig']:
                        print(f"       Sig: {med['sig'][:100]}...")
    
    # Diagnoses
    if data['diagnoses']:
        print(f"\n🏥 DIAGNOSES:")
        for diag_type in ['current', 'historical']:
            diags = [d for d in data['diagnoses'] if d['diagnosis_type'] == diag_type]
            if diags:
                print(f"   {diag_type.upper()} ({len(diags)}):")
                for diag in diags[:3]:  # Show first 3 of each type
                    print(f"     • {diag['diagnosis_text']}")
                    if diag['acuity']:
                        print(f"       Acuity: {diag['acuity']}")
    
    # Allergies
    if data['allergies']:
        print(f"\n⚠️ ALLERGIES ({len(data['allergies'])}):")
        for allergy in data['allergies'][:5]:
            print(f"   • {allergy['allergy_name']} ({allergy['allergy_type']})")
            if allergy['reaction']:
                print(f"     Reaction: {allergy['reaction']}")
    
    # Health concerns
    if data['health_concerns']:
        print(f"\n🩺 HEALTH CONCERNS ({len(data['health_concerns'])}):")
        for concern in data['health_concerns'][:3]:
            concern_text = concern['concern_text']
            if len(concern_text) > 100:
                concern_text = concern_text[:100] + "..."
            print(f"   • {concern_text}")
    
    # Conflicts
    if data['conflicts']:
        print(f"\n⚠️ DATA CONFLICTS ({len(data['conflicts'])}):")
        for conflict in data['conflicts']:
            print(f"   • {conflict['conflict_type']}: {conflict['conflict_description']}")
            print(f"     Severity: {conflict['severity']} | Status: {conflict['status']}")
            print(f"     Detected: {format_datetime(conflict['detected_at'])}")

def main():
    """Main CLI function"""
    parser = argparse.ArgumentParser(
        description="Patient Data Query System",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python patient_data_query.py --prn "MH167307" --provider "gary_wang"
  python patient_data_query.py --patient-name "Melissa" --provider "gary_wang" 
  python patient_data_query.py --provider "gary_wang" --list-patients
  python patient_data_query.py --provider "gary_wang" --conflicts
        """
    )
    
    parser.add_argument('--provider', required=True, help='Provider name')
    parser.add_argument('--prn', help='Patient Record Number')
    parser.add_argument('--patient-name', help='Patient name (partial match)')
    parser.add_argument('--date-start', help='Start date filter (YYYY-MM-DD)')
    parser.add_argument('--date-end', help='End date filter (YYYY-MM-DD)')
    parser.add_argument('--list-patients', action='store_true', help='List all patients')
    parser.add_argument('--conflicts', action='store_true', help='Show provider conflicts')
    parser.add_argument('--json', action='store_true', help='Output as JSON')
    parser.add_argument('--limit', type=int, default=50, help='Limit for patient list')
    
    args = parser.parse_args()
    
    if len(sys.argv) == 1:
        parser.print_help()
        return
    
    query_system = PatientDataQuery()
    
    try:
        # Build date range if provided
        date_range = None
        if args.date_start and args.date_end:
            date_range = (args.date_start, args.date_end)
        
        if args.list_patients:
            patients = query_system.list_patients(args.provider, args.limit)
            
            if args.json:
                print(json.dumps(patients, default=str, indent=2))
            else:
                print(f"\n📋 PATIENTS FOR PROVIDER: {args.provider}")
                print(f"{'='*80}")
                for patient in patients:
                    print(f"PRN: {patient['prn']:12} | {patient['patient_name']:30} | "
                          f"Extractions: {patient['total_extractions']:2} | "
                          f"Medications: {patient['total_medications']:3} | "
                          f"Conflicts: {patient['total_conflicts']:2}")
        
        elif args.conflicts:
            conflicts = query_system.get_provider_conflicts(args.provider)
            
            if args.json:
                print(json.dumps(conflicts, default=str, indent=2))
            else:
                print(f"\n⚠️ DATA CONFLICTS FOR PROVIDER: {args.provider}")
                print(f"{'='*80}")
                for conflict in conflicts:
                    print(f"PRN: {conflict['prn']} | Patient: {conflict['patient_name']}")
                    print(f"Type: {conflict['conflict_type']} | Severity: {conflict['severity']}")
                    print(f"Description: {conflict['conflict_description']}")
                    print(f"Detected: {format_datetime(conflict['detected_at'])}")
                    print(f"{'-'*40}")
        
        elif args.prn or args.patient_name:
            data = query_system.get_comprehensive_patient_data(
                args.provider, args.prn, args.patient_name, date_range
            )
            
            if 'error' in data:
                print(f"❌ Error: {data['error']}")
                return
            
            if args.json:
                print(json.dumps(data, default=str, indent=2))
            else:
                print_patient_summary(data)
        
        else:
            print("❌ Error: Please specify --prn, --patient-name, --list-patients, or --conflicts")
            parser.print_help()
    
    except mysql.connector.Error as e:
        print(f"❌ Database Error: {e}")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    main() 