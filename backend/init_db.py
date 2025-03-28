#!/usr/bin/env python3
"""
Database initialization script for WebAutoDash

This script initializes the database and adds sample adapters for testing.
"""

import os
import sys
from pathlib import Path

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from models import db, PortalAdapter

def init_database():
    """Initialize the database and add sample adapters"""
    app = create_app()
    
    with app.app_context():
        # Create all tables
        db.create_all()
        print("Database tables created successfully!")
        
        # Check if test adapter already exists
        existing_adapter = PortalAdapter.query.filter_by(name='Test Portal Adapter').first()
        if existing_adapter:
            print("Test adapter already exists in database.")
            return
        
        # Add test adapter
        test_adapter = PortalAdapter(
            name='Test Portal Adapter',
            description='A simple test adapter for validating WebAutoDash functionality',
            script_filename='test_adapter.py',
            is_active=True
        )
        
        db.session.add(test_adapter)
        db.session.commit()
        
        print(f"Test adapter added successfully with ID: {test_adapter.id}")
        
        # List all adapters
        adapters = PortalAdapter.query.all()
        print(f"\nAll adapters in database ({len(adapters)}):")
        for adapter in adapters:
            status = "Active" if adapter.is_active else "Inactive"
            print(f"  ID: {adapter.id}, Name: {adapter.name}, Status: {status}")

if __name__ == "__main__":
    init_database() 