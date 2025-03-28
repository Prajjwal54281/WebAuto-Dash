#!/usr/bin/env python3
"""
WebAutoDash Database Cleanup Script
==================================
This script provides options to clean up provider databases:
1. Clean all data from all provider databases (keep structure)
2. Drop and recreate all provider databases
3. Clean specific provider data
4. Reset system to initial state

Usage:
    python cleanup_database.py --help
    python cleanup_database.py --clean-all-data
    python cleanup_database.py --reset-system
    python cleanup_database.py --provider "gary_wang" --clean-data
"""

import argparse
import sys
import logging
from datetime import datetime
from pathlib import Path

import mysql.connector
from dotenv import load_dotenv
import os

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class DatabaseCleanup:
    """Handles database cleanup operations"""
    
    def __init__(self):
        """Initialize database connection"""
        load_dotenv('.env', override=True)
        
        self.config = {
            'host': os.getenv('WEBAUTODASH_DB_HOST', '128.205.221.54'),
            'port': int(os.getenv('WEBAUTODASH_DB_PORT', 3306)),
            'user': os.getenv('WEBAUTODASH_DB_USER', 'xvoice_user'),
            'password': os.getenv('WEBAUTODASH_DB_PASSWORD', 'Jetson@123')
        }
        
    def get_connection(self, database=None):
        """Get database connection"""
        config = self.config.copy()
        if database:
            config['database'] = database
        return mysql.connector.connect(**config)
    
    def get_provider_databases(self):
        """Get list of all provider databases"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute("SHOW DATABASES LIKE 'webautodash_%'")
            databases = [db[0] for db in cursor.fetchall()]
            
            # Filter out system database
            provider_databases = [db for db in databases if db != 'webautodash_system']
            
            return databases, provider_databases
        finally:
            cursor.close()
            conn.close()
    
    def get_provider_statistics(self):
        """Get statistics before cleanup"""
        all_databases, provider_databases = self.get_provider_databases()
        
        stats = {
            'total_databases': len(all_databases),
            'provider_databases': len(provider_databases),
            'providers': {}
        }
        
        for db_name in provider_databases:
            try:
                conn = self.get_connection(db_name)
                cursor = conn.cursor()
                
                provider_stats = {'database': db_name}
                
                # Get counts from each table
                tables = ['patients', 'extraction_sessions', 'patient_extractions', 
                         'medications', 'diagnoses', 'allergies', 'health_concerns', 'data_conflicts']
                
                for table in tables:
                    try:
                        cursor.execute(f"SELECT COUNT(*) FROM {table}")
                        count = cursor.fetchone()[0]
                        provider_stats[table] = count
                    except mysql.connector.Error:
                        provider_stats[table] = 0
                
                stats['providers'][db_name] = provider_stats
                
                cursor.close()
                conn.close()
                
            except mysql.connector.Error as e:
                logger.error(f"Error getting stats for {db_name}: {e}")
                stats['providers'][db_name] = {'error': str(e)}
        
        return stats
    
    def clean_provider_data(self, provider_database=None):
        """Clean data from provider database(s) but keep structure"""
        if provider_database:
            databases_to_clean = [provider_database]
        else:
            _, databases_to_clean = self.get_provider_databases()
        
        if not databases_to_clean:
            logger.info("No provider databases found to clean")
            return
        
        logger.info(f"Cleaning data from {len(databases_to_clean)} provider database(s)")
        
        # Tables in dependency order (child tables first)
        tables_to_clean = [
            'data_conflicts',
            'health_concerns', 
            'allergies',
            'diagnoses',
            'medications',
            'patient_extractions',
            'extraction_sessions',
            'patients'
        ]
        
        for db_name in databases_to_clean:
            try:
                logger.info(f"Cleaning data from database: {db_name}")
                conn = self.get_connection(db_name)
                cursor = conn.cursor()
                
                # Disable foreign key checks temporarily
                cursor.execute("SET FOREIGN_KEY_CHECKS = 0")
                
                for table in tables_to_clean:
                    try:
                        cursor.execute(f"DELETE FROM {table}")
                        affected_rows = cursor.rowcount
                        logger.info(f"  Cleaned {affected_rows} rows from {table}")
                    except mysql.connector.Error as e:
                        logger.warning(f"  Could not clean {table}: {e}")
                
                # Reset auto-increment counters
                for table in tables_to_clean:
                    try:
                        cursor.execute(f"ALTER TABLE {table} AUTO_INCREMENT = 1")
                    except mysql.connector.Error:
                        pass  # Not all tables have auto-increment
                
                # Re-enable foreign key checks
                cursor.execute("SET FOREIGN_KEY_CHECKS = 1")
                
                conn.commit()
                cursor.close()
                conn.close()
                
                logger.info(f"✅ Successfully cleaned database: {db_name}")
                
            except mysql.connector.Error as e:
                logger.error(f"❌ Error cleaning database {db_name}: {e}")
    
    def clean_system_database(self):
        """Clean system database data"""
        try:
            logger.info("Cleaning system database: webautodash_system")
            conn = self.get_connection('webautodash_system')
            cursor = conn.cursor()
            
            # Clean system tables
            cursor.execute("DELETE FROM system_logs")
            logs_cleaned = cursor.rowcount
            
            cursor.execute("DELETE FROM providers")
            providers_cleaned = cursor.rowcount
            
            # Reset auto-increment
            cursor.execute("ALTER TABLE system_logs AUTO_INCREMENT = 1")
            cursor.execute("ALTER TABLE providers AUTO_INCREMENT = 1")
            
            conn.commit()
            cursor.close()
            conn.close()
            
            logger.info(f"✅ System database cleaned: {logs_cleaned} logs, {providers_cleaned} providers")
            
        except mysql.connector.Error as e:
            logger.error(f"❌ Error cleaning system database: {e}")
    
    def drop_provider_databases(self):
        """Drop all provider databases completely"""
        _, provider_databases = self.get_provider_databases()
        
        if not provider_databases:
            logger.info("No provider databases found to drop")
            return
        
        logger.info(f"Dropping {len(provider_databases)} provider database(s)")
        
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            for db_name in provider_databases:
                logger.info(f"Dropping database: {db_name}")
                cursor.execute(f"DROP DATABASE IF EXISTS {db_name}")
                logger.info(f"✅ Dropped database: {db_name}")
            
            conn.commit()
            
        except mysql.connector.Error as e:
            logger.error(f"❌ Error dropping databases: {e}")
        finally:
            cursor.close()
            conn.close()
    
    def reset_system(self):
        """Complete system reset - drop all databases"""
        logger.info("🔄 Performing complete system reset...")
        
        # Get all databases
        all_databases, provider_databases = self.get_provider_databases()
        
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            # Drop all webautodash databases
            for db_name in all_databases:
                logger.info(f"Dropping database: {db_name}")
                cursor.execute(f"DROP DATABASE IF EXISTS {db_name}")
                logger.info(f"✅ Dropped database: {db_name}")
            
            conn.commit()
            logger.info("🎯 Complete system reset successful!")
            
        except mysql.connector.Error as e:
            logger.error(f"❌ Error during system reset: {e}")
        finally:
            cursor.close()
            conn.close()

def main():
    """Main function with command line interface"""
    parser = argparse.ArgumentParser(
        description="WebAutoDash Database Cleanup Tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python cleanup_database.py --stats                    # Show current statistics
  python cleanup_database.py --clean-all-data          # Clean all provider data
  python cleanup_database.py --provider gary_wang --clean-data  # Clean specific provider
  python cleanup_database.py --reset-system            # Complete reset (DANGEROUS!)
  python cleanup_database.py --drop-providers          # Drop all provider databases
        """
    )
    
    parser.add_argument('--stats', action='store_true', 
                       help='Show current database statistics')
    parser.add_argument('--clean-all-data', action='store_true',
                       help='Clean data from all provider databases (keep structure)')
    parser.add_argument('--clean-system', action='store_true',
                       help='Clean system database data')
    parser.add_argument('--drop-providers', action='store_true',
                       help='Drop all provider databases completely')
    parser.add_argument('--reset-system', action='store_true',
                       help='Complete system reset - drops ALL databases (DANGEROUS!)')
    parser.add_argument('--provider', type=str,
                       help='Specific provider database to clean (use with --clean-data)')
    parser.add_argument('--clean-data', action='store_true',
                       help='Clean data from specified provider (use with --provider)')
    parser.add_argument('--yes', action='store_true',
                       help='Skip confirmation prompts')
    
    args = parser.parse_args()
    
    if len(sys.argv) == 1:
        parser.print_help()
        return
    
    cleanup = DatabaseCleanup()
    
    # Show statistics
    if args.stats:
        print("\n📊 DATABASE STATISTICS")
        print("=" * 50)
        
        stats = cleanup.get_provider_statistics()
        print(f"Total Databases: {stats['total_databases']}")
        print(f"Provider Databases: {stats['provider_databases']}")
        
        for db_name, db_stats in stats['providers'].items():
            if 'error' in db_stats:
                print(f"\n❌ {db_name}: {db_stats['error']}")
                continue
                
            print(f"\n📋 {db_name.upper()}:")
            for table, count in db_stats.items():
                if table != 'database':
                    print(f"  {table:20}: {count:,}")
        
        return
    
    # Confirmation for destructive operations
    destructive_ops = [args.clean_all_data, args.drop_providers, args.reset_system, 
                      args.clean_system, (args.provider and args.clean_data)]
    
    if any(destructive_ops) and not args.yes:
        print("\n⚠️  WARNING: This operation will modify or delete database data!")
        if args.reset_system:
            print("🚨 DANGER: --reset-system will DROP ALL DATABASES!")
        
        response = input("\nAre you sure you want to continue? (yes/no): ")
        if response.lower() not in ['yes', 'y']:
            print("Operation cancelled.")
            return
    
    # Execute operations
    if args.provider and args.clean_data:
        provider_db = f"webautodash_{args.provider.lower().replace(' ', '_')}"
        cleanup.clean_provider_data(provider_db)
    
    elif args.clean_all_data:
        cleanup.clean_provider_data()
    
    elif args.clean_system:
        cleanup.clean_system_database()
    
    elif args.drop_providers:
        cleanup.drop_provider_databases()
    
    elif args.reset_system:
        cleanup.reset_system()
    
    else:
        print("No valid operation specified. Use --help for options.")

if __name__ == "__main__":
    main() 