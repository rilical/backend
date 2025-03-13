import os
from pathlib import Path

from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Build paths
BASE_DIR = Path(__file__).resolve().parent.parent

# Security settings
SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "your-secret-key-here")
DEBUG = os.getenv("DJANGO_DEBUG", "True") == "True"

# When in DEBUG mode, allow all hosts for ease of development
if DEBUG:
    ALLOWED_HOSTS = ["*"]
else:
    ALLOWED_HOSTS = os.getenv("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1").split(",")

# Application definition
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # Third party apps
    "rest_framework",
    "django_celery_beat",
    "django_filters",
    "corsheaders",  # Add CORS headers app
    "django_extensions",  # Added for debugging
    "drf_spectacular",  # OpenAPI 3.0 schema generator
    "drf_spectacular_sidecar",  # Required for Swagger UI
    # Local apps
    "providers",  # Provider rate comparison (changed from apps.providers)
    "aggregator",  # Aggregator service
    "quotes",  # Quote storage and caching
    "remit_scout",  # Added remit_scout app
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "corsheaders.middleware.CorsMiddleware",  # Add CORS middleware
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    # Custom security middleware
    "remit_scout.middleware.SecurityHeadersMiddleware",
    "remit_scout.middleware.RequestIDMiddleware",
    "remit_scout.middleware.SessionAuthMiddleware",  # Add session auth middleware
    "remit_scout.middleware.RequestLoggingMiddleware",
    "remit_scout.middleware.RateLimitMiddleware",
]

# CORS settings
if DEBUG:
    CORS_ALLOW_ALL_ORIGINS = True  # Only in development
else:
    CORS_ALLOW_ALL_ORIGINS = False
    CORS_ALLOWED_ORIGINS = os.getenv("CORS_ALLOWED_ORIGINS", "http://localhost:3000").split(",")
    CORS_ALLOW_CREDENTIALS = True
    CORS_ALLOW_METHODS = [
        "DELETE",
        "GET",
        "OPTIONS",
        "PATCH",
        "POST",
        "PUT",
    ]
    CORS_ALLOW_HEADERS = [
        "accept",
        "accept-encoding",
        "authorization",
        "content-type",
        "dnt",
        "origin",
        "user-agent",
        "x-csrftoken",
        "x-requested-with",
        "x-api-key",
        "x-request-id",
    ]

ROOT_URLCONF = "remit_scout.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "remit_scout" / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "remit_scout.wsgi.application"

# Database
if os.getenv("DJANGO_ENV", "development") == "development":
    # Use SQLite for development
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }
else:
    # Use PostgreSQL for production
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": os.getenv("POSTGRES_DB", "remitscout"),
            "USER": os.getenv("POSTGRES_USER", "postgres"),
            "PASSWORD": os.getenv("POSTGRES_PASSWORD", "postgres"),
            "HOST": os.getenv("POSTGRES_HOST", "localhost"),
            "PORT": os.getenv("POSTGRES_PORT", "5432"),
            # Add connection pooling for better performance
            "CONN_MAX_AGE": 60,  # Keep connections alive for 60 seconds
            # Add SSL settings for production only
            "OPTIONS": {
                "sslmode": "require",
            },
        }
    }

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
        "OPTIONS": {
            "min_length": 10,  # Increased from default 8
        },
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]

# Password hashing - use stronger Argon2 hasher
PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.Argon2PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2SHA1PasswordHasher",
]

# Internationalization
LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

# Static files
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

# Add staticfiles dirs to help Django find the Swagger UI files
STATICFILES_DIRS = [
    BASE_DIR / ".venv" / "lib" / "python3.12" / "site-packages" / "drf_spectacular_sidecar" / "static",
]

# Default primary key field type
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Celery settings
CELERY_BROKER_URL = os.getenv("REDIS_URL", "redis://127.0.0.1:6379/0")
CELERY_RESULT_BACKEND = os.getenv("REDIS_URL", "redis://127.0.0.1:6379/0")
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_TIMEZONE = TIME_ZONE
CELERY_BEAT_SCHEDULER = "django_celery_beat.schedulers:DatabaseScheduler"
# Celery security settings
CELERY_TASK_ACKS_LATE = True
CELERY_WORKER_MAX_TASKS_PER_CHILD = 1000  # Restart worker after 1000 tasks

# Cache settings
CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": os.getenv("REDIS_URL", "redis://127.0.0.1:6379/1"),
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
            "SOCKET_CONNECT_TIMEOUT": 5,
            "SOCKET_TIMEOUT": 5,
            "COMPRESSOR": "django_redis.compressors.zlib.ZlibCompressor",  # Use compression for larger values
            "IGNORE_EXCEPTIONS": True,  # Don't crash on Redis connection issues
            "CONNECTION_POOL_KWARGS": {
                "max_connections": 100,
                "retry_on_timeout": True,
            },
            "PASSWORD": os.getenv("REDIS_PASSWORD", None),  # Redis password if set
        },
        "KEY_PREFIX": "remitscout",
    },
    "providers": {  # Specific cache for provider data (longer TTL)
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": os.getenv("REDIS_URL", "redis://127.0.0.1:6379/2"),
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
            "IGNORE_EXCEPTIONS": True,
            "PASSWORD": os.getenv("REDIS_PASSWORD", None),  # Redis password if set
        },
        "KEY_PREFIX": "provider",
    },
}

# Cache timeout settings (TTL) in seconds
QUOTE_CACHE_TTL = 60 * 30  # 30 minutes for quotes
PROVIDER_CACHE_TTL = 60 * 60 * 24  # 24 hours for provider details
CORRIDOR_CACHE_TTL = 60 * 60 * 12  # 12 hours for corridor availability
CORRIDOR_RATE_CACHE_TTL = 60 * 60 * 3  # 3 hours for corridor rate data (exchange rates, fees)
JITTER_MAX_SECONDS = 60  # Maximum jitter in seconds to prevent thundering herd

# Enable the cache middleware
CACHE_MIDDLEWARE_ALIAS = "default"
CACHE_MIDDLEWARE_SECONDS = 60 * 5  # 5 minutes
CACHE_MIDDLEWARE_KEY_PREFIX = "middleware"

# REST Framework settings
REST_FRAMEWORK = {
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 10,
    "DEFAULT_FILTER_BACKENDS": [
        "django_filters.rest_framework.DjangoFilterBackend",
    ],
    # Add Spectacular as the default schema generator
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    # Add throttling for rate limiting
    "DEFAULT_THROTTLE_CLASSES": [
        "rest_framework.throttling.AnonRateThrottle",
        "rest_framework.throttling.UserRateThrottle"
    ],
    "DEFAULT_THROTTLE_RATES": {
        "anon": os.getenv("THROTTLE_RATE_ANON", "60/minute"),
        "user": os.getenv("THROTTLE_RATE_USER", "300/minute"),
    },
    # Add authentication classes
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.SessionAuthentication",
        "rest_framework.authentication.TokenAuthentication",
    ],
    # Exception handling
    "EXCEPTION_HANDLER": "rest_framework.views.exception_handler",
    # Content type validation
    "DEFAULT_PARSER_CLASSES": [
        "rest_framework.parsers.JSONParser",
        "rest_framework.parsers.FormParser",
        "rest_framework.parsers.MultiPartParser",
    ],
}

# DRF Spectacular settings
SPECTACULAR_SETTINGS = {
    "TITLE": "RemitScout API",
    "DESCRIPTION": "API for comparing remittance rates across providers",
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
    # Use SIDECAR values for Swagger UI instead of module paths
    "SWAGGER_UI_DIST": "SIDECAR",
    "SWAGGER_UI_FAVICON_HREF": "SIDECAR",
    "REDOC_DIST": "SIDECAR",
    "SWAGGER_UI_SETTINGS": {
        "deepLinking": True,
        "persistAuthorization": True,
        "displayOperationId": True,
        "docExpansion": "list",
        "syntaxHighlight.theme": "agate",
        "filter": True,
    },
    "APPEND_COMPONENTS": {},
    "DISABLE_ERRORS_AND_WARNINGS": False,
    "SORT_OPERATIONS": False,
}

# Logging configuration
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "{levelname} {asctime} {module} {process:d} {thread:d} {message}",
            "style": "{",
        },
        "json": {
            "()": "json_log_formatter.JSONFormatter",
        },
    },
    "filters": {
        "require_debug_false": {
            "()": "django.utils.log.RequireDebugFalse",
        },
        "require_debug_true": {
            "()": "django.utils.log.RequireDebugTrue",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "verbose",
        },
        "json_file": {
            "class": "logging.handlers.TimedRotatingFileHandler",
            "filename": os.path.join(BASE_DIR, "logs/remitscout.json"),
            "when": "midnight",
            "interval": 1,
            "backupCount": 30,
            "formatter": "json",
        },
        "error_file": {
            "class": "logging.handlers.TimedRotatingFileHandler",
            "filename": os.path.join(BASE_DIR, "logs/error.log"),
            "when": "midnight",
            "interval": 1,
            "backupCount": 30,
            "formatter": "verbose",
            "level": "ERROR",
        },
        "security_file": {
            "class": "logging.handlers.TimedRotatingFileHandler",
            "filename": os.path.join(BASE_DIR, "logs/security.log"),
            "when": "midnight",
            "interval": 1,
            "backupCount": 90,  # Keep longer history for security logs
            "formatter": "json",
        },
        "mail_admins": {
            "level": "ERROR",
            "filters": ["require_debug_false"],
            "class": "django.utils.log.AdminEmailHandler",
        },
    },
    "loggers": {
        "django": {
            "handlers": ["console", "json_file"],
            "level": "INFO",
        },
        "django.server": {
            "handlers": ["console", "json_file"],
            "level": "INFO",
            "propagate": False,
        },
        "django.request": {
            "handlers": ["console", "error_file", "mail_admins"],
            "level": "ERROR",
            "propagate": False,
        },
        "django.security": {
            "handlers": ["console", "security_file", "mail_admins"],
            "level": "INFO",
            "propagate": False,
        },
        "remit_scout": {
            "handlers": ["console", "json_file"],
            "level": "INFO",
            "propagate": False,
        },
        "quotes": {
            "handlers": ["console", "json_file"],
            "level": "INFO",
            "propagate": False,
        },
        "providers": {
            "handlers": ["console", "json_file"],
            "level": "INFO",
            "propagate": False,
        },
        "aggregator": {
            "handlers": ["console", "json_file"],
            "level": "INFO",
            "propagate": False,
        },
    },
    "root": {
        "handlers": ["console", "error_file"],
        "level": os.getenv("DJANGO_LOG_LEVEL", "WARNING"),
    },
}

# Security settings for production
if not DEBUG:
    # HTTPS/SSL settings
    SECURE_SSL_REDIRECT = True
    SECURE_HSTS_SECONDS = 31536000  # 1 year
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
    
    # Session and cookie settings
    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    CSRF_COOKIE_SECURE = True
    CSRF_COOKIE_HTTPONLY = True
    CSRF_COOKIE_SAMESITE = "Lax"
    
    # Content security
    SECURE_CONTENT_TYPE_NOSNIFF = True
    SECURE_REFERRER_POLICY = "strict-origin-when-cross-origin"
    
    # Email configuration for error reporting
    ADMINS = [("Admin", os.getenv("ADMIN_EMAIL", "admin@example.com"))]
    SERVER_EMAIL = os.getenv("SERVER_EMAIL", "errors@example.com")
    EMAIL_HOST = os.getenv("EMAIL_HOST", "smtp.example.com")
    EMAIL_PORT = int(os.getenv("EMAIL_PORT", "587"))
    EMAIL_HOST_USER = os.getenv("EMAIL_HOST_USER", "")
    EMAIL_HOST_PASSWORD = os.getenv("EMAIL_HOST_PASSWORD", "")
    EMAIL_USE_TLS = True

# Ensure we have a logs directory
os.makedirs(os.path.join(BASE_DIR, "logs"), exist_ok=True)
