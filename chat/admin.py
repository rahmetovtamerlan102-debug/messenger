from django.contrib import admin
from .models import Chat, Message, UserProfile, MessageReaction

admin.site.register(Chat)
admin.site.register(Message)
admin.site.register(UserProfile)
admin.site.register(MessageReaction)
