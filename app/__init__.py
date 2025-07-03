"""
Application factory for the Flask app.
"""
import os
from flask import Flask, g, session
from supabase import create_client, Client
import pyrebase
from datetime import datetime
from app.services.cache_service import CacheService
import threading
import time

# Global variables for external services
supabase: Client = None
firebase = None
auth = None

def create_app(config_name=None):
    """
    Application factory function.
    
    Args:
        config_name (str): Configuration name ('development', 'production', 'testing')
        
    Returns:
        Flask: Configured Flask application instance
    """
    app = Flask(__name__)
    
    # Load configuration
    if config_name is None:
        config_name = os.environ.get('FLASK_ENV', 'development')
    
    from config import config
    app.config.from_object(config[config_name])
    
    # Initialize external services
    init_external_services(app)
    
    # Register blueprints
    register_blueprints(app)
    
    # Register error handlers
    register_error_handlers(app)
    
    # Register template filters
    register_template_filters(app)
    
    # Register before request handlers
    register_before_request_handlers(app)
    
    # Configurar limpeza automática do cache
    def start_cache_cleanup():
        """Inicia thread para limpeza automática do cache"""
        def cleanup_worker():
            while True:
                try:
                    time.sleep(1800)  # 30 minutos
                    CacheService.cleanup_cache()
                except Exception as e:
                    app.logger.error(f"Erro na limpeza automática do cache: {e}")
        
        cleanup_thread = threading.Thread(target=cleanup_worker, daemon=True)
        cleanup_thread.start()
    
    # Iniciar limpeza automática apenas em produção
    if not app.debug:
        start_cache_cleanup()
    
    return app

def init_external_services(app):
    """Initialize Firebase and Supabase clients."""
    global supabase, firebase, auth
    
    # Initialize Firebase (for authentication)
    firebase_config = app.config['FIREBASE_CONFIG']
    firebase = pyrebase.initialize_app(firebase_config)
    auth = firebase.auth()
    
    # Initialize Supabase (for database and storage)
    supabase_url = app.config['SUPABASE_URL']
    supabase_key = app.config['SUPABASE_SERVICE_ROLE']
    supabase = create_client(supabase_url, supabase_key)

def register_blueprints(app):
    """Register all application blueprints."""
    from app.routes.main_routes import main_bp
    from app.routes.auth_routes import auth_bp
    from app.routes.blog_routes import blog_bp
    from app.routes.galeria_routes import galeria_bp
    from app.routes.admin_routes import admin_bp
    from app.routes.transparency_routes import transparency_bp
    
    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(blog_bp, url_prefix='/blog')
    app.register_blueprint(galeria_bp, url_prefix='/galeria')
    app.register_blueprint(admin_bp, url_prefix='/admin')
    app.register_blueprint(transparency_bp, url_prefix='/transparencia')

def register_error_handlers(app):
    """Register error handlers."""
    from flask import render_template, request, jsonify
    import logging
    
    # Configurar logging
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)
    
    @app.errorhandler(404)
    def not_found_error(error):
        if request.path.startswith('/api/'):
            return jsonify({'error': 'Endpoint não encontrado'}), 404
        return render_template('errors/404.html'), 404

    @app.errorhandler(403)
    def forbidden_error(error):
        if request.path.startswith('/api/'):
            return jsonify({'error': 'Acesso negado'}), 403
        return render_template('errors/403.html'), 403

    @app.errorhandler(500)
    def internal_error(error):
        logger.error(f"Erro interno: {error}")
        if request.path.startswith('/api/'):
            return jsonify({'error': 'Erro interno do servidor'}), 500
        return render_template('errors/500.html'), 500
    
    @app.errorhandler(503)
    def service_unavailable_error(error):
        logger.warning(f"Serviço indisponível: {error}")
        if request.path.startswith('/api/'):
            return jsonify({'error': 'Serviço temporariamente indisponível'}), 503
        return render_template('errors/503.html'), 503
    
    @app.errorhandler(Exception)
    def handle_exception(error):
        """Handle unexpected exceptions."""
        logger.error(f"Erro não tratado: {error}", exc_info=True)
        
        # Se for um erro de conectividade do Supabase
        error_str = str(error)
        if "521" in error_str or "Web server is down" in error_str:
            if request.path.startswith('/api/'):
                return jsonify({'error': 'Serviço temporariamente indisponível'}), 503
            return render_template('errors/503.html'), 503
        
        # Outros erros
        if request.path.startswith('/api/'):
            return jsonify({'error': 'Erro interno do servidor'}), 500
        return render_template('errors/500.html'), 500

def register_template_filters(app):
    """Register custom template filters."""
    @app.template_filter('datetime')
    def format_datetime(value):
        if isinstance(value, str):
            try:
                value = datetime.fromisoformat(value.replace('Z', '+00:00'))
            except ValueError:
                return value
        
        if isinstance(value, datetime):
            return value.strftime('%d/%m/%Y %H:%M')
        
        return value

def register_before_request_handlers(app):
    """Register before request handlers."""
    @app.before_request
    def load_logged_in_user():
        """Load user information into g.user before each request."""
        user_session = session.get('user')
        if user_session is None:
            g.user = None
        else:
            g.user = user_session