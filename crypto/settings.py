import os
from pathlib import Path
from web3 import Web3
from dotenv import load_dotenv
import environ

# Load environment variables
load_dotenv()  # Load from .env file if it exists
env = environ.Env(DEBUG=(bool, False))  # Set default for DEBUG

# Base directory of the project
BASE_DIR = Path(__file__).resolve().parent.parent

# Environment variables with validation
KUCOIN_API_KEY = env('KUCOIN_API_KEY', default=None)
KUCOIN_API_SECRET = env('KUCOIN_API_SECRET', default=None)
KUCOIN_API_PASSPHRASE = env('KUCOIN_API_PASSPHRASE', default=None)
KUCOIN_API_URL = env('KUCOIN_API_URL', default='https://api.kucoin.com')
OWNER_WALLET_ADDRESSES = env.list('OWNER_WALLET_ADDRESSES', default=[])


# Critical settings
SECRET_KEY = env('SECRET_KEY')
if not SECRET_KEY:
    raise ValueError("SECRET_KEY is not set in the environment variables.")

DEBUG = env.bool('DEBUG', default=False)
ALLOWED_HOSTS = env.list('ALLOWED_HOSTS', default=['127.0.0.1'])

# Web3 Configuration
WEB3_PROVIDER_URL = env('WEB3_PROVIDER_URL')
if not WEB3_PROVIDER_URL:
    raise ValueError("WEB3_PROVIDER_URL is not set in the environment variables.")

web3 = Web3(Web3.HTTPProvider(WEB3_PROVIDER_URL))

# Email Configuration
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = env('EMAIL_HOST', default='smtp.gmail.com')
EMAIL_PORT = env.int('EMAIL_PORT', default=587)
EMAIL_USE_TLS = env.bool('EMAIL_USE_TLS', default=True)
EMAIL_HOST_USER = env('EMAIL_HOST_USER')
EMAIL_HOST_PASSWORD = env('EMAIL_HOST_PASSWORD')

# Coinbase API keys
COINBASE_API_KEY = env('COINBASE_API_KEY')
COINBASE_API_SECRET = env('COINBASE_API_SECRET')
COINBASE_API_PASS = env('COINBASE_API_PASS')
if not COINBASE_API_KEY or not COINBASE_API_SECRET:
    raise ValueError("Coinbase API credentials are missing.")

# Database Configuration
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

# Installed Apps for Django
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.humanize",
    "mainapp",
    "crispy_forms",
    "crispy_bootstrap5",
    'django_q',
    'corsheaders',
]

# Middleware settings for Django
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    'corsheaders.middleware.CorsMiddleware',
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

# Root URL configuration
ROOT_URLCONF = "crypto.urls"
WSGI_APPLICATION = "crypto.wsgi.application"

# Static and Media Configuration
STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# Template settings for Django
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',  # The correct template engine
        'DIRS': [
            BASE_DIR / 'templates',  # Global templates directory (optional)
        ],
        'APP_DIRS': True,  # This allows Django to find templates inside app folders
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

# CORS Configuration
CORS_ALLOW_ALL_ORIGINS = True
CORS_ALLOWED_ORIGINS = [
    "http://localhost:8000",  # Change this to your actual frontend domain
]

# Q Cluster settings (Django Q configuration)
Q_CLUSTER = {
    'name': 'default',
    'workers': 4,
    'timeout': 60,  # Timeout in seconds
    'retry': 120,   # Retry time in seconds (should be greater than timeout)
    'catch_up': False,
    'save_limit': 250,
    'demand': False,
    'orm': 'default',
}

# Twilio configuration (ensure these are set in .env)
TWILIO_SID = env('TWILIO_SID')
TWILIO_AUTH_TOKEN = env('TWILIO_AUTH_TOKEN')
TWILIO_PHONE_NUMBER = env('TWILIO_PHONE_NUMBER')

# MetaTrader configuration
METATRADER_CONFIG = {
    'server': env('METATRADER_SERVER', default='broker_server_name'),
    'login': env('METATRADER_LOGIN', default=88884746),
    'password': env('METATRADER_PASSWORD', default='default-password'),
    'path': env('METATRADER_PATH', default=r'C:\Path\To\Your\MetaTrader5\terminal64.exe'),
}


LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'DEBUG',
    },
}
