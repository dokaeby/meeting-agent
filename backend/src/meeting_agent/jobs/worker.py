from celery import Celery

from ..config import Settings
from ..db import make_database
from .runner import execute, pending

settings = Settings()
app = Celery("meeting_agent", broker=settings.redis_url)
app.conf.update(
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    worker_prefetch_multiplier=1,
    broker_connection_retry_on_startup=True,
    beat_schedule={
        "dispatch": {"task": "meeting.dispatch", "schedule": 10},
        "retention": {"task": "meeting.retention", "schedule": 3600},
    },
)


@app.task(name="meeting.execute")
def run(org, job_id):
    engine, factory = make_database(settings.database_url)
    try:
        execute(settings, factory, org, job_id)
    finally:
        engine.dispose()


@app.task(name="meeting.dispatch")
def dispatch():
    engine, factory = make_database(settings.database_url)
    try:
        for org, job_id in pending(factory):
            run.delay(org, job_id)
    finally:
        engine.dispose()


@app.task(name="meeting.retention")
def retention():
    from .retention import cleanup

    engine, factory = make_database(settings.database_url)
    try:
        cleanup(settings, factory)
    finally:
        engine.dispose()
