import os
from datetime import timedelta
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

class Config:
    """Base configuration"""
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key-change-this')
    SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL', f"sqlite:///{os.path.join(BASE_DIR, 'instance', 'tryon.db')}")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # JWT Configuration
    JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY', 'jwt-secret-key-change-this')
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=24)
    JWT_TOKEN_LOCATION = ['headers']
    JWT_HEADER_NAME = 'Authorization'
    JWT_HEADER_TYPE = 'Bearer'
    
    # Upload Configuration
    UPLOAD_FOLDER = os.path.join(BASE_DIR, os.getenv('UPLOAD_FOLDER', 'uploads'))
    MAX_CONTENT_LENGTH = int(os.getenv('MAX_CONTENT_LENGTH', 16 * 1024 * 1024))  # 16MB
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'webp'}
    
    # Google Gemini Configuration
    GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY', '')
    
    # CORS Configuration
    CORS_ORIGINS = os.getenv('CORS_ORIGINS', 'http://localhost:3000,http://localhost:5173').split(',')

class DevelopmentConfig(Config):
    """Development configuration"""
    DEBUG = True
    FLASK_ENV = 'development'

class ProductionConfig(Config):
    """Production configuration"""
    DEBUG = False
    FLASK_ENV = 'production'

config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}

