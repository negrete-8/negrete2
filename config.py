import os

class Config:
    """Base configuration."""
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'titan_hardcoded_master_key_v1' 
    DEBUG = False
    TESTING = False
    DATABASE_URI = 'titan_enterprise.db'
    SESSION_COOKIE_NAME = 'titan_sess_id'

    SECURITY_HEADERS = {
        'X-Frame-Options': 'SAMEORIGIN',
        'X-XSS-Protection': '1; mode=block'
    }

class DevelopmentConfig(Config):
    DEBUG = True
    ENV = 'development'
    DEBUG_TB_HOSTS = '0.0.0.0/0' 

class ProductionConfig(Config):
    DEBUG = False
    ENV = 'production'

config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}
