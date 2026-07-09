import importlib.util
import os
from django.utils.translation import gettext_lazy as _
from pathlib import Path
from datetime import timedelta
from urllib.parse import quote
from django.templatetags.static import static
from django.urls import reverse_lazy

import environ

BASE_DIR = Path(__file__).resolve().parent.parent

env = environ.Env(
    DEBUG=(bool, False),
)
environ.Env.read_env(BASE_DIR / '.env')


def _read_env_secret(name, default=None):
    secret_file = os.getenv(f'{name}_FILE')
    if secret_file:
        secret_path = Path(secret_file)
        if not secret_path.is_file():
            raise ValueError(f'{name}_FILE aponta para um arquivo inexistente: {secret_file}')
        return secret_path.read_text(encoding='utf-8').strip()

    value = os.getenv(name)
    if value is None or value == '':
        return default
    return value.strip()


def _build_postgres_url():
    postgres_password = _read_env_secret('POSTGRES_PASSWORD')
    if postgres_password:
        postgres_user = os.getenv('POSTGRES_USER', 'disparo_user')
        postgres_host = os.getenv('POSTGRES_HOST', 'disparo_postgres')
        postgres_port = os.getenv('POSTGRES_PORT', '5432')
        postgres_db = os.getenv('POSTGRES_DB', 'disparo_db')

        return (
            f'postgres://{quote(postgres_user, safe="")}:{quote(postgres_password, safe="")}@'
            f'{postgres_host}:{postgres_port}/{postgres_db}'
        )

    database_url = os.getenv('DATABASE_URL')
    if database_url:
        return database_url

    raise ValueError('DATABASE_URL ou POSTGRES_PASSWORD_FILE deve estar definido')


def _build_redis_url(database='0'):
    redis_password = _read_env_secret('REDIS_PASSWORD')
    if redis_password:
        redis_host = os.getenv('REDIS_HOST', 'disparo_redis')
        redis_port = os.getenv('REDIS_PORT', '6379')

        return f'redis://:{quote(redis_password, safe="")}@{redis_host}:{redis_port}/{database}'

    redis_url = os.getenv('REDIS_URL')
    if redis_url:
        return redis_url

    raise ValueError('REDIS_URL ou REDIS_PASSWORD_FILE deve estar definido')


DATABASE_URL = _build_postgres_url()
REDIS_URL = _build_redis_url()
CELERY_BROKER_URL = os.getenv('CELERY_BROKER_URL', REDIS_URL)
CAMPANHAS_DELAY_MIN_SECONDS = env.int('CAMPANHAS_DELAY_MIN_SECONDS', default=20)
CAMPANHAS_DELAY_MAX_SECONDS = env.int('CAMPANHAS_DELAY_MAX_SECONDS', default=120)


os.environ['DATABASE_URL'] = DATABASE_URL
os.environ['REDIS_URL'] = REDIS_URL
os.environ['CELERY_BROKER_URL'] = CELERY_BROKER_URL


if not env.bool('DJANGO_DEBUG', default=False) and not _read_env_secret('DJANGO_SECRET_KEY'):
    raise ValueError('DJANGO_SECRET_KEY deve estar definido em produção!')

if not env.bool('DJANGO_DEBUG', default=False) and not env.list('DJANGO_ALLOWED_HOSTS', default=[]):
    raise ValueError('DJANGO_ALLOWED_HOSTS deve estar definido em produção!')

SECRET_KEY = _read_env_secret('DJANGO_SECRET_KEY')
DEBUG = env.bool('DJANGO_DEBUG', default=False)
ALLOWED_HOSTS = env.list('DJANGO_ALLOWED_HOSTS', default=['localhost', '127.0.0.1', 'canevaspub.duckdns.org'])
CSRF_TRUSTED_ORIGINS = env.list('CSRF_TRUSTED_ORIGINS', default=[])

DJANGO_APPS = [
    'unfold',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
]

THIRD_PARTY_APPS = [
    'rest_framework',
    'corsheaders',
    'celery',
    'django_celery_beat',
    'django_celery_results',
    'two_factor',
    'django_otp',
    'django_otp.plugins.otp_totp',
    'django_otp.plugins.otp_static',
    'axes',
    'csp',
]

LOCAL_APPS = [
    'contatos',
    'campanhas',
    'envios',
]

HAS_DEBUG_TOOLBAR = importlib.util.find_spec('debug_toolbar') is not None

DEV_APPS = ['debug_toolbar'] if DEBUG and HAS_DEBUG_TOOLBAR else []

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS + DEV_APPS

UNFOLD = {
    "SITE_TITLE": "Campanhas de Mensagens",
    "SITE_HEADER": "Campanhas de Mensagens",
    "SITE_SYMBOL": "drag_click",
    "SHOW_HISTORY": True,
    "SHOW_VIEW_ON_SITE": True,
    "SHOW_BACK_BUTTON": True,
    "ENVIRONMENT": "config.settings.environment_callback",
    "DASHBOARD_CALLBACK": "config.dashboard.dashboard_callback",

    "COLORS": {
        "base": {
            "50": "oklch(98.5% 0 0)",
            "100": "oklch(97% 0 0)",
            "200": "oklch(92.2% 0 0)",
            "300": "oklch(87% 0 0)",
            "400": "oklch(70.8% 0 0)",
            "500": "oklch(55.6% 0 0)",
            "600": "oklch(43.9% 0 0)",
            "700": "oklch(37.1% 0 0)",
            "800": "oklch(26.9% 0 0)",
            "900": "oklch(20.5% 0 0)",
            "950": "oklch(14.5% 0 0)",
        },
        "primary": {
            "50": "oklch(98.7% .022 95.277)",
            "100": "oklch(96.2% .059 95.617)",
            "200": "oklch(92.4% .12 95.746)",
            "300": "oklch(87.9% .169 91.605)",
            "400": "oklch(82.8% .189 84.429)",
            "500": "oklch(76.9% .188 70.08)",
            "600": "oklch(66.6% .179 58.318)",
            "700": "oklch(55.5% .163 48.998)",
            "800": "oklch(47.3% .137 46.201)",
            "900": "oklch(41.4% .112 45.904)",
            "950": "oklch(27.9% .077 45.635)",
        },
    },

    "SIDEBAR": {
        "show_search": True,
        "show_all_applications": True,
        "navigation": [
            {
                "separator": True,
                "items": [
                    {
                        "title": _("Dashboard"),
                        "icon": "dashboard",
                        "link": reverse_lazy("admin:index"),
                    },
                ],
            },
            {
                "title": _("Campanhas"),
                "icon": "campaign",
                "separator": True,
                "collapsible": True,
                "items": [
                    {
                        "title": _("Campanhas"),
                        "icon": "campaign",
                        "link": reverse_lazy("admin:campanhas_campanha_changelist"),
                    },
                    {
                        "title": _("Templates de Mensagem"),
                        "icon": "description",
                        "link": reverse_lazy("admin:campanhas_templatemensagem_changelist"),
                    },
                ],
            },
            {
                "title": _("Contatos"),
                "icon": "contacts",
                "separator": True,
                "collapsible": True,
                "items": [
                    {
                        "title": _("Contatos"),
                        "icon": "contacts",
                        "link": reverse_lazy("admin:contatos_contato_changelist"),
                    },
                    {
                        "title": _("Grupos de Contatos"),
                        "icon": "groups",
                        "link": reverse_lazy("admin:contatos_grupocontatos_changelist"),
                    },
                ],
            },
            {
                "title": _("Envios"),
                "icon": "send",
                "separator": True,
                "collapsible": True,
                "items": [
                    {
                        "title": _("Envios"),
                        "icon": "send",
                        "link": reverse_lazy("admin:envios_envio_changelist"),
                    },
                ],
            },
            {
                "title": _("Administração"),
                "separator": True,
                "collapsible": True,
                "items": [
                    {
                        "title": _("Task Results"),
                        "icon": "task_alt",
                        "link": reverse_lazy("admin:django_celery_results_taskresult_changelist"),
                        "permission": lambda request: request.user.is_superuser,
                    },
                    {
                        "title": _("Usuários"),
                        "icon": "person",
                        "link": reverse_lazy("admin:auth_user_changelist"),
                        "permission": lambda request: request.user.is_superuser,
                    },
                    {
                        "title": _("Grupos"),
                        "icon": "group",
                        "link": reverse_lazy("admin:auth_group_changelist"),
                        "permission": lambda request: request.user.is_superuser,
                    },
                ],
            },
        ],
    },

    "TABS": [],
}


def environment_callback(request):
    from django.conf import settings
    if settings.DEBUG:
        return ["Desenvolvimento", "warning"]
    return ["Produção", "danger"]


MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'csp.middleware.CSPMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.locale.LocaleMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django_otp.middleware.OTPMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'axes.middleware.AxesMiddleware',
]

if DEBUG and HAS_DEBUG_TOOLBAR:
    MIDDLEWARE += ['debug_toolbar.middleware.DebugToolbarMiddleware']

ROOT_URLCONF = 'config.urls'
WSGI_APPLICATION = 'config.wsgi.application'

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

DATABASES = {
    'default': {
        **env.db('DATABASE_URL'),
        'CONN_MAX_AGE': env.int('DB_CONN_MAX_AGE', default=600),
    }
}

if DATABASES['default']['ENGINE'] != 'django.db.backends.sqlite3':
    DATABASES['default']['OPTIONS'] = {
        'connect_timeout': env.int('DB_CONNECT_TIMEOUT', default=5),
    }

if not DEBUG:
    CACHES = {
        'default': {
            'BACKEND': 'django.core.cache.backends.redis.RedisCache',
            'LOCATION': REDIS_URL,
        }
    }
else:
    CACHES = {
        'default': {
            'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
            'LOCATION': 'disparo-cache',
        }
    }

CELERY_BROKER_URL = env('CELERY_BROKER_URL')
CELERY_RESULT_BACKEND = env('CELERY_RESULT_BACKEND', default='django-db')
CELERY_TIMEZONE = env('CELERY_TIMEZONE', default='America/Sao_Paulo')
CELERY_BEAT_SCHEDULER = 'django_celery_beat.schedulers:DatabaseScheduler'
CELERY_RESULT_EXTENDED = True
CELERY_TASK_TRACK_STARTED = True

PUBLIC_BASE_URL = env('PUBLIC_BASE_URL', default='http://localhost:8000')

EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = env('EMAIL_HOST')
EMAIL_PORT = env.int('EMAIL_PORT')
EMAIL_USE_TLS = env.bool('EMAIL_USE_TLS')
EMAIL_HOST_USER = env('EMAIL_HOST_USER')
EMAIL_HOST_PASSWORD = _read_env_secret('EMAIL_HOST_PASSWORD')
DEFAULT_FROM_EMAIL = EMAIL_HOST_USER

STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LOGIN_URL = 'two_factor:login'
LOGIN_REDIRECT_URL = 'two_factor:profile'

AXES_FAILURE_LIMIT = 5
AXES_COOLOFF_TIME = timedelta(minutes=1)
AXES_LOCKOUT_CALLABLE = None
AUTHENTICATION_BACKENDS = [
    'axes.backends.AxesStandaloneBackend',
    'django.contrib.auth.backends.ModelBackend',
]

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.TokenAuthentication',
        'rest_framework.authentication.SessionAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_THROTTLE_CLASSES': [
        'rest_framework.throttling.AnonRateThrottle',
        'rest_framework.throttling.UserRateThrottle',
    ],
    'DEFAULT_THROTTLE_RATES': {
        'anon': '100/hour',
        'user': '1000/hour',
    },
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 20,
}

EVOLUTION_API_URL = env('EVOLUTION_API_URL')
EVOLUTION_API_KEY = _read_env_secret('AUTHENTICATION_API_KEY')
EVOLUTION_INSTANCE_NAME = env('EVOLUTION_INSTANCE_NAME')
EVOLUTION_WEBHOOK_SECRET = _read_env_secret('EVOLUTION_WEBHOOK_SECRET')

OPT_OUT_TOKEN_EXPIRY_DAYS = env.int('OPT_OUT_TOKEN_EXPIRY_DAYS', default=30)

if not DEBUG:
    SECURE_HSTS_SECONDS = 31536000
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    SECURE_SSL_REDIRECT = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True

SESSION_COOKIE_HTTPONLY = True
SESSION_EXPIRE_AT_BROWSER_CLOSE = True
X_FRAME_OPTIONS = 'DENY'
SECURE_REFERRER_POLICY = 'strict-origin-when-cross-origin'

if not DEBUG:
    CONTENT_SECURITY_POLICY = {
        'DIRECTIVES': {
            'default-src': ("'self'",),
            'script-src': ("'self'", 'https://cdn.jsdelivr.net'),
            'style-src': ("'self'", "'unsafe-inline'"),
            'img-src': ("'self'", 'data:', 'https:'),
            'font-src': ("'self'",),
            'connect-src': ("'self'",),
        },
    }

LANGUAGE_CODE = 'pt-br'
TIME_ZONE = 'America/Sao_Paulo'
USE_I18N = True
USE_TZ = True

LANGUAGES = (
    ('pt-br', _('Português (Brasil)')),
    ('en', _('English')),
)

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
        'simple': {
            'format': '{levelname} {asctime} {message}',
            'style': '{',
        },
    },
    'filters': {
        'require_debug_false': {
            '()': 'django.utils.log.RequireDebugFalse',
        },
        'require_debug_true': {
            '()': 'django.utils.log.RequireDebugTrue',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'simple' if DEBUG else 'verbose',
        },
        'file': {
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': BASE_DIR / 'logs' / 'django.log',
            'maxBytes': 1024 * 1024 * 15,
            'backupCount': 10,
            'formatter': 'verbose',
        },
    },
    'root': {
        'handlers': ['console'] if DEBUG else ['console', 'file'],
        'level': 'DEBUG' if DEBUG else 'INFO',
    },
    'loggers': {
        'django': {
            'handlers': ['console'] if DEBUG else ['console', 'file'],
            'level': 'DEBUG' if DEBUG else 'INFO',
            'propagate': False,
        },
        'celery': {
            'handlers': ['console'] if DEBUG else ['console', 'file'],
            'level': 'INFO',
            'propagate': False,
        },
    },
}

if not DEBUG and env('SENTRY_DSN', default=None):
    try:
        import sentry_sdk
        from sentry_sdk.integrations.django import DjangoIntegration
        from sentry_sdk.integrations.celery import CeleryIntegration
        from sentry_sdk.integrations.redis import RedisIntegration

        sentry_sdk.init(
            dsn=env('SENTRY_DSN'),
            integrations=[
                DjangoIntegration(),
                CeleryIntegration(),
                RedisIntegration(),
            ],
            traces_sample_rate=0.1,
            send_default_pii=False,
            environment=env('ENVIRONMENT', default='production'),
        )
    except ImportError:
        pass

DEBUG_TOOLBAR_CONFIG = {
    'SHOW_TOOLBAR_CALLBACK': lambda r: False,
    'SHOW_TEMPLATE_CONTEXT': DEBUG,
    'ENABLE_STACKTRACES': DEBUG,
} if DEBUG else {}