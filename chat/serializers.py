from rest_framework import serializers
from django.contrib.auth.models import User
from .models import Chat, Message, UserProfile, MessageReaction

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('id', 'username', 'first_name', 'last_name')

class UserProfileSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    class Meta:
        model = UserProfile
        fields = ('user', 'avatar', 'bio', 'last_seen', 'is_online')

class ChatSerializer(serializers.ModelSerializer):
    participants = UserSerializer(many=True, read_only=True)
    class Meta:
        model = Chat
        fields = ('id', 'name', 'is_group', 'participants', 'created_at')

class MessageSerializer(serializers.ModelSerializer):
    sender = UserSerializer(read_only=True)
    reply_to = serializers.PrimaryKeyRelatedField(read_only=True)
    reactions = serializers.JSONField(read_only=True)
    class Meta:
        model = Message
        fields = (
            'id', 'chat', 'sender', 'text', 'media_url', 'media_type',
            'voice_duration', 'reply_to', 'is_forwarded', 'is_pinned',
            'reactions', 'read_by', 'delivered_to', 'is_deleted',
            'timestamp', 'updated_at'
        )

class MessageReactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = MessageReaction
        fields = ('id', 'message', 'user', 'emoji', 'created_at')
