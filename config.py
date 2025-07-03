"""
Configuration settings for the Flask application.

This module defines different configuration classes for various
environments (e.g., Development, Production, Testing).
The appropriate configuration is loaded based on an environment variable.
"""
import os
from dotenv import load_dotenv

load_dotenv() # Load environment variables from .env file

class Config:
    """Base configuration class."""
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'you-will-never-guess'
    DEBUG = False
    TESTING = False

    # Firebase Configuration
    FIREBASE_API_KEY = os.environ.get('FIREBASE_API_KEY')
    FIREBASE_AUTH_DOMAIN = os.environ.get('FIREBASE_AUTH_DOMAIN')
    FIREBASE_PROJECT_ID = os.environ.get('FIREBASE_PROJECT_ID')
    FIREBASE_STORAGE_BUCKET = os.environ.get('FIREBASE_STORAGE_BUCKET')
    FIREBASE_MESSAGING_SENDER_ID = os.environ.get('FIREBASE_MESSAGING_SENDER_ID')
    FIREBASE_APP_ID = os.environ.get('FIREBASE_APP_ID')
    FIREBASE_DATABASE_URL = os.environ.get('FIREBASE_DATABASE_URL', '') # Optional, if using Realtime DB

    FIREBASE_CONFIG = {
        "apiKey": FIREBASE_API_KEY,
        "authDomain": FIREBASE_AUTH_DOMAIN,
        "projectId": FIREBASE_PROJECT_ID,
        "storageBucket": FIREBASE_STORAGE_BUCKET,
        "messagingSenderId": FIREBASE_MESSAGING_SENDER_ID,
        "appId": FIREBASE_APP_ID,
        "databaseURL": FIREBASE_DATABASE_URL, # For Realtime Database, if used
    }

    # Supabase Configuration
    SUPABASE_URL = os.environ.get('SUPABASE_URL')
    SUPABASE_SERVICE_ROLE = os.environ.get('SUPABASE_SERVICE_ROLE')

    # File Upload Configuration
    ALLOWED_EXTENSIONS_PDF = {'pdf', 'doc', 'docx', 'xls', 'xlsx'}
    ALLOWED_EXTENSIONS_IMG = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
    BUCKET_DOCUMENTS = 'documents'
    BUCKET_BLOG_IMAGES = 'blog-images'
    BUCKET_IMAGES = 'gallery'
    
    # Flask Configuration
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max upload


class DevelopmentConfig(Config):
    """Development configuration."""
    DEBUG = True
    # Add development-specific settings here, e.g.,
    # SQLALCHEMY_DATABASE_URI = os.environ.get('DEV_DATABASE_URL') or \
    #     'sqlite:///' + os.path.join(os.path.abspath(os.path.dirname(__file__)), 'instance', 'dev_blog.db')


class ProductionConfig(Config):
    """Production configuration."""
    DEBUG = False
    TESTING = False
    # Add production-specific settings here, e.g.,
    # SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL')
    # Ensure SECRET_KEY is strong and set via environment variable


class TestingConfig(Config):
    """Testing configuration."""
    TESTING = True
    DEBUG = True
    # Add test-specific settings here, e.g.,
    # SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    # WTF_CSRF_ENABLED = False # Disable CSRF for tests if using Flask-WTF


config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}