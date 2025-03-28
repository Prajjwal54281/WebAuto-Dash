"""
Comprehensive Patient Data Query Tool
Query comprehensive patient records organized by date ranges with complete medical data
"""

import json
import logging
import argparse
from datetime import datetime
from typing import Dict, List, Any, Optional
from db_connection_provider import get_provider_connection

logger = logging.getLogger(__name__)

class ComprehensivePatientQuery:
    """Query tool for comprehensive patient records organized by date ranges"""
    
    def __init__(self):
        self.supported_providers = self._get_available_providers()
    
    def _get_available_providers(self) -> List[str]:
        """Get list of available providers from database"""
        try:
            from db_connection_provider import provider_db_manager
            providers = provider_db_manager.list_providers()
            return [p['provider_name'] for p in providers]
        except Exception as e:
            logger.error(f"Error getting providers: {e}")
            return []
    
    def get_patient_comprehensive_records(self, prn: str, provider_name: str, 
                                        target_medication: str = None,
                                        date_start: str = None, date_end: str = None) -> List[Dict]:
        """
        Get comprehensive patient records for a specific PRN
        
        Args:
            prn: Patient Record Number
            provider_name: Provider name
            target_medication: Optional medication filter
            date_start: Optional start date filter (YYYY-MM-DD)
            date_end: Optional end date filter (YYYY-MM-DD)
            
        Returns:
            List of comprehensive patient records
        """
        try:
            conn = get_provider_connection(provider_name)
            cursor = conn.cursor(dictionary=True)
            
            # Build query with optional filters
            query = """
                SELECT cpr.*, 
                       es.job_name, es.portal_name, es.extracted_at,
                       es.results_filename
                FROM comprehensive_patient_records cpr
                JOIN extraction_sessions es ON cpr.extraction_session_id = es.id
                WHERE cpr.prn = %s
            """
            params = [prn]
            
            # Add medication filter
            if target_medication:
                query += " AND cpr.target_medication = %s"
                params.append(target_medication)
            
            # Add date range filters
            if date_start:
                query += " AND cpr.date_range_end >= %s"
                params.append(date_start)
            
            if date_end:
                query += " AND cpr.date_range_start <= %s"
                params.append(date_end)
            
            query += " ORDER BY cpr.date_range_start DESC, cpr.created_at DESC"
            
            cursor.execute(query, params)
            results = cursor.fetchall()
            
            # Parse JSON fields
            for record in results:
                record['all_medications'] = json.loads(record['all_medications'] or '[]')
                record['all_diagnoses'] = json.loads(record['all_diagnoses'] or '[]')
                record['all_allergies'] = json.loads(record['all_allergies'] or '[]')
                record['all_health_concerns'] = json.loads(record['all_health_concerns'] or '[]')
            
            return results
            
        except Exception as e:
            logger.error(f"Error getting comprehensive records for PRN {prn}: {e}")
            return []
        finally:
            if conn.is_connected():
                cursor.close()
                conn.close()
    
    def get_patient_by_name(self, patient_name: str, provider_name: str) -> List[Dict]:
        """Get comprehensive records by patient name"""
        try:
            conn = get_provider_connection(provider_name)
            cursor = conn.cursor(dictionary=True)
            
            query = """
                SELECT cpr.*, 
                       es.job_name, es.portal_name, es.extracted_at,
                       es.results_filename
                FROM comprehensive_patient_records cpr
                JOIN extraction_sessions es ON cpr.extraction_session_id = es.id
                WHERE cpr.patient_name LIKE %s
                ORDER BY cpr.patient_name, cpr.date_range_start DESC
            """
            
            cursor.execute(query, (f"%{patient_name}%",))
            results = cursor.fetchall()
            
            # Parse JSON fields
            for record in results:
                record['all_medications'] = json.loads(record['all_medications'] or '[]')
                record['all_diagnoses'] = json.loads(record['all_diagnoses'] or '[]')
                record['all_allergies'] = json.loads(record['all_allergies'] or '[]')
                record['all_health_concerns'] = json.loads(record['all_health_concerns'] or '[]')
            
            return results
            
        except Exception as e:
            logger.error(f"Error getting comprehensive records for patient {patient_name}: {e}")
            return []
        finally:
            if conn.is_connected():
                cursor.close()
                conn.close()
    
    def list_all_comprehensive_patients(self, provider_name: str, 
                                      target_medication: str = None) -> List[Dict]:
        """List all patients with comprehensive records"""
        try:
            conn = get_provider_connection(provider_name)
            cursor = conn.cursor(dictionary=True)
            
            query = """
                SELECT prn, patient_name, 
                       MIN(date_range_start) as earliest_date,
                       MAX(date_range_end) as latest_date,
                       COUNT(*) as total_records,
                       GROUP_CONCAT(DISTINCT target_medication) as medications,
                       MAX(created_at) as last_updated
                FROM comprehensive_patient_records
            """
            params = []
            
            if target_medication:
                query += " WHERE target_medication = %s"
                params.append(target_medication)
            
            query += """
                GROUP BY prn, patient_name
                ORDER BY patient_name
            """
            
            cursor.execute(query, params)
            return cursor.fetchall()
            
        except Exception as e:
            logger.error(f"Error listing comprehensive patients: {e}")
            return []
        finally:
            if conn.is_connected():
                cursor.close()
                conn.close()
    
    def get_date_range_conflicts(self, provider_name: str) -> List[Dict]:
        """Get comprehensive records with conflicts for same date ranges"""
        try:
            conn = get_provider_connection(provider_name)
            cursor = conn.cursor(dictionary=True)
            
            query = """
                SELECT cpr1.prn, cpr1.patient_name,
                       cpr1.date_range_start, cpr1.date_range_end,
                       cpr1.target_medication,
                       COUNT(*) as conflict_count,
                       GROUP_CONCAT(cpr1.id) as record_ids,
                       GROUP_CONCAT(cpr1.data_checksum) as checksums
                FROM comprehensive_patient_records cpr1
                WHERE cpr1.record_status = 'conflict'
                OR cpr1.prn IN (
                    SELECT prn FROM comprehensive_patient_records cpr2 
                    WHERE cpr2.prn = cpr1.prn 
                    AND cpr2.date_range_start = cpr1.date_range_start
                    AND cpr2.date_range_end = cpr1.date_range_end
                    AND cpr2.target_medication = cpr1.target_medication
                    AND cpr2.id != cpr1.id
                )
                GROUP BY cpr1.prn, cpr1.date_range_start, cpr1.date_range_end, cpr1.target_medication
                HAVING COUNT(*) > 1
                ORDER BY cpr1.patient_name, cpr1.date_range_start
            """
            
            cursor.execute(query)
            return cursor.fetchall()
            
        except Exception as e:
            logger.error(f"Error getting date range conflicts: {e}")
            return []
        finally:
            if conn.is_connected():
                cursor.close()
                conn.close()
    
    def get_comprehensive_statistics(self, provider_name: str) -> Dict[str, Any]:
        """Get statistics about comprehensive records"""
        try:
            conn = get_provider_connection(provider_name)
            cursor = conn.cursor(dictionary=True)
            
            stats = {}
            
            # Total patients and records
            cursor.execute("""
                SELECT 
                    COUNT(DISTINCT prn) as total_patients,
                    COUNT(*) as total_records,
                    COUNT(CASE WHEN record_status = 'active' THEN 1 END) as active_records,
                    COUNT(CASE WHEN record_status = 'conflict' THEN 1 END) as conflict_records,
                    COUNT(CASE WHEN record_status = 'superseded' THEN 1 END) as superseded_records
                FROM comprehensive_patient_records
            """)
            stats.update(cursor.fetchone())
            
            # Date range coverage
            cursor.execute("""
                SELECT 
                    MIN(date_range_start) as earliest_date,
                    MAX(date_range_end) as latest_date,
                    COUNT(DISTINCT target_medication) as unique_medications
                FROM comprehensive_patient_records
            """)
            stats.update(cursor.fetchone())
            
            # Most common medications
            cursor.execute("""
                SELECT target_medication, COUNT(*) as record_count
                FROM comprehensive_patient_records
                GROUP BY target_medication
                ORDER BY record_count DESC
                LIMIT 10
            """)
            stats['top_medications'] = cursor.fetchall()
            
            return stats
            
        except Exception as e:
            logger.error(f"Error getting comprehensive statistics: {e}")
            return {}
        finally:
            if conn.is_connected():
                cursor.close()
                conn.close()

def main():
    """Command line interface for comprehensive patient queries"""
    parser = argparse.ArgumentParser(description='Query comprehensive patient records')
    parser.add_argument('--provider', required=True, help='Provider name')
    parser.add_argument('--prn', help='Patient Record Number')
    parser.add_argument('--patient-name', help='Patient name (partial match)')
    parser.add_argument('--medication', help='Target medication filter')
    parser.add_argument('--date-start', help='Start date filter (YYYY-MM-DD)')
    parser.add_argument('--date-end', help='End date filter (YYYY-MM-DD)')
    parser.add_argument('--list-patients', action='store_true', help='List all patients')
    parser.add_argument('--conflicts', action='store_true', help='Show date range conflicts')
    parser.add_argument('--stats', action='store_true', help='Show statistics')
    parser.add_argument('--json', action='store_true', help='Output in JSON format')
    
    args = parser.parse_args()
    
    query_tool = ComprehensivePatientQuery()
    
    if args.stats:
        # Show statistics
        stats = query_tool.get_comprehensive_statistics(args.provider)
        if args.json:
            print(json.dumps(stats, indent=2, default=str))
        else:
            print(f"\n📊 Comprehensive Records Statistics for {args.provider}")
            print(f"{'='*50}")
            print(f"Total Patients: {stats.get('total_patients', 0)}")
            print(f"Total Records: {stats.get('total_records', 0)}")
            print(f"Active Records: {stats.get('active_records', 0)}")
            print(f"Conflict Records: {stats.get('conflict_records', 0)}")
            print(f"Superseded Records: {stats.get('superseded_records', 0)}")
            print(f"Date Range: {stats.get('earliest_date')} to {stats.get('latest_date')}")
            print(f"Unique Medications: {stats.get('unique_medications', 0)}")
            
            print(f"\n🏆 Top Medications:")
            for med in stats.get('top_medications', [])[:5]:
                print(f"  - {med['target_medication']}: {med['record_count']} records")
    
    elif args.conflicts:
        # Show conflicts
        conflicts = query_tool.get_date_range_conflicts(args.provider)
        if args.json:
            print(json.dumps(conflicts, indent=2, default=str))
        else:
            print(f"\n⚠️  Date Range Conflicts for {args.provider}")
            print(f"{'='*60}")
            if not conflicts:
                print("No conflicts found! ✅")
            else:
                for conflict in conflicts:
                    print(f"\nPatient: {conflict['patient_name']} (PRN: {conflict['prn']})")
                    print(f"Date Range: {conflict['date_range_start']} to {conflict['date_range_end']}")
                    print(f"Medication: {conflict['target_medication']}")
                    print(f"Conflict Count: {conflict['conflict_count']}")
                    print(f"Record IDs: {conflict['record_ids']}")
    
    elif args.list_patients:
        # List patients
        patients = query_tool.list_all_comprehensive_patients(args.provider, args.medication)
        if args.json:
            print(json.dumps(patients, indent=2, default=str))
        else:
            print(f"\n👥 Comprehensive Patient List for {args.provider}")
            print(f"{'='*70}")
            for patient in patients:
                print(f"\nPRN: {patient['prn']}")
                print(f"Name: {patient['patient_name']}")
                print(f"Date Range: {patient['earliest_date']} to {patient['latest_date']}")
                print(f"Records: {patient['total_records']}")
                print(f"Medications: {patient['medications']}")
                print(f"Last Updated: {patient['last_updated']}")
    
    elif args.prn:
        # Query by PRN
        records = query_tool.get_patient_comprehensive_records(
            args.prn, args.provider, args.medication, args.date_start, args.date_end
        )
        if args.json:
            print(json.dumps(records, indent=2, default=str))
        else:
            print(f"\n🏥 Comprehensive Records for PRN: {args.prn}")
            print(f"{'='*60}")
            if not records:
                print("No records found!")
            else:
                for record in records:
                    print(f"\nRecord ID: {record['id']}")
                    print(f"Patient: {record['patient_name']}")
                    print(f"Date Range: {record['date_range_start']} to {record['date_range_end']}")
                    print(f"Medication: {record['target_medication']}")
                    print(f"Status: {record['record_status']}")
                    print(f"Extracted: {record['extracted_at']}")
                    
                    print(f"\n  📋 Medications ({len(record['all_medications'])})")
                    for i, med in enumerate(record['all_medications'][:5]):
                        print(f"    {i+1}. {med.get('medication_name', 'Unknown')}")
                    if len(record['all_medications']) > 5:
                        print(f"    ... and {len(record['all_medications']) - 5} more")
                    
                    print(f"\n  🩺 Diagnoses ({len(record['all_diagnoses'])})")
                    for i, diag in enumerate(record['all_diagnoses'][:3]):
                        print(f"    {i+1}. {diag.get('diagnosis_text', 'Unknown')}")
                    if len(record['all_diagnoses']) > 3:
                        print(f"    ... and {len(record['all_diagnoses']) - 3} more")
                    
                    print(f"\n  🚨 Allergies ({len(record['all_allergies'])})")
                    for i, allergy in enumerate(record['all_allergies'][:3]):
                        print(f"    {i+1}. {allergy}")
                    if len(record['all_allergies']) > 3:
                        print(f"    ... and {len(record['all_allergies']) - 3} more")
    
    elif args.patient_name:
        # Query by name
        records = query_tool.get_patient_by_name(args.patient_name, args.provider)
        if args.json:
            print(json.dumps(records, indent=2, default=str))
        else:
            print(f"\n🔍 Search Results for '{args.patient_name}'")
            print(f"{'='*50}")
            if not records:
                print("No patients found!")
            else:
                for record in records:
                    print(f"\nPRN: {record['prn']} | Name: {record['patient_name']}")
                    print(f"Date Range: {record['date_range_start']} to {record['date_range_end']}")
                    print(f"Medication: {record['target_medication']} | Status: {record['record_status']}")
    
    else:
        parser.print_help()
        print(f"\nAvailable providers: {', '.join(query_tool.supported_providers)}")

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main() 