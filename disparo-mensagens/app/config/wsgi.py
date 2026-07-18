import os
import logging
from pathlib import Path
from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

logger = logging.getLogger("gunicorn.error")


def _validate_environment():
    secret_key = os.getenv('DJANGO_SECRET_KEY')
    secret_key_file = os.getenv('DJANGO_SECRET_KEY_FILE')
    secret_key_file_exists = secret_key_file and Path(secret_key_file).is_file()

    missing = []
    if not secret_key and not secret_key_file_exists:
        missing.append('DJANGO_SECRET_KEY')

    if missing:
        msg = f"CRITICAL: missing required environment variables: {', '.join(missing)}."
        logger.critical(msg)
        raise RuntimeError(msg)


_validate_environment()

_django_app = get_wsgi_application()


def _with_sentry(wsgi_app):
    sentry_dsn = os.getenv("SENTRY_DSN")
    if not sentry_dsn:
        return wsgi_app
    try:
        import sentry_sdk
        from sentry_sdk.integrations.wsgi import SentryWsgiMiddleware

        if not sentry_sdk.is_initialized():
            sentry_sdk.init(
                dsn=sentry_dsn,
                integrations=[],
                traces_sample_rate=0.1,
                send_default_pii=False,
                environment=os.getenv("ENVIRONMENT", "production"),
            )
        return SentryWsgiMiddleware(wsgi_app)
    except ImportError:
        logger.warning("SENTRY_DSN definido mas sentry-sdk não instalado — ignorando")
        return wsgi_app


class HealthCheckMiddleware:
    def __init__(self, wsgi_app):
        self.wsgi_app = wsgi_app

    def __call__(self, environ, start_response):
        if environ.get("PATH_INFO") == "/health/":
            start_response("200 OK", [("Content-Type", "text/plain")])
            return [b"ok"]
        return self.wsgi_app(environ, start_response)


application = HealthCheckMiddleware(_with_sentry(_django_app))
