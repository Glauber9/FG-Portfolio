import logging
import logging.config
import os

from celery import Celery, signals
from django.conf import settings

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

app = Celery("config")

app.config_from_object("django.conf:settings", namespace="CELERY")

app.autodiscover_tasks()

app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="America/Sao_Paulo",
    enable_utc=True,
    result_extended=True,
    task_track_started=True,
    task_acks_late=True,
    task_acks_on_failure=False,
    task_reject_on_worker_lost=True,
    task_soft_time_limit=300,
    task_time_limit=360,
    task_ignore_result=False,
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=50,
    broker_connection_retry_on_startup=True,
    broker_connection_max_retries=20,
    broker_transport_options={
        "visibility_timeout": 43_200,
        "socket_keepalive": True,
    },
    task_routes={
        "campanhas.tasks.enviar_whatsapp": {"queue": "whatsapp"},
        "campanhas.tasks.enviar_email": {"queue": "email"},
    },
    task_annotations={
        "campanhas.tasks.enviar_whatsapp": {"rate_limit": "30/m"},
        "campanhas.tasks.enviar_email": {"rate_limit": "10/m"},
    },
)


@signals.setup_logging.connect
def on_celery_setup_logging(loglevel, logfile, format, colorize, **kwargs):
    logging.config.dictConfig(settings.LOGGING)


@signals.task_prerun.connect
def on_task_prerun(task_id, task, **kwargs):
    logging.getLogger("celery").info("Task %s [%s] starting", task.name, task_id)


@signals.task_failure.connect
def on_task_failure(task_id, exception, args, traceback, einfo, **kwargs):
    logging.getLogger("celery").error(
        "Task %s failed: %s",
        task_id,
        exception,
        exc_info=(type(exception), exception, traceback),
    )


@app.task(bind=True, ignore_result=True)
def debug_task(self):
    logging.getLogger("celery").info("Request: %s", self.request)