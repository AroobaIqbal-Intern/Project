"""
Celery configuration for the reference_graph project.
"""
import os
from celery import Celery

# Set the default Django settings module for the 'celery' program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'reference_graph.settings')

app = Celery('reference_graph')

# Using a string here means the worker doesn't have to serialize
# the configuration object to child processes.
app.config_from_object('django.conf:settings', namespace='CELERY')

# Load task modules from all registered Django app configs.
app.autodiscover_tasks()


@app.task(bind=True)
def debug_task(self):
    print(f'Request: {self.request!r}')


# Celery Beat Schedule (for periodic tasks)
app.conf.beat_schedule = {
    'process-pending-papers': {
        'task': 'papers.tasks.process_pending_papers',
        'schedule': 300.0,  # Every 5 minutes
    },
    'update-reference-graph': {
        'task': 'papers.tasks.update_reference_graph',
        'schedule': 3600.0,  # Every hour
    },
    'cleanup-old-files': {
        'task': 'papers.tasks.cleanup_old_files',
        'schedule': 86400.0,  # Every day
    },
}
