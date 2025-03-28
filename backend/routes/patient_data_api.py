"""
Optimized Patient Data API with Caching and Smart Data Reuse
"""

from flask import Blueprint, request, jsonify, current_app
from datetime import datetime, timedelta
import json
import os
from typing import Dict, List, Optional, Any
import mysql.connector
from dotenv import load_dotenv

load_dotenv('.env', override=True)

patient_data_bp = Blueprint('patient_data', __name__)

class PatientDataCache:
    """Simple in-memory cache for patient data"""
    def __init__(self):
        self.cache = {}
        self.cache_ttl = 300  # 5 minutes
    
    def get(self, key: str):
        if key in self.cache:
            data, timestamp = self.cache[key]
            if datetime.now() - timestamp < timedelta(seconds=self.cache_ttl):
                return data
            else:
                del self.cache[key]
        return None
    
    def set(self, key: str, data: Any):
        self.cache[key] = (data, datetime.now())

# Global cache instance
cache = PatientDataCache()

def get_db_connection(provider: str):
    """Get database connection for provider"""
    return mysql.connector.connect(
        host=os.getenv('WEBAUTODASH_DB_HOST', '128.205.221.54'),
        port=int(os.getenv('WEBAUTODASH_DB_PORT', 3306)),
        user=os.getenv('WEBAUTODASH_DB_USER', 'xvoice_user'),
        password=os.getenv('WEBAUTODASH_DB_PASSWORD', 'Jetson@123'),
        database=f'webautodash_{provider}'
    )

@patient_data_bp.route('/providers', methods=['GET'])
def get_providers():
    """Get list of all providers (fast, cached)"""
    cache_key = "all_providers"
    cached_data = cache.get(cache_key)
    if cached_data:
        return jsonify({"status": "success", "data": cached_data, "cached": True})
    
    try:
        # Get list of databases that match webautodash_* pattern
        temp_conn = mysql.connector.connect(
            host=os.getenv('WEBAUTODASH_DB_HOST', '128.205.221.54'),
            port=int(os.getenv('WEBAUTODASH_DB_PORT', 3306)),
            user=os.getenv('WEBAUTODASH_DB_USER', 'xvoice_user'),
            password=os.getenv('WEBAUTODASH_DB_PASSWORD', 'Jetson@123')
        )
        
        cursor = temp_conn.cursor()
        cursor.execute("SHOW DATABASES LIKE 'webautodash_%'")
        databases = [db[0].replace('webautodash_', '') for db in cursor.fetchall()]
        
        providers_data = []
        for provider in databases:
            try:
                conn = get_db_connection(provider)
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM extraction_sessions")
                session_count = cursor.fetchone()[0]
                
                cursor.execute("SELECT COUNT(*) FROM comprehensive_patient_records")
                patient_count = cursor.fetchone()[0]
                
                providers_data.append({
                    "name": provider,
                    "sessions": session_count,
                    "patients": patient_count
                })
                conn.close()
            except Exception as e:
                print(f"Error getting stats for provider {provider}: {e}")
                providers_data.append({
                    "name": provider,
                    "sessions": 0,
                    "patients": 0,
                    "error": str(e)
                })
        
        cache.set(cache_key, providers_data)
        temp_conn.close()
        
        return jsonify({"status": "success", "data": providers_data, "cached": False})
        
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@patient_data_bp.route('/provider/<provider>/sessions', methods=['GET'])
def get_provider_sessions(provider: str):
    """Get paginated sessions for a provider"""
    page = int(request.args.get('page', 1))
    per_page = int(request.args.get('per_page', 20))
    offset = (page - 1) * per_page
    
    cache_key = f"sessions_{provider}_{page}_{per_page}"
    cached_data = cache.get(cache_key)
    if cached_data:
        return jsonify({"status": "success", "data": cached_data, "cached": True})
    
    try:
        conn = get_db_connection(provider)
        cursor = conn.cursor(dictionary=True)
        
        # Get total count
        cursor.execute("SELECT COUNT(*) as total FROM extraction_sessions")
        total = cursor.fetchone()['total']
        
        # Get paginated sessions
        cursor.execute("""
            SELECT id as session_id, job_name as doctor_name, target_medication as medication_name, 
                   start_date, end_date, extracted_at as session_date, total_patients_found as total_patients_extracted, 
                   'completed' as status
            FROM extraction_sessions 
            ORDER BY extracted_at DESC 
            LIMIT %s OFFSET %s
        """, (per_page, offset))
        
        sessions = cursor.fetchall()
        
        result = {
            "sessions": sessions,
            "pagination": {
                "page": page,
                "per_page": per_page,
                "total": total,
                "pages": (total + per_page - 1) // per_page
            }
        }
        
        cache.set(cache_key, result)
        conn.close()
        
        return jsonify({"status": "success", "data": result, "cached": False})
        
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@patient_data_bp.route('/provider/<provider>/patients', methods=['GET'])
def get_provider_patients(provider: str):
    """Get paginated patients for a provider"""
    page = int(request.args.get('page', 1))
    per_page = int(request.args.get('per_page', 50))
    session_id = request.args.get('session_id')
    medication = request.args.get('medication')
    
    offset = (page - 1) * per_page
    
    cache_key = f"patients_{provider}_{page}_{per_page}_{session_id}_{medication}"
    cached_data = cache.get(cache_key)
    if cached_data:
        return jsonify({"status": "success", "data": cached_data, "cached": True})
    
    try:
        conn = get_db_connection(provider)
        cursor = conn.cursor(dictionary=True)
        
        # Build query based on filters
        where_conditions = []
        params = []
        
        if session_id:
            where_conditions.append("cpr.extraction_session_id = %s")
            params.append(session_id)
        
        if medication:
            where_conditions.append("cpr.target_medication LIKE %s")
            params.append(f"%{medication}%")
        
        where_clause = "WHERE " + " AND ".join(where_conditions) if where_conditions else ""
        
        # Get total count
        count_query = f"""
            SELECT COUNT(*) as total 
            FROM comprehensive_patient_records cpr 
            JOIN extraction_sessions es ON cpr.extraction_session_id = es.id 
            {where_clause}
        """
        cursor.execute(count_query, params)
        total = cursor.fetchone()['total']
        
        # Get paginated patients
        query = f"""
            SELECT cpr.patient_name, cpr.date_of_birth as dob, cpr.target_medication as medication_name, 
                   cpr.date_range_start as visit_date, cpr.all_medications, cpr.all_diagnoses, 
                   cpr.all_allergies, es.job_name as doctor_name, es.extracted_at as session_date,
                   cpr.gender, cpr.age
            FROM comprehensive_patient_records cpr 
            JOIN extraction_sessions es ON cpr.extraction_session_id = es.id 
            {where_clause}
            ORDER BY cpr.date_range_start DESC 
            LIMIT %s OFFSET %s
        """
        
        cursor.execute(query, params + [per_page, offset])
        patients = cursor.fetchall()
        
        result = {
            "patients": patients,
            "pagination": {
                "page": page,
                "per_page": per_page,
                "total": total,
                "pages": (total + per_page - 1) // per_page
            },
            "filters": {
                "session_id": session_id,
                "medication": medication
            }
        }
        
        cache.set(cache_key, result)
        conn.close()
        
        return jsonify({"status": "success", "data": result, "cached": False})
        
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@patient_data_bp.route('/provider/<provider>/check-existing', methods=['POST'])
def check_existing_data(provider: str):
    """Check if data already exists for given parameters"""
    try:
        data = request.get_json()
        medication = data.get('medication')
        start_date = data.get('start_date')
        end_date = data.get('end_date')
        
        # Import smart data reuse system
        import sys
        sys.path.append('..')
        from smart_data_reuse import smart_reuse_manager
        
        result = smart_reuse_manager.check_existing_data(provider, medication, start_date, end_date)
        return jsonify({"status": "success", "data": result})
        
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@patient_data_bp.route('/provider/<provider>/stats', methods=['GET'])
def get_provider_stats(provider: str):
    """Get quick stats for a provider"""
    cache_key = f"stats_{provider}"
    cached_data = cache.get(cache_key)
    if cached_data:
        return jsonify({"status": "success", "data": cached_data, "cached": True})
    
    try:
        conn = get_db_connection(provider)
        cursor = conn.cursor(dictionary=True)
        
        # Get basic stats
        cursor.execute("SELECT COUNT(*) as total_sessions FROM extraction_sessions")
        sessions = cursor.fetchone()['total_sessions']
        
        cursor.execute("SELECT COUNT(*) as total_patients FROM comprehensive_patient_records")
        patients = cursor.fetchone()['total_patients']
        
        cursor.execute("SELECT COUNT(DISTINCT target_medication) as unique_medications FROM comprehensive_patient_records")
        medications = cursor.fetchone()['unique_medications']
        
        cursor.execute("""
            SELECT target_medication as medication_name, COUNT(*) as count 
            FROM comprehensive_patient_records 
            GROUP BY target_medication 
            ORDER BY count DESC 
            LIMIT 5
        """)
        top_medications = cursor.fetchall()
        
        cursor.execute("""
            SELECT DATE(extracted_at) as date, COUNT(*) as sessions 
            FROM extraction_sessions 
            WHERE extracted_at >= DATE_SUB(NOW(), INTERVAL 30 DAY)
            GROUP BY DATE(extracted_at) 
            ORDER BY date DESC
        """)
        recent_activity = cursor.fetchall()
        
        result = {
            "totals": {
                "sessions": sessions,
                "patients": patients,
                "medications": medications
            },
            "top_medications": top_medications,
            "recent_activity": recent_activity
        }
        
        cache.set(cache_key, result)
        conn.close()
        
        return jsonify({"status": "success", "data": result, "cached": False})
        
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@patient_data_bp.route('/cache/clear', methods=['POST'])
def clear_cache():
    """Clear the cache (admin function)"""
    cache.cache.clear()
    return jsonify({"status": "success", "message": "Cache cleared"})

@patient_data_bp.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        "status": "success", 
        "service": "Patient Data API",
        "timestamp": datetime.now().isoformat(),
        "cache_size": len(cache.cache)
    }) 