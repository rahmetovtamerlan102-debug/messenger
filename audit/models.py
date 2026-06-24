from django.db import models
from django.contrib.auth.models import User

class AuditLog(models.Model):
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    action = models.CharField(max_length=100)
    details = models.JSONField(default=dict)
    ip = models.GenericIPAddressField(null=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    class Meta:
        indexes = [models.Index(fields=['user', 'timestamp'])]
