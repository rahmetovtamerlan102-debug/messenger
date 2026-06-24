import os
from celery import Celery
from celery.schedules import crontab

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'messenger.settings')
app = Celery('messenger')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()

app.conf.beat_schedule = {
    'archive-old-messages': {
        'task': 'chat.tasks.archive_old_messages',
        'schedule': crontab(hour=2, minute=0),
    },
    'cleanup-deleted-files': {
        'task': 'chat.tasks.cleanup_deleted_files',
        'schedule': crontab(hour=3, minute=0),
    },
}
