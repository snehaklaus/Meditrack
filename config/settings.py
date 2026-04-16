"""
Django settings for config project.
"""

from pathlib import Path
from decouple import config
import os
from datetime import timedelta
import dj_database_url

BASE_DIR = Path(__file__).resolve().parent.parent

# ========================
# SECURITY
# ========================
SECRET_KEY = config("SECRET_KEY", default="unsafe-secret-key")
DEBUG = config("DEBUG", default=False, cast=bool)

ALLOWED_HOSTS = [
    "meditrack.up.railway.app",
    "meditrack7.up.railway.app",
    "meditrack7.vercel.app",
    "localhost",
    "127.0.0.1",
]

# ========================
# APPS
# ========================
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    'rest_framework',
    'rest_framework_simplejwt',
    'corsheaders',
    'django_celery_beat',
    'django_ratelimit',
    'drf_spectacular',

    'accounts',
    'medications',
    'django_filters',
    'symptoms',
    'fhir_integration',
    'visitor_tracking',
]

# ========================
# MIDDLEWARE
# ========================
MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',

    'visitor_tracking.middleware.VisitorTrackingMiddleware',
    'visitor_tracking.middleware.BotDetectionMiddleware',
]

ROOT_URLCONF = 'config.urls'
WSGI_APPLICATION = 'config.wsgi.application'

# ========================
# TEMPLATES
# ========================
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
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

# ========================
# DATABASE
# ========================
DATABASES = {
    'default': dj_database_url.config(
        default=config("DATABASE_URL", default=f"sqlite:///{BASE_DIR / 'db.sqlite3'}"),
        conn_max_age=600,
        conn_health_checks=True,
    )
}

# ========================
# AUTH
# ========================
AUTH_USER_MODEL = 'accounts.User'

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# ========================
# INTERNATIONALIZATION
# ========================
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

# ========================
# STATIC FILES
# ========================
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# ========================
# DRF + JWT
# ========================
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ),
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.IsAuthenticated',
    ),
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
}

SPECTACULAR_SETTINGS = {
    'TITLE': 'MediTrack API',
    'DESCRIPTION': 'Personal Health & Medication Reminder API with AI insights',
    'VERSION': '1.0.0',
    'SERVE_INCLUDE_SCHEMA': False,
}

SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(hours=1),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
}

# ========================
# CORS
# ========================
CORS_ALLOW_CREDENTIALS = True

CORS_ALLOWED_ORIGINS = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "https://meditrack7.vercel.app",
    "https://meditrack7.up.railway.app",
    "https://meditrack1.up.railway.app",
]

CSRF_TRUSTED_ORIGINS = [
    "https://meditrack.up.railway.app",
    "https://meditrack7.up.railway.app",
    "https://meditrack7.vercel.app",
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]

# ========================
# API KEYS (SAFE)
# ========================
GEMINI_API_KEY = config("GEMINI_API_KEY", default=None)
BREVO_API_KEY = config("BREVO_API_KEY", default=None)
DEFAULT_FROM_EMAIL = config("BREVO_EMAIL", default="noreply@example.com")

# ========================
# REDIS / CACHE
# ========================
REDIS_URL = config('REDIS_URL', default='redis://localhost:6379/1')

CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': REDIS_URL,
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
        }
    }
}

# ========================
# CELERY
# ========================
CELERY_BROKER_URL = REDIS_URL
CELERY_RESULT_BACKEND = REDIS_URL
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = 'UTC'

# ========================
# FEATURE FLAGS
# ========================
USE_MOCK_AI = config('USE_MOCK_AI', default=False, cast=bool)

# ========================
# EMAIL
# ========================
EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"

# ========================
# SECURITY (PROD ONLY)
# ========================
if not DEBUG:
    SECURE_SSL_REDIRECT = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_BROWSER_XSS_FILTER = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    X_FRAME_OPTIONS = 'DENY'
    SECURE_HSTS_SECONDS = 3153600
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True

# ========================
# GOOGLE OAUTH
# ========================
GOOGLE_OAUTH_CLIENT_ID = config('GOOGLE_CLIENT_ID', default='')
GOOGLE_OAUTH_CLIENT_SECRET = config('GOOGLE_CLIENT_SECRET', default='')

SECURE_CROSS_ORIGIN_OPENER_POLICY = None

# ========================
# FHIR
# ========================
FHIR_CONFIG = {
    'R4_BASE_URL': 'https://meditrack.up.railway.app/fhir/r4/',
    'ORGANIZATION_NAME': 'MediTrack',
    'ENABLE_SMART_ON_FHIR': True,
}

# ========================
# VISITOR TRACKING
# ========================
ENABLE_VISITOR_TRACKING = True
ADMIN_IPS = '1110.226.183.226'
ADMIN_EMAIL = 'admin@example.com'

# ========================
# LOGGING
# ========================
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {'class': 'logging.StreamHandler'},
        'fhir_file': {
            'level': 'DEBUG',
            'class': 'logging.FileHandler',
            'filename': 'fhir.log',
        },
    },
    'loggers': {
        'fhir_integration': {
            'handlers': ['console', 'fhir_file'],
            'level': 'DEBUG',
            'propagate': False,
        },
    },
}