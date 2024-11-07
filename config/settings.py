"""
Django settings for config project.

Generated by 'django-admin startproject' using Django 5.1.1.

For more information on this file, see
https://docs.djangoproject.com/en/5.1/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/5.1/ref/settings/
"""

import os
from datetime import timedelta
from pathlib import Path

from celery.schedules import crontab

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/5.1/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.environ.get('SECRET_KEY', 'django-insecure--5x)i0j6)wox$gs=$q@x$p8qymrw@$nsk)_aa48vo=)**d)n6(')

REDIS_HOST = os.getenv('REDIS_HOST', 'localhost')
POSTGRES_HOST = os.getenv('POSTGRES_HOST', 'localhost')
MAILHOG_HOST = os.getenv('MAILHOG_HOST', 'localhost')
MINIO_HOST = os.getenv('MINIO_STORAGE_HOST', 'localhost')
ELASTIC_HOST = os.getenv('ELASTIC_HOST', 'localhost')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = os.getenv('DEBUG', 'True') == 'True'

ALLOWED_HOSTS = []

# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.sites',
    # Third party apps
    "rest_framework",
    'rest_framework.authtoken',
    "rest_framework_simplejwt",
    'django_filters',
    "drf_spectacular",
    'django_minio_backend.apps.DjangoMinioBackendConfig',
    'django_elasticsearch_dsl',
    'allauth',
    'allauth.account',
    'allauth.socialaccount',
    'allauth.socialaccount.providers.github',
    # Local apps
    'config',
    "apps.common",
    "apps.users",
    "apps.tasks",
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'allauth.account.middleware.AccountMiddleware',
    # Local middleware
    "apps.common.middlewares.ApiMiddleware",
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': ["templates/"],
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

WSGI_APPLICATION = 'config.wsgi.application'

REST_FRAMEWORK = {
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    'PAGE_SIZE': 100,
    "DATETIME_FORMAT": "%Y-%m-%dT%H:%M:%SZ",
    "DEFAULT_AUTHENTICATION_CLASSES": ("rest_framework_simplejwt.authentication.JWTAuthentication",),
    "DEFAULT_PERMISSION_CLASSES": ("rest_framework.permissions.IsAuthenticated",),
    "DEFAULT_RENDERER_CLASSES": ("rest_framework.renderers.JSONRenderer",),
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
}

# Database
# https://docs.djangoproject.com/en/5.1/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.getenv('POSTGRES_DB', 'db'),
        'USER': os.getenv('POSTGRES_USER', 'postgres'),
        'PASSWORD': os.getenv('POSTGRES_PASSWORD', 'postgres'),
        'HOST': POSTGRES_HOST,
        'PORT': os.getenv('POSTGRES_PORT', 5432),
    }
}

CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": f"redis://{REDIS_HOST}:6379/1",
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
        }
    }
}

AUTH_USER_MODEL = 'users.User'

# Password validation
# https://docs.djangoproject.com/en/5.1/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# Internationalization
# https://docs.djangoproject.com/en/5.1/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_TZ = True

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.1/howto/static-files/

STORAGES = {
    "default": {
        "BACKEND": "django_minio_backend.models.MinioBackend",
    },
    "staticfiles": {
        "BACKEND": "django_minio_backend.models.MinioBackendStatic",
    },
}

STATIC_URL = '/static/'
STATICFILES_STORAGE = 'django_minio_backend.models.MinioBackendStatic'
MINIO_STATIC_FILES_BUCKET = 'static'  # replacement for STATIC_ROOT

MEDIA_URL = '/media/'
DEFAULT_FILE_STORAGE = 'django_minio_backend.models.MinioBackend'
MINIO_MEDIA_FILES_BUCKET = 'media'  # replacement for MEDIA_ROOT

MINIO_ENDPOINT = f'{MINIO_HOST}:9000'
MINIO_ACCESS_KEY = os.getenv('MINIO_ROOT_USER', 'minio')
MINIO_SECRET_KEY = os.getenv('MINIO_ROOT_PASSWORD', 'minio123')
MINIO_USE_HTTPS = False

MINIO_PUBLIC_BUCKETS = ['static', ]
MINIO_PRIVATE_BUCKETS = ['media', ]

MINIO_CONSISTENCY_CHECK_ON_START = True

# Default primary key field type
# https://docs.djangoproject.com/en/5.1/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

SPECTACULAR_SETTINGS = {
    "TITLE": "EBS Task Management System",
    "DESCRIPTION": "EBS Task Management System",
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": True,
    'COMPONENT_SPLIT_REQUEST': True,
}

EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = MAILHOG_HOST
EMAIL_PORT = 1025
EMAIL_USE_TLS = False
DEFAULT_FROM_EMAIL = 'noreply@ebs-task-management.local'

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(days=1),
}

CELERY_BROKER_URL = f'redis://{REDIS_HOST}:6379/0'
CELERY_RESULT_BACKEND = f'redis://{REDIS_HOST}:6379/0'
# Optional: Add these for more configuration
CELERY_ACCEPT_CONTENT = ['application/json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'

CELERY_BEAT_SCHEDULE = {
    'send-weekly-reports': {
        'task': 'apps.tasks.tasks.send_weekly_report',
        'schedule': crontab(hour='8', minute='0', day_of_week='1'),  # Monday at 8 AM
    }
}

ELASTICSEARCH_DSL = {
    'default': {
        'hosts': f'http://{ELASTIC_HOST}:9200',
        "http_auth": ("elastic", "LpHtxnsBqjxJjd=XqdL1"),
    }
}

SITE_ID = 1

AUTHENTICATION_BACKENDS = [
    'django.contrib.auth.backends.ModelBackend',
    'allauth.account.auth_backends.AuthenticationBackend',
]

REDIRECT_URI = os.getenv('REDIRECT_URI')
SOCIALACCOUNT_PROVIDERS = {
    'github': {
        'APP': {
            'client_id': f'{os.getenv('GITHUB_CLIENT_ID')}',
            'secret': f'{os.getenv('GITHUB_SECRET')}',
            'key': '',
            "redirect_uri": REDIRECT_URI,
        }
    }
}

ACCOUNT_EMAIL_VERIFICATION = 'none'
ACCOUNT_USER_MODEL_USERNAME_FIELD = None
ACCOUNT_AUTHENTICATION_METHOD = 'email'
ACCOUNT_EMAIL_REQUIRED = True
ACCOUNT_USERNAME_REQUIRED = False
