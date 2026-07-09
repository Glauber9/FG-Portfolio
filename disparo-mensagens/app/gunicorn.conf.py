import logging
import multiprocessing
import os

bind = "0.0.0.0:8000"

workers = int(os.getenv("GUNICORN_WORKERS", multiprocessing.cpu_count() * 2 + 1))
worker_class = "sync"
worker_tmp_dir = "/dev/shm"

max_requests = int(os.getenv("GUNICORN_MAX_REQUESTS", "1000"))
max_requests_jitter = int(os.getenv("GUNICORN_MAX_REQUESTS_JITTER", "50"))
timeout = int(os.getenv("GUNICORN_TIMEOUT", "30"))
graceful_timeout = int(os.getenv("GUNICORN_GRACEFUL_TIMEOUT", "30"))

accesslog = "-"
errorlog = "-"
loglevel = os.getenv("GUNICORN_LOG_LEVEL", "info")

proc_name = "disparo-mensagens"


def on_starting(server):
    logging.getLogger("gunicorn.error").info(
        "Gunicorn iniciando — %d workers, timeout %ds", workers, timeout
    )


def on_exit(server):
    logging.getLogger("gunicorn.error").info("Gunicorn encerrando")