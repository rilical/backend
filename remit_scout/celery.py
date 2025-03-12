"""
Celery configuration for the RemitScout project.
"""
import os

from celery import Celery
from celery.schedules import crontab

# Set the default Django settings module for Celery
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "remit_scout.settings")

app = Celery("remit_scout")

# Use string names for task routing since Django settings aren't loaded yet
app.config_from_object("django.conf:settings", namespace="CELERY")

# Load tasks from all registered Django app configs
app.autodiscover_tasks()

# Configure periodic tasks
app.conf.beat_schedule = {
    "refresh-popular-corridors-hourly": {
        "task": "quotes.tasks.refresh_popular_corridor_caches",
        "schedule": crontab(minute=0),  # Run hourly at the start of the hour
        "args": (),
    },
    "refresh-popular-quotes-hourly": {
        "task": "quotes.tasks.refresh_popular_quote_caches",
        "schedule": crontab(minute=15),  # Run hourly at 15 minutes past the hour
        "args": (),
    },
    "clean-old-quotes-daily": {
        "task": "quotes.tasks.clean_old_quotes",
        "schedule": crontab(hour=2, minute=0),  # Run daily at 2:00 AM
        "args": (),
    },
    "refresh-cache-daily": {
        "task": "quotes.tasks.refresh_cache_daily",
        "schedule": crontab(hour=3, minute=0),  # Run daily at 3:00 AM
        "args": (),
    },
}


@app.task(bind=True)
def debug_task(self):
    """Debug task to verify Celery is working."""
    print(f"Request: {self.request!r}")
