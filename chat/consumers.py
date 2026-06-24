import json, logging
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth.models import User
from rest_framework_simplejwt.tokens import AccessToken
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from django.core.cache import cache
from django.utils import timezone
from .models import Chat, Message, MessageReaction
from utils.rate_limiter import DistributedRateLimiter

logger = logging.getLogger(__name__)
rate_limiter = DistributedRateLimiter('ws', 10, 2)

class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        headers = dict(self.scope['headers'])
        auth_header = headers.get(b'authorization', b'').decode()
        token = None
        if auth_header.startswith('Bearer '):
            token = auth_header.split(' ')[1]
        if not token:
            await self.close(); return
        try:
            user = await self.get_user_from_token(token)
            if not user:
                await self.close(); return
        except Exception:
            await self.close(); return
        self.user = user
        self.room_name = self.scope['url_route']['kwargs']['room_name']
        try:
            chat = await self.get_chat_by_id(self.room_name)
            if not chat or not await self.is_participant(chat, user):
                await self.close(); return
        except Exception:
            await self.close(); return
        self.chat = chat
        self.room_group_name = f'chat_{self.room_name}'
        await self.set_online(True)
        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        if hasattr(self, 'room_group_name'):
            await self.channel_layer.group_discard(self.room_group_name, self.channel_name)
        await self.set_online(False)

    async def receive(self, text_data):
        if not rate_limiter.allow(f"user_{self.user.id}"):
            await self.send(text_data=json.dumps({'error': 'Too many messages'})); return
        try:
            data = json.loads(text_data)
        except json.JSONDecodeError:
            await self.send(text_data=json.dumps({'error': 'Invalid JSON'})); return
        action = data.get('action', 'message')
        try:
            if action == 'typing':
                await self.send_typing_status()
            elif action == 'read':
                await self.mark_messages_read(data.get('message_ids', []))
            elif action == 'delivered':
                await self.mark_messages_delivered(data.get('message_ids', []))
            elif action == 'ack':
                await self.send_ack(data.get('message_id'))
            elif action == 'message':
                msg_text = data.get('message', '').strip()
                media_url = data.get('media_url', '')
                reply_to_id = data.get('reply_to')
                is_forwarded = data.get('forwarded', False)
                if not msg_text and not media_url:
                    await self.send(text_data=json.dumps({'error': 'Empty message'})); return
                if len(msg_text) > 5000:
                    await self.send(text_data=json.dumps({'error': 'Message too long'})); return
                reply_to = None
                if reply_to_id:
                    reply_to = await self.get_message(reply_to_id)
                    if reply_to.chat_id != self.chat.id:
                        await self.send(text_data=json.dumps({'error': 'Reply message from different chat'})); return
                msg = await self.save_message(self.chat, self.user, msg_text, media_url, reply_to_id, is_forwarded)
                recipients = await self.get_recipients()
                await self.channel_layer.group_send(
                    self.room_group_name,
                    {
                        'type': 'chat_message',
                        'message': msg.text,
                        'media_url': msg.media_url,
                        'sender': self.user.username,
                        'timestamp': str(msg.timestamp),
                        'msg_id': str(msg.id),
                        'reply_to': str(msg.reply_to_id) if msg.reply_to else None,
                        'is_forwarded': msg.is_forwarded,
                    }
                )
            elif action == 'reaction':
                if not await self.is_participant(self.chat, self.user):
                    await self.send(text_data=json.dumps({'error': 'Not in chat'})); return
                await self.handle_reaction(data)
            elif action == 'pin':
                msg = await self.get_message(data['message_id'])
                if not (self.user.is_staff or msg.sender_id == self.user.id):
                    await self.send(text_data=json.dumps({'error': 'Permission denied'})); return
                await self.handle_pin(data)
            elif action == 'delete':
                msg = await self.get_message(data['message_id'])
                if not (self.user.is_staff or msg.sender_id == self.user.id):
                    await self.send(text_data=json.dumps({'error': 'Permission denied'})); return
                await self.handle_delete(data)
        except Message.DoesNotExist:
            await self.send(text_data=json.dumps({'error': 'Message not found'}))
        except Chat.DoesNotExist:
            await self.send(text_data=json.dumps({'error': 'Chat not found'}))
        except Exception as e:
            logger.error(f"WebSocket error: {e}")
            await self.send(text_data=json.dumps({'error': 'Internal error'}))

    async def chat_message(self, event):
        await self.send(text_data=json.dumps(event))
    async def typing_status(self, event):
        await self.send(text_data=json.dumps({'type': 'typing', 'user': event['user']}))
    async def reaction_update(self, event):
        await self.send(text_data=json.dumps(event))
    async def pin_update(self, event):
        await self.send(text_data=json.dumps(event))
    async def delete_update(self, event):
        await self.send(text_data=json.dumps(event))

    @database_sync_to_async
    def get_user_from_token(self, token):
        try:
            access = AccessToken(token); user_id = access['user_id']; return User.objects.get(id=user_id)
        except (InvalidToken, TokenError, User.DoesNotExist):
            return None
    @database_sync_to_async
    def get_chat_by_id(self, chat_id):
        return Chat.objects.get(id=chat_id)
    @database_sync_to_async
    def is_participant(self, chat, user):
        return chat.participants.filter(id=user.id).exists()
    @database_sync_to_async
    def get_message(self, message_id):
        return Message.objects.get(id=message_id)
    @database_sync_to_async
    def save_message(self, chat, user, text, media_url, reply_to_id, is_forwarded):
        reply_to = None
        if reply_to_id:
            reply_to = Message.objects.get(id=reply_to_id)
        return Message.objects.create(
            chat=chat, sender=user, text=text, media_url=media_url if media_url else None,
            reply_to=reply_to, is_forwarded=is_forwarded,
        )
    @database_sync_to_async
    def get_recipients(self):
        return list(self.chat.participants.exclude(id=self.user.id))
    @database_sync_to_async
    def set_online(self, status):
        cache.set(f'online_{self.user.id}', status, timeout=30)
        profile = self.user.profile
        profile.is_online = status
        profile.last_seen = timezone.now()
        profile.save()
    @database_sync_to_async
    def mark_messages_read(self, msg_ids):
        for msg_id in msg_ids:
            msg = Message.objects.get(id=msg_id); msg.read_by.add(self.user.id)
    @database_sync_to_async
    def mark_messages_delivered(self, msg_ids):
        for msg_id in msg_ids:
            msg = Message.objects.get(id=msg_id); msg.delivered_to.add(self.user.id)
    async def send_ack(self, msg_id):
        await self.send(text_data=json.dumps({'type': 'ack', 'msg_id': msg_id}))
    @database_sync_to_async
    def handle_reaction_db(self, data):
        msg = Message.objects.get(id=data['message_id'])
        emoji = data['emoji']
        MessageReaction.objects.filter(message=msg, user=self.user, emoji=emoji).delete()
        MessageReaction.objects.create(message=msg, user=self.user, emoji=emoji)
        reactions = {}
        for r in msg.reaction_set.all():
            reactions[r.emoji] = reactions.get(r.emoji, 0) + 1
        msg.reactions = reactions
        msg.save()
        return {'message_id': str(msg.id), 'emoji': emoji, 'user': self.user.username}
    async def handle_reaction(self, data):
        result = await self.handle_reaction_db(data)
        await self._send_to_group('reaction_update', result)
    async def _send_to_group(self, event_type, data):
        await self.channel_layer.group_send(self.room_group_name, {'type': event_type, **data})
    @database_sync_to_async
    def handle_pin_db(self, data):
        msg = Message.objects.get(id=data['message_id']); msg.is_pinned = not msg.is_pinned; msg.save()
        return {'message_id': str(msg.id), 'pinned': msg.is_pinned}
    async def handle_pin(self, data):
        result = await self.handle_pin_db(data); await self._send_to_group('pin_update', result)
    @database_sync_to_async
    def handle_delete_db(self, data):
        msg = Message.objects.get(id=data['message_id'])
        if data.get('for_all', False):
            msg.is_deleted = True
            msg.save()
        return {'message_id': str(msg.id), 'for_all': data.get('for_all', False)}
    async def handle_delete(self, data):
        result = await self.handle_delete_db(data); await self._send_to_group('delete_update', result)
