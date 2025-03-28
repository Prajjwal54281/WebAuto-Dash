#!/usr/bin/env python3

"""
Test script to verify the updated Patient Data API
"""

import requests
import json
from routes.patient_data_api import get_db_connection

def test_direct_database():
    """Test direct database connection"""
    print("🔍 Testing Direct Database Connection...")
    try:
        conn = get_db_connection('gary_wang')
        cursor = conn.cursor(dictionary=True)
        
        # Test extraction sessions
        cursor.execute("SELECT COUNT(*) as count FROM extraction_sessions")
        sessions = cursor.fetchone()['count']
        print(f"✅ Extraction sessions: {sessions}")
        
        # Test patient records
        cursor.execute("SELECT COUNT(*) as count FROM comprehensive_patient_records")
        patients = cursor.fetchone()['count']
        print(f"✅ Patient records: {patients}")
        
        # Get sample data
        if sessions > 0:
            cursor.execute("SELECT id, job_name, target_medication, extracted_at FROM extraction_sessions LIMIT 3")
            sample_sessions = cursor.fetchall()
            print("📋 Sample sessions:")
            for session in sample_sessions:
                print(f"  - ID {session['id']}: {session['job_name']} | {session['target_medication']} | {session['extracted_at']}")
        
        if patients > 0:
            cursor.execute("SELECT patient_name, target_medication, date_range_start FROM comprehensive_patient_records LIMIT 3")
            sample_patients = cursor.fetchall()
            print("📋 Sample patients:")
            for patient in sample_patients:
                print(f"  - {patient['patient_name']} | {patient['target_medication']} | {patient['date_range_start']}")
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Database test failed: {e}")
        return False

def test_api_endpoints():
    """Test API endpoints"""
    print("\n🌐 Testing API Endpoints...")
    base_url = "http://localhost:5005/api/patient-data"
    
    # Test health endpoint
    try:
        response = requests.get(f"{base_url}/health")
        if response.status_code == 200:
            print("✅ Health endpoint: OK")
        else:
            print(f"❌ Health endpoint failed: {response.status_code}")
    except Exception as e:
        print(f"❌ Health endpoint error: {e}")
    
    # Clear cache first
    try:
        requests.post(f"{base_url}/cache/clear")
        print("🧹 Cache cleared")
    except:
        pass
    
    # Test providers endpoint
    try:
        response = requests.get(f"{base_url}/providers")
        if response.status_code == 200:
            data = response.json()
            print("✅ Providers endpoint: OK")
            for provider in data.get('data', []):
                print(f"  - {provider['name']}: {provider.get('sessions', 0)} sessions, {provider.get('patients', 0)} patients")
                if 'error' in provider:
                    print(f"    ⚠️  Error: {provider['error']}")
        else:
            print(f"❌ Providers endpoint failed: {response.status_code}")
    except Exception as e:
        print(f"❌ Providers endpoint error: {e}")
    
    # Test stats endpoint
    try:
        response = requests.get(f"{base_url}/provider/gary_wang/stats")
        if response.status_code == 200:
            data = response.json()
            print("✅ Stats endpoint: OK")
            if data['status'] == 'success':
                totals = data['data']['totals']
                print(f"  - Sessions: {totals['sessions']}")
                print(f"  - Patients: {totals['patients']}")
                print(f"  - Medications: {totals['medications']}")
        else:
            print(f"❌ Stats endpoint failed: {response.status_code}")
    except Exception as e:
        print(f"❌ Stats endpoint error: {e}")

if __name__ == "__main__":
    print("🧪 Testing Updated Patient Data API\n")
    
    if test_direct_database():
        test_api_endpoints()
    
    print("\n✅ Test completed!") 