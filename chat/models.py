import uuid
from django.db import models
from django.contrib.auth.models import User
from django.contrib.postgres.search import SearchVectorField
from django.contrib.postgres.indexes import GinIndex

class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    avatar = models.ImageField(upload_to='avatars/', blank=True, null=True)
    bio = models.TextField(blank=True)
    last_seen = models.DateTimeField(auto_now=True)
    is_online = models.BooleanField(default=False)

class Chat(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100, blank=True)
    is_group = models.BooleanField(default=False)
    participants = models.ManyToManyField(User, related_name='chats')
    created_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)
    class Meta:
        indexes = [models.Index(fields=['created_at'])]

class Message(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    chat = models.ForeignKey(Chat, on_delete=models.CASCADE, related_name='messages')
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_messages')
    text = models.TextField(blank=True)
    media_url = models.URLField(max_length=500, blank=True, null=True)
    media_type = models.CharField(max_length=20, blank=True)
    voice_duration = models.IntegerField(blank=True, null=True)
    reply_to = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, related_name='replies')
    is_forwarded = models.BooleanField(default=False)
    is_pinned = models.BooleanField(default=False)
    reactions = models.JSONField(default=dict, blank=True)
    read_by = models.ManyToManyField(User, related_name='read_messages', blank=True)
    delivered_to = models.ManyToManyField(User, related_name='delivered_messages', blank=True)
    is_deleted = models.BooleanField(default=False)
    archived_at = models.DateTimeField(null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    search_vector = SearchVectorField(null=True, blank=True)
    class Meta:
        indexes = [
            models.Index(fields=['chat', 'timestamp']),
            models.Index(fields=['sender']),
            GinIndex(fields=['search_vector']),
        ]
        ordering = ['-timestamp']

class MessageReaction(models.Model):
    message = models.ForeignKey(Message, on_delete=models.CASCADE, related_name='reaction_set')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    emoji = models.CharField(max_length=20)
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta:
        unique_together = ('message', 'user', 'emoji')
