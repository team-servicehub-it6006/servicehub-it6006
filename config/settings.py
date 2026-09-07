"""
Django settings for ServiceHub.

One settings module. Production behaviour is switched on by environment variables so that the
same code runs in both places. Nothing secret lives in this file.
"""
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent


def env_flag(name, default='0'):
    return os.environ.get(name, default) == '1'


# Deliberately no fallback outside development. If the variable is missing we want a loud failure
# at start-up rather than a public site quietly running on a key that is sitting in the repository.
SECRET_KEY = os.environ.get('DJANGO_SECRET_KEY')
DEBUG = env_flag('DJANGO_DEBUG', '1')
if not SECRET_KEY:
    if DEBUG:
        SECRET_KEY = 'dev-only-not-for-production-do-not-copy-this'
    else:
        raise RuntimeError('DJANGO_SECRET_KEY must be set when DEBUG is off.')

ALLOWED_HOSTS = [h for h in os.environ.get(
    'DJANGO_ALLOWED_HOSTS', 'localhost,127.0.0.1,testserver').split(',') if h]

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    'accounts',
    'services',
    'bookings',
    'core',
]

# Email is the login field and the three roles are auth Groups, so the whole of Django's
# permission machinery keeps working. See accounts/models.py.
AUTH_USER_MODEL = 'accounts.User'

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
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

# SQLite locally, PostgreSQL in production. Nothing else in the codebase knows the difference.
if os.environ.get('DATABASE_URL'):
    import dj_database_url
    DATABASES = {'default': dj_database_url.parse(os.environ['DATABASE_URL'], conn_max_age=600)}
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    # Raised from Django's default of 8. Twelve characters is the single cheapest improvement
    # we can make to password strength and it costs the user nothing but typing.
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
     'OPTIONS': {'min_length': 12}},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LANGUAGE_CODE = 'en-nz'
TIME_ZONE = 'Pacific/Auckland'
USE_I18N = True
USE_TZ = True

STATIC_URL = 'static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
