"""Minimal Celery application for Docker Compose worker/beat/flower services."""
from celery import Celery

from app.api.core.config import settings

celery_app = Celery(
    "eduboost",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
)
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Africa/Johannesburg",
    enable_utc=True,
)


@celery_app.task(name="eduboost.health.ping")
def ping() -> str:
    return "pong"
