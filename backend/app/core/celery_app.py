import os
from celery import Celery

# Configure basic Celery setting mapping correctly to Redis
redis_url = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0")

celery_app = Celery(
    "breath_analyzer_worker",
    broker=redis_url,
    backend=redis_url,
    include=["app.services.satellite_engine"]
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    broker_connection_retry_on_startup=True
)

if __name__ == "__main__":
    celery_app.start()
