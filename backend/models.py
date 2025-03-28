from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import json

db = SQLAlchemy()

class PortalAdapter(db.Model):
    __tablename__ = 'portal_adapters'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False, index=True)
    description = db.Column(db.Text, nullable=True)
    script_filename = db.Column(db.String(200), unique=True, nullable=False)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationship
    extraction_jobs = db.relationship('ExtractionJob', backref='adapter', lazy=True)
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'script_filename': self.script_filename,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }

class ExtractionJob(db.Model):
    __tablename__ = 'extraction_jobs'
    
    id = db.Column(db.Integer, primary_key=True)
    job_name = db.Column(db.String(200), nullable=True)  # New field for custom job naming
    target_url = db.Column(db.String(500), nullable=False)
    portal_adapter_id = db.Column(db.Integer, db.ForeignKey('portal_adapters.id'), nullable=False)
    extraction_mode = db.Column(db.String(50), nullable=False)  # 'SINGLE_PATIENT', 'ALL_PATIENTS'
    input_patient_identifier = db.Column(db.String(200), nullable=True)
    # New medication report parameters
    doctor_name = db.Column(db.String(200), nullable=True)
    medication = db.Column(db.String(200), nullable=True)
    start_date = db.Column(db.Date, nullable=True)
    end_date = db.Column(db.Date, nullable=True)
    # Results storage
    results_file_path = db.Column(db.String(500), nullable=True)
    status = db.Column(db.String(50), nullable=False, index=True, default='PENDING_LOGIN')
    # Status values: 'PENDING_LOGIN', 'LAUNCHING_BROWSER', 'AWAITING_USER_CONFIRMATION', 'EXTRACTING', 'COMPLETED', 'FAILED'
    error_message = db.Column(db.Text, nullable=True)
    raw_extracted_data_json = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    def to_dict(self, include_adapter_name=True):
        """Optimized to_dict with optional adapter name loading"""
        extracted_data = None
        if self.raw_extracted_data_json:
            try:
                extracted_data = json.loads(self.raw_extracted_data_json)
            except json.JSONDecodeError:
                extracted_data = None
        
        result = {
            'id': self.id,
            'job_name': self.job_name,
            'target_url': self.target_url,
            'portal_adapter_id': self.portal_adapter_id,
            'extraction_mode': self.extraction_mode,
            'input_patient_identifier': self.input_patient_identifier,
            'doctor_name': self.doctor_name,
            'medication': self.medication,
            'start_date': self.start_date.isoformat() if self.start_date else None,
            'end_date': self.end_date.isoformat() if self.end_date else None,
            'results_file_path': self.results_file_path,
            'status': self.status,
            'error_message': self.error_message,
            'extracted_data': extracted_data,
            'raw_extracted_data_json': self.raw_extracted_data_json,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }
        
        # Only include adapter_name if specifically requested to avoid N+1 queries
        if include_adapter_name:
            result['adapter_name'] = self.adapter.name if self.adapter else None
            
        return result 