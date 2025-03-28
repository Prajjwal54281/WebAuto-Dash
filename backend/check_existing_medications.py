#!/usr/bin/env python3
"""
Check what medications exist in the database for Gary Wang
"""

import mysql.connector
import os
from dotenv import load_dotenv

load_dotenv('.env', override=True)

def main():
    print("🔍 Checking existing medications for Gary Wang...")
    print("=" * 50)
    
    try:
        # Connect to Gary Wang's database
        conn = mysql.connector.connect(
            host=os.getenv('WEBAUTODASH_DB_HOST', '128.205.221.54'),
            port=int(os.getenv('WEBAUTODASH_DB_PORT', 3306)),
            user=os.getenv('WEBAUTODASH_DB_USER', 'xvoice_user'),
            password=os.getenv('WEBAUTODASH_DB_PASSWORD', 'Jetson@123'),
            database='webautodash_gary_wang'
        )
        
        cursor = conn.cursor(dictionary=True)
        
        # Check extraction sessions
        print("📊 Extraction Sessions:")
        cursor.execute("""
            SELECT id, target_medication, start_date, end_date, extracted_at, total_patients_found
            FROM extraction_sessions
            ORDER BY extracted_at DESC
            LIMIT 10
        """)
        
        sessions = cursor.fetchall()
        for session in sessions:
            print(f"   Session {session['id']}: {session['target_medication']}")
            print(f"      📅 {session['start_date']} to {session['end_date']}")
            print(f"      👥 {session['total_patients_found']} patients")
            print(f"      🕒 {session['extracted_at']}")
            print()
        
        # Check unique medications
        print("💊 Unique Medications Found:")
        cursor.execute("""
            SELECT DISTINCT target_medication, COUNT(*) as session_count
            FROM extraction_sessions
            GROUP BY target_medication
            ORDER BY session_count DESC
        """)
        
        medications = cursor.fetchall()
        for med in medications:
            print(f"   • {med['target_medication']} ({med['session_count']} sessions)")
        
        # Check for Alprazolam or Xanax specifically
        print("\n🔍 Checking for Alprazolam/Xanax specifically:")
        cursor.execute("""
            SELECT id, target_medication, start_date, end_date, total_patients_found
            FROM extraction_sessions
            WHERE target_medication LIKE '%alprazolam%' 
               OR target_medication LIKE '%xanax%'
               OR target_medication LIKE '%Alprazolam%'
               OR target_medication LIKE '%Xanax%'
            ORDER BY extracted_at DESC
        """)
        
        alprazolam_sessions = cursor.fetchall()
        if alprazolam_sessions:
            print("✅ Found Alprazolam/Xanax sessions:")
            for session in alprazolam_sessions:
                print(f"   Session {session['id']}: {session['target_medication']}")
                print(f"      📅 {session['start_date']} to {session['end_date']}")
                print(f"      👥 {session['total_patients_found']} patients")
        else:
            print("❌ No Alprazolam/Xanax sessions found")
        
        # Check date overlap for 2000-2025 range
        print("\n📅 Checking for date overlap with 2000-2025:")
        cursor.execute("""
            SELECT id, target_medication, start_date, end_date, total_patients_found
            FROM extraction_sessions
            WHERE (start_date <= '2025-06-28' AND end_date >= '2000-01-01')
               OR (start_date >= '2000-01-01' AND end_date <= '2025-06-28')
            ORDER BY extracted_at DESC
        """)
        
        overlapping_sessions = cursor.fetchall()
        if overlapping_sessions:
            print("✅ Found sessions with date overlap:")
            for session in overlapping_sessions:
                print(f"   Session {session['id']}: {session['target_medication']}")
                print(f"      📅 {session['start_date']} to {session['end_date']}")
                print(f"      👥 {session['total_patients_found']} patients")
        else:
            print("❌ No sessions found with date overlap")
        
        conn.close()
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main() 