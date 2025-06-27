"""
Django settings for PriceTracker project.
"""
import os
import json
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(dotenv_path=BASE_DIR / '.env')

# ===================================================================
# --- SHARED CONFIGURATION LOADER ---
# This block reads the central config file. It is the single source of truth.
# ===================================================================
try:
    with open(BASE_DIR / 'shared_config.json', 'r') as f:
        shared_config = json.load(f)
    NGROK_URL = shared_config['NGROK_URL'].strip()
    LOCAL_IP = shared_config['LOCAL_IP'].strip()
    # Extract domain from ngrok URL for ALLOWED_HOSTS
    NGROK_DOMAIN = NGROK_URL.split('//')[1]
    print("✅ Loaded shared config successfully.")
except (FileNotFoundError, KeyError, IndexError) as e:
    print(f"⚠️ WARNING: Could not load or parse 'shared_config.json': {e}")
    print("   Falling back to default development values. Your app might not connect.")
    NGROK_URL = "https://placeholder.ngrok-free.app"
    LOCAL_IP = "192.168.1.100"
    NGROK_DOMAIN = "placeholder.ngrok-free.app"

# ===================================================================
# Core Django Settings
# ===================================================================
SECRET_KEY = os.getenv('DJANGO_SECRET_KEY', 'django-insecure-fallback-key-for-dev')
DEBUG = True
# AI Processing Configuration
AI_USE_GPU = False  # Set to False for CPU-only processing
AI_DEBUG_SAVE_STEPS = True  # Enable automatic saving of preprocessing steps
AI_DEBUG_DIR = os.path.join(BASE_DIR, 'media', 'debug_preprocessing')  # Where to save debug images
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'file': {
            'level': 'INFO',
            'class': 'logging.FileHandler',
            'filename': os.path.join(BASE_DIR, 'logs', 'ai_processing.log'),
            'formatter': 'verbose',
        },
        'console': {
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
    },
    'loggers': {
        'api.enhanced_preprocessor': {
            'handlers': ['file', 'console'],
            'level': 'INFO',
            'propagate': True,
        },
        'api.util': {
            'handlers': ['file', 'console'],
            'level': 'INFO',
            'propagate': True,
        },
        'api.tasks': {
            'handlers': ['file', 'console'],
            'level': 'INFO', 
            'propagate': True,
        },
    },
}

# Create logs directory
os.makedirs(os.path.join(BASE_DIR, 'logs'), exist_ok=True)
# --- Automatically configured hosts ---
ALLOWED_HOSTS = [
    'localhost', 
    '127.0.0.1', 
    LOCAL_IP, 
    NGROK_DOMAIN,
]

# --- Application definition ---
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',
    'rest_framework.authtoken',
    'corsheaders',
    'api',
    # 'frontend', # Usually not needed in INSTALLED_APPS for a separate RN app
]

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'PriceTracker.urls'
WSGI_APPLICATION = 'PriceTracker.wsgi.application'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

# --- Database ---
# Reads from shared_config.json, with a fallback
try:
    db_config = shared_config['DATABASE']
    DATABASES = {'default': db_config}
    DATABASES['default']['ENGINE'] = 'django.db.backends.postgresql'
except (NameError, KeyError):
    print("⚠️ WARNING: Using fallback database configuration.")
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql', 'NAME': 'price_tracker',
            'USER': 'price_tracker_user', 'PASSWORD': 'berke12345',
            'HOST': 'localhost', 'PORT': '5432',
        }
    }


# --- REST Framework & CORS ---
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.TokenAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticatedOrReadOnly',
    ],
}

# --- Automatically configured CORS origins ---
CORS_ALLOWED_ORIGINS = [
    NGROK_URL,
    f"http://{LOCAL_IP}:8081", # For Expo Go
    "http://localhost:8081",  # For Expo Go
]
# For development, allowing all origins is often easier
# In production, you MUST restrict this to your actual frontend domain.
CORS_ALLOW_ALL_ORIGINS = DEBUG 

# --- Static & Media Files ---
STATIC_URL = 'static/'
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# --- Internationalization ---
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

# --- Other Settings ---
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# --- Celery & Redis Configuration ---
CELERY_BROKER_URL = 'redis://localhost:6379/0'
CELERY_RESULT_BACKEND = 'redis://localhost:6379/0'
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'

# --- Final Debug Output ---
if DEBUG:
    print("--- Django Settings Loaded ---")
    print(f"MODE: Development")
    print(f"NGROK_URL: {NGROK_URL}")
    print(f"LOCAL_IP: {LOCAL_IP}")
    print(f"ALLOWED_HOSTS: {ALLOWED_HOSTS}")
    print(f"CORS_ALLOWED_ORIGINS: {CORS_ALLOWED_ORIGINS} (CORS_ALLOW_ALL_ORIGINS={CORS_ALLOW_ALL_ORIGINS})")
    print("----------------------------")