from app import create_app
from models import db, PortalAdapter, ExtractionJob

app = create_app()

with app.app_context():
    print('=== Portal Adapters ===')
    adapters = PortalAdapter.query.all()
    for adapter in adapters:
        print(f'ID: {adapter.id}, Name: {adapter.name}, Active: {adapter.is_active}, Script: {adapter.script_filename}')
    
    print('\n=== Extraction Jobs ===')
    jobs = ExtractionJob.query.order_by(ExtractionJob.created_at.desc()).limit(10).all()
    for job in jobs:
        print(f'ID: {job.id}, Status: {job.status}, Adapter: {job.portal_adapter_id}, URL: {job.target_url}, Error: {job.error_message}')
    
    print(f'\nTotal Jobs: {ExtractionJob.query.count()}')
    print(f'Active Jobs: {ExtractionJob.query.filter(ExtractionJob.status.in_(["PENDING_LOGIN", "AWAITING_USER_CONFIRMATION", "EXTRACTING", "LAUNCHING_BROWSER"])).count()}') 