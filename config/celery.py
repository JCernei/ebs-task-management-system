import os
from celery import Celery
import logging
from config import settings

logger = logging.getLogger(__name__)
# Set the default Django settings module
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

# Create Celery app
app = Celery('config')

# Load config from Django settings
app.config_from_object('django.conf:settings', namespace='CELERY')

logger.info(f"Initializing Celery with broker URL: {settings.CELERY_BROKER_URL}")
# Autodiscover tasks from all registered Django apps
app.autodiscover_tasks()

@app.task(bind=True)
def debug_task(self):
    logger.info(f'Request: {self.request!r}')