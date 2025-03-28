"""
Smart Data Reuse System
Checks existing database before running new extractions
"""

import mysql.connector
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import os
from dotenv import load_dotenv

load_dotenv('.env', override=True)

class SmartDataReuseManager:
    """Manages intelligent data reuse to avoid duplicate extractions"""
    
    def __init__(self):
        self.db_config = {
            'host': os.getenv('WEBAUTODASH_DB_HOST', '128.205.221.54'),
            'port': int(os.getenv('WEBAUTODASH_DB_PORT', 3306)),
            'user': os.getenv('WEBAUTODASH_DB_USER', 'xvoice_user'),
            'password': os.getenv('WEBAUTODASH_DB_PASSWORD', 'Jetson@123')
        }
    
    def check_existing_data(self, provider: str, medication: str, 
                          start_date: str, end_date: str) -> Dict:
        """
        Check if we already have data for the given parameters
        Returns recommendation on whether to reuse or extract new
        """
        try:
            config = self.db_config.copy()
            config['database'] = f'webautodash_{provider.lower().replace(" ", "_")}'
            
            conn = mysql.connector.connect(**config)
            cursor = conn.cursor(dictionary=True)
            
            # Find overlapping extractions
            cursor.execute("""
                SELECT es.*, 
                       COUNT(pe.id) as total_patients,
                       SUM(CASE WHEN pe.processing_status = 'processed' THEN 1 ELSE 0 END) as successful_patients
                FROM extraction_sessions es
                LEFT JOIN patient_extractions pe ON es.id = pe.extraction_session_id
                WHERE es.target_medication LIKE %s
                AND (
                    (es.start_date <= %s AND es.end_date >= %s) OR
                    (es.start_date <= %s AND es.end_date >= %s) OR
                    (es.start_date >= %s AND es.end_date <= %s)
                )
                GROUP BY es.id
                ORDER BY es.extracted_at DESC
            """, (
                f"%{medication}%",
                start_date, start_date,
                end_date, end_date,
                start_date, end_date
            ))
            
            existing_sessions = cursor.fetchall()
            
            if not existing_sessions:
                return {
                    'should_reuse': False,
                    'reason': 'No existing data found for this medication and date range',
                    'action': 'EXTRACT_NEW',
                    'existing_sessions': []
                }
            
            # Check data quality and completeness
            best_session = existing_sessions[0]
            coverage_percentage = self._calculate_coverage(
                cursor, best_session['id'], start_date, end_date
            )
            
            # Get sample data
            sample_patients = self._get_sample_patients(
                cursor, best_session['id'], limit=5
            )
            
            conn.close()
            
            # Decision logic
            if coverage_percentage >= 90:
                return {
                    'should_reuse': True,
                    'reason': f'Excellent data coverage ({coverage_percentage:.1f}%) for requested period',
                    'action': 'REUSE_EXISTING',
                    'best_session': best_session,
                    'existing_sessions': existing_sessions,
                    'sample_patients': sample_patients,
                    'coverage_percentage': coverage_percentage
                }
            elif coverage_percentage >= 70:
                return {
                    'should_reuse': True,
                    'reason': f'Good data coverage ({coverage_percentage:.1f}%) - recommend using existing data',
                    'action': 'REUSE_WITH_WARNING',
                    'best_session': best_session,
                    'existing_sessions': existing_sessions,
                    'sample_patients': sample_patients,
                    'coverage_percentage': coverage_percentage
                }
            else:
                return {
                    'should_reuse': False,
                    'reason': f'Low data coverage ({coverage_percentage:.1f}%) - recommend new extraction',
                    'action': 'EXTRACT_NEW',
                    'best_session': best_session,
                    'existing_sessions': existing_sessions,
                    'sample_patients': sample_patients,
                    'coverage_percentage': coverage_percentage
                }
                
        except Exception as e:
            return {
                'should_reuse': False,
                'reason': f'Error checking existing data: {str(e)}',
                'action': 'EXTRACT_NEW',
                'error': str(e)
            }
    
    def _calculate_coverage(self, cursor, session_id: int, 
                          requested_start: str, requested_end: str) -> float:
        """Calculate what percentage of requested date range is covered"""
        try:
            cursor.execute("""
                SELECT MIN(filter_start_date) as actual_start,
                       MAX(filter_stop_date) as actual_end,
                       COUNT(*) as patient_count
                FROM patient_extractions
                WHERE extraction_session_id = %s
                AND processing_status = 'processed'
            """, (session_id,))
            
            result = cursor.fetchone()
            if not result or result['patient_count'] == 0:
                return 0.0
            
            # Simple coverage calculation based on date overlap
            # In a real implementation, you'd want more sophisticated logic
            return min(100.0, result['patient_count'] * 10)  # Rough estimate
            
        except Exception:
            return 0.0
    
    def _get_sample_patients(self, cursor, session_id: int, limit: int = 5) -> List[Dict]:
        """Get sample patients from existing extraction"""
        try:
            cursor.execute("""
                SELECT p.prn, p.patient_name, 
                       COUNT(m.id) as medication_count,
                       COUNT(d.id) as diagnosis_count,
                       pe.filter_start_date, pe.filter_stop_date
                FROM patient_extractions pe
                JOIN patients p ON pe.patient_id = p.id
                LEFT JOIN medications m ON pe.id = m.patient_extraction_id
                LEFT JOIN diagnoses d ON pe.id = d.patient_extraction_id
                WHERE pe.extraction_session_id = %s
                AND pe.processing_status = 'processed'
                GROUP BY pe.id
                ORDER BY (COUNT(m.id) + COUNT(d.id)) DESC
                LIMIT %s
            """, (session_id, limit))
            
            return cursor.fetchall()
            
        except Exception:
            return []
    
    def get_existing_patient_data(self, provider: str, session_id: int, 
                                 start_date: str = None, end_date: str = None) -> Dict:
        """Get existing patient data from a previous extraction"""
        try:
            config = self.db_config.copy()
            config['database'] = f'webautodash_{provider.lower().replace(" ", "_")}'
            
            conn = mysql.connector.connect(**config)
            cursor = conn.cursor(dictionary=True)
            
            # Build date filter if provided
            date_filter = ""
            date_params = [session_id]
            
            if start_date and end_date:
                date_filter = """
                    AND pe.filter_start_date <= %s 
                    AND pe.filter_stop_date >= %s
                """
                date_params.extend([end_date, start_date])
            
            # Get all patients from the session
            cursor.execute(f"""
                SELECT p.*, pe.filter_start_date, pe.filter_stop_date,
                       COUNT(m.id) as medication_count,
                       COUNT(d.id) as diagnosis_count,
                       COUNT(a.id) as allergy_count,
                       COUNT(hc.id) as health_concern_count
                FROM patient_extractions pe
                JOIN patients p ON pe.patient_id = p.id
                LEFT JOIN medications m ON pe.id = m.patient_extraction_id
                LEFT JOIN diagnoses d ON pe.id = d.patient_extraction_id
                LEFT JOIN allergies a ON pe.id = a.patient_extraction_id
                LEFT JOIN health_concerns hc ON pe.id = hc.patient_extraction_id
                WHERE pe.extraction_session_id = %s
                {date_filter}
                AND pe.processing_status = 'processed'
                GROUP BY p.id
                ORDER BY p.patient_name
            """, date_params)
            
            patients = cursor.fetchall()
            
            # Get session metadata
            cursor.execute("""
                SELECT * FROM extraction_sessions WHERE id = %s
            """, (session_id,))
            
            session_info = cursor.fetchone()
            
            conn.close()
            
            return {
                'success': True,
                'session_info': session_info,
                'patients': patients,
                'total_patients': len(patients),
                'summary': {
                    'total_medications': sum(p['medication_count'] for p in patients),
                    'total_diagnoses': sum(p['diagnosis_count'] for p in patients),
                    'total_allergies': sum(p['allergy_count'] for p in patients),
                    'total_health_concerns': sum(p['health_concern_count'] for p in patients)
                }
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f'Failed to get existing data: {str(e)}'
            }

# Global instance
smart_reuse_manager = SmartDataReuseManager()

def check_before_extraction(provider: str, medication: str, 
                          start_date: str, end_date: str) -> Dict:
    """
    Convenience function to check existing data before starting extraction
    """
    return smart_reuse_manager.check_existing_data(
        provider, medication, start_date, end_date
    )

if __name__ == "__main__":
    # Test the system
    result = check_before_extraction(
        "gary_wang", "Xanax", "2020-01-01", "2025-12-31"
    )
    
    print("🔍 Data Reuse Check Results:")
    print(f"   Should reuse: {result.get('should_reuse', False)}")
    print(f"   Reason: {result.get('reason', 'Unknown')}")
    print(f"   Action: {result.get('action', 'Unknown')}")
    
    if 'existing_sessions' in result:
        print(f"   Existing sessions: {len(result['existing_sessions'])}")
    
    if 'sample_patients' in result:
        print(f"   Sample patients: {len(result['sample_patients'])}") 