from celery import shared_task
from django.utils import timezone
from datetime import timedelta
import os, logging
from django.conf import settings
from .models import Message

logger = logging.getLogger(__name__)

@shared_task
def archive_old_messages():
    threshold = timezone.now() - timedelta(days=30)
    count = Message.objects.filter(timestamp__lt=threshold, archived_at__isnull=True).update(archived_at=timezone.now())
    logger.info(f"Archived {count} old messages")
    return count

@shared_task
def cleanup_deleted_files():
    media_root = settings.MEDIA_ROOT
    for root, dirs, files in os.walk(media_root):
        for file in files:
            file_path = os.path.join(root, file)
            rel_path = os.path.relpath(file_path, media_root)
            if not Message.objects.filter(media_url__endswith=rel_path).exists():
                try:
                    os.remove(file_path)
                    logger.info(f"Removed orphan file: {rel_path}")
                except Exception as e:
                    logger.error(f"Failed to remove {rel_path}: {e}")

@shared_task
def scan_file(file_path):
    # Заглушка для антивируса (можно заменить на ClamAV)
    logger.info(f"Scanning file: {file_path}")
    return True
