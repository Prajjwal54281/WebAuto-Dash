from flask import Flask, request
from flask_cors import CORS
from flask_migrate import Migrate
from flask_socketio import SocketIO
import os
import logging
from dotenv import load_dotenv
from datetime import datetime
import time

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

def create_app():
    app = Flask(__name__)
    
    # Configuration with optimized SQLite settings
    database_url = os.environ.get('DATABASE_URL') or 'sqlite:///webautodash.db'
    
    # Add SQLite optimizations
    if database_url.startswith('sqlite:'):
        if '?' not in database_url:
            database_url += '?timeout=30&check_same_thread=False'
    
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'
    app.config['SQLALCHEMY_DATABASE_URI'] = database_url
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
        'pool_pre_ping': True,
        'pool_recycle': 3600,
        'connect_args': {
            'timeout': 30,
            'check_same_thread': False
        } if database_url.startswith('sqlite:') else {}
    }
    
    # Initialize extensions
    from models import db
    db.init_app(app)
    
    # Enable CORS for frontend integration - Allow any origin for development
    CORS(app, 
         origins="*",
         allow_headers=["Content-Type", "Authorization", "Cache-Control", "Pragma", "Expires", "X-Requested-With", "X-Cache-Bust"],
         methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
         supports_credentials=True)
    
    # Initialize Flask-Migrate
    migrate = Migrate(app, db)
    
    # Initialize SocketIO for real-time updates - Allow any origin for development
    socketio = SocketIO(
        app, 
        cors_allowed_origins="*",
        logger=True,
        engineio_logger=True,
        transport=['websocket', 'polling']
    )
    
    # Add after_request handler for cache control headers
    @app.after_request
    def after_request(response):
        # Log slow requests for performance monitoring
        if hasattr(request, 'start_time'):
            duration = time.time() - request.start_time
            if duration > 5.0:  # Log requests taking more than 5 seconds
                logger.warning(f"Slow request: {request.method} {request.path} took {duration:.2f}s")
        
        # Add strong cache-busting headers for Chrome compatibility
        response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate, max-age=0'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'
        response.headers['X-Content-Type-Options'] = 'nosniff'
        return response
    
    # Add before_request handler for timing
    @app.before_request
    def before_request():
        """Add request timeout handling"""
        request.start_time = time.time()
    
    # Register blueprints
    try:
        from routes.jobs_api import jobs_bp
        from routes.admin_api import admin_bp
        from routes.portal_inspector_api import portal_inspector_bp
        from routes.live_inspector_api_v2 import live_inspector_bp as live_inspector_v2_bp
        from routes.realtime_api import realtime_bp, init_socketio
        from routes.patient_data_api import patient_data_bp
        
        app.register_blueprint(jobs_bp, url_prefix='/api')
        app.register_blueprint(admin_bp, url_prefix='/api/admin')
        app.register_blueprint(portal_inspector_bp, url_prefix='/api/portal-inspector')
        app.register_blueprint(patient_data_bp, url_prefix='/api/patient-data')
        
        # Pass SocketIO to live inspector blueprint
        live_inspector_v2_bp.socketio = socketio
        app.register_blueprint(live_inspector_v2_bp, url_prefix='/api/live-inspector')
        
        app.register_blueprint(realtime_bp, url_prefix='/api/realtime')
        
        # Initialize socketio in realtime module
        init_socketio(socketio)
        logger.info("✅ All blueprints registered successfully - using advanced live inspector v2")
        
    except Exception as e:
        logger.error(f"❌ Failed to register blueprints: {e}")
        raise e
    
    # Create tables
    with app.app_context():
        try:
            db.create_all()
            logger.info("✅ Database tables created/verified")
        except Exception as e:
            logger.error(f"❌ Database initialization failed: {e}")
            raise e
    
    @app.route('/')
    def index():
        return {
            'message': 'WebAutoDash Backend API', 
            'version': '2.0.0', 
            'features': [
                'real-time updates',
                'enhanced portal inspector',
                'comprehensive portal analysis',
                'automatic adapter generation',
                'CAPTCHA detection',
                'multi-strategy extraction'
            ],
            'status': 'ready'
        }
    
    @app.route('/health')
    def health():
        try:
            # Test database connection
            with app.app_context():
                db.session.execute('SELECT 1')
            
            return {
                'status': 'healthy', 
                'database': 'connected', 
                'socketio': 'enabled',
                'portal_inspector': 'ready',
                'timestamp': datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return {
                'status': 'unhealthy',
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }, 500
    
    @app.route('/api/portal-inspector/status')
    def portal_inspector_status():
        """Check Portal Inspector components status"""
        try:
            status = {
                'enhanced_inspector': False,
                'quick_inspector': False,
                'universal_inspector': False,
                'playwright_available': False,
                'selenium_available': False
            }
            
            # Check Enhanced Portal Inspector
            try:
                import sys
                sys.path.append('..')
                from enhanced_portal_inspector import EnhancedPortalInspector
                status['enhanced_inspector'] = True
            except ImportError:
                pass
            
            # Check Quick Portal Inspector
            try:
                import os
                quick_inspector_path = os.path.join('..', 'quick_portal_inspector.py')
                if os.path.exists(quick_inspector_path):
                    status['quick_inspector'] = True
            except:
                pass
            
            # Check Universal Portal Inspector
            try:
                from universal_portal_inspector import UniversalPortalInspector
                status['universal_inspector'] = True
            except ImportError:
                pass
            
            # Check Playwright
            try:
                from playwright.async_api import async_playwright
                status['playwright_available'] = True
            except ImportError:
                pass
            
            # Check Selenium
            try:
                from selenium import webdriver
                status['selenium_available'] = True
            except ImportError:
                pass
            
            return {
                'success': True,
                'status': status,
                'ready': any(status.values()),
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }, 500
    
    # Store socketio instance for use in other modules
    app.socketio = socketio
    
    # Add error handlers
    @app.errorhandler(404)
    def not_found(error):
        return {'error': 'Endpoint not found', 'message': str(error)}, 404
    
    @app.errorhandler(500)
    def internal_error(error):
        logger.error(f"Internal server error: {error}")
        return {'error': 'Internal server error', 'message': 'Please check the logs'}, 500
    
    logger.info("🚀 WebAutoDash Backend initialized successfully")
    return app

if __name__ == '__main__':
    app = create_app()
    logger.info("🌐 Starting WebAutoDash Backend Server...")
    # Run with proper Socket.IO support
    app.socketio.run(
        app, 
        debug=True, 
        host='0.0.0.0', 
        port=5005, 
        allow_unsafe_werkzeug=True, 
        use_reloader=False
    ) 