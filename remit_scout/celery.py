"""
Celery configuration for the RemitScout project.
"""
import os
from celery import Celery
from celery.schedules import crontab

# Set the default Django settings module for the 'celery' program
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'remit_scout.settings')

app = Celery('remit_scout')

# Using a string here means the worker doesn't have to serialize
# the configuration object to child processes.
app.config_from_object('django.conf:settings', namespace='CELERY')

# Load task modules from all registered Django app configs.
app.autodiscover_tasks()

# Configure periodic tasks
app.conf.beat_schedule = {
    'update-common-rates': {
        'task': 'apps.providers.tasks.update_all_rates',
        'schedule': crontab(minute='*/30'),  # Run every 30 minutes
        'args': (1000, 'USD', 'MX'),  # Example: $1000 USD to Mexico
    },
}

@app.task(bind=True)
def debug_task(self):
    """Debug task to verify Celery is working."""
    print(f'Request: {self.request!r}') 