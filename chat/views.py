import os, uuid, magic
from PIL import Image
from io import BytesIO
from django.shortcuts import get_object_or_404
from django.http import JsonResponse
from django.contrib.auth.models import User
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.pagination import CursorPagination
from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from django.db.models import Q, Count
from django.core.cache import cache
from django.contrib.postgres.search import SearchQuery
from .models import Chat, Message, UserProfile, MessageReaction
from .serializers import (
    ChatSerializer, MessageSerializer, UserSerializer, UserProfileSerializer,
    MessageReactionSerializer
)
from utils.permissions import IsChatParticipant, IsSenderOrAdmin
from .tasks import scan_file   # Celery задача

ALLOWED_MIME_TYPES = {
    'image/jpeg', 'image/png', 'image/gif', 'image/webp',
    'video/mp4', 'video/quicktime',
    'application/pdf',
    'audio/mpeg', 'audio/ogg', 'audio/wav'
}
MAX_FILE_SIZE = 20 * 1024 * 1024
MIN_SEARCH_LENGTH = 3
MAX_SEARCH_RESULTS = 50

def health(request):
    return JsonResponse({"status": "ok"})

class RegisterView(APIView):
    permission_classes = [AllowAny]
    def post(self, request):
        username = request.data.get('username')
        password = request.data.get('password')
        if not username or not password:
            return Response({'error': 'username and password required'}, status=400)
        if len(username) < 3:
            return Response({'error': 'Username too short'}, status=400)
        if User.objects.filter(username=username).exists():
            return Response({'error': 'Username taken'}, status=400)
        try:
            validate_password(password)
        except ValidationError as e:
            return Response({'error': e.messages}, status=400)
        user = User.objects.create_user(username=username, password=password)
        return Response(UserSerializer(user).data, status=201)

class LoginView(APIView):
    permission_classes = [AllowAny]
    def post(self, request):
        username = request.data.get('username')
        password = request.data.get('password')
        user = authenticate(username=username, password=password)
        if not user:
            return Response({'error': 'Invalid credentials'}, status=401)
        refresh = RefreshToken.for_user(user)
        return Response({
            'refresh': str(refresh),
            'access': str(refresh.access_token),
            'user': UserSerializer(user).data
        })

class ProfileView(APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request):
        profile = request.user.profile
        serializer = UserProfileSerializer(profile)
        return Response(serializer.data)
    def put(self, request):
        profile = request.user.profile
        serializer = UserProfileSerializer(profile, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=400)

class UserSearchView(APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request):
        query = request.GET.get('q', '').strip()
        cache_key = f'user_search_{query}_{request.user.id}'
        cached = cache.get(cache_key)
        if cached is not None:
            return Response(cached)
        if len(query) < MIN_SEARCH_LENGTH:
            return Response({'results': []})
        users = User.objects.filter(
            Q(username__icontains=query) |
            Q(first_name__icontains=query)
        ).distinct()[:MAX_SEARCH_RESULTS]
        serializer = UserSerializer(users, many=True)
        cache.set(cache_key, serializer.data, timeout=60)
        return Response(serializer.data)

class ChatListView(APIView):
    permission_classes = [IsAuthenticated]
    throttle_scope = 'chat_create'

    def get(self, request):
        chats = request.user.chats.all().select_related()
        serializer = ChatSerializer(chats, many=True)
        return Response(serializer.data)

    def post(self, request):
        participants_ids = request.data.get('participants', [])
        is_group = request.data.get('is_group', False)
        name = request.data.get('name', '')
        if request.user.chats.count() >= 100:
            return Response({'error': 'Too many chats'}, status=400)
        if not is_group and len(participants_ids) == 1:
            other_user = get_object_or_404(User, id=participants_ids[0])
            existing = Chat.objects.filter(
                is_group=False
            ).annotate(
                cnt=Count("participants")
            ).filter(
                cnt=2,
                participants=request.user
            ).filter(
                participants=other_user
            ).first()
            if existing:
                serializer = ChatSerializer(existing)
                return Response(serializer.data, status=200)
        chat = Chat.objects.create(name=name, is_group=is_group)
        chat.participants.set(set([request.user.id] + participants_ids))
        serializer = ChatSerializer(chat)
        return Response(serializer.data, status=201)

class MessageListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, chat_id):
        chat = get_object_or_404(Chat, id=chat_id)
        if not chat.participants.filter(id=request.user.id).exists():
            return Response({'error': 'Not in chat'}, status=403)
        messages = chat.messages.filter(is_deleted=False).select_related('sender')
        paginator = CursorPagination()
        page = paginator.paginate_queryset(messages, request)
        serializer = MessageSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)

class MessageDetailView(APIView):
    permission_classes = [IsAuthenticated, IsSenderOrAdmin]

    def put(self, request, message_id):
        msg = get_object_or_404(Message, id=message_id)
        self.check_object_permissions(request, msg)
        new_text = request.data.get('text', '').strip()
        if len(new_text) > 5000:
            return Response({'error': 'Message too long'}, status=400)
        msg.text = new_text
        msg.save()
        return Response(MessageSerializer(msg).data)

    def delete(self, request, message_id):
        msg = get_object_or_404(Message, id=message_id)
        self.check_object_permissions(request, msg)
        msg.is_deleted = True
        msg.save()
        return Response(status=204)

class UploadView(APIView):
    permission_classes = [IsAuthenticated]
    throttle_scope = 'upload'

    def post(self, request):
        file = request.FILES.get('file')
        if not file:
            return Response({'error': 'No file'}, status=400)
        if file.size > MAX_FILE_SIZE:
            return Response({'error': f'File too large. Max {MAX_FILE_SIZE // (1024*1024)}MB'}, status=400)

        try:
            mime = magic.from_buffer(file.read(1024), mime=True)
            file.seek(0)
        except Exception:
            mime = None
        if mime not in ALLOWED_MIME_TYPES:
            return Response({'error': f'File type {mime} not allowed'}, status=400)

        if mime.startswith('image/'):
            try:
                img = Image.open(file)
                img.verify()
                file.seek(0)
                img = Image.open(file)
                img_clean = Image.new(img.mode, img.size)
                img_clean.putdata(list(img.getdata()))
                output = BytesIO()
                img_clean.save(output, format=img.format)
                output.seek(0)
                file = ContentFile(output.read(), name=file.name)
            except Exception:
                return Response({'error': 'Invalid image file'}, status=400)

        ext = os.path.splitext(file.name)[1].lower()
        allowed_exts = {'.jpg', '.jpeg', '.png', '.gif', '.webp', '.mp4', '.mov', '.pdf', '.mp3', '.ogg', '.wav'}
        if ext not in allowed_exts:
            return Response({'error': f'Extension {ext} not allowed'}, status=400)

        filename = f"{uuid.uuid4().hex}{ext}"
        path = default_storage.save(f"uploads/{filename}", file)
        url = default_storage.url(path)

        # Вызов Celery задачи для сканирования файла
        scan_file.delay(path)

        return Response({'url': url}, status=201)

class MessageCreateView(APIView):
    permission_classes = [IsAuthenticated, IsChatParticipant]
    throttle_scope = 'message_create'

    def post(self, request):
        chat_id = request.data.get('chat_id')
        text = request.data.get('text', '').strip()
        media_url = request.data.get('media_url', '')
        reply_to_id = request.data.get('reply_to')
        is_forwarded = request.data.get('is_forwarded', False)

        if not chat_id:
            return Response({'error': 'chat_id required'}, status=400)
        if not text and not media_url:
            return Response({'error': 'text or media required'}, status=400)
        if len(text) > 5000:
            return Response({'error': 'Message too long'}, status=400)

        chat = get_object_or_404(Chat, id=chat_id)
        self.check_object_permissions(request, chat)

        reply_to = None
        if reply_to_id:
            reply_to = get_object_or_404(Message, id=reply_to_id)
            if reply_to.chat != chat:
                return Response({'error': 'Reply message is from different chat'}, status=400)

        msg = Message.objects.create(
            chat=chat, sender=request.user, text=text,
            media_url=media_url if media_url else None,
            reply_to=reply_to, is_forwarded=is_forwarded,
        )

        from channels.layers import get_channel_layer
        from asgiref.sync import async_to_sync
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            f'chat_{chat.id}',
            {
                'type': 'chat_message',
                'message': msg.text,
                'media_url': msg.media_url,
                'sender': request.user.username,
                'timestamp': str(msg.timestamp),
                'msg_id': str(msg.id),
                'reply_to': str(msg.reply_to_id) if msg.reply_to else None,
                'is_forwarded': msg.is_forwarded,
            }
        )

        serializer = MessageSerializer(msg)
        return Response(serializer.data, status=201)

class ReactionView(APIView):
    permission_classes = [IsAuthenticated]
    def post(self, request, message_id):
        msg = get_object_or_404(Message, id=message_id)
        if not msg.chat.participants.filter(id=request.user.id).exists():
            return Response({'error': 'Not in chat'}, status=403)
        emoji = request.data.get('emoji')
        if not emoji:
            return Response({'error': 'emoji required'}, status=400)
        MessageReaction.objects.filter(message=msg, user=request.user, emoji=emoji).delete()
        reaction = MessageReaction.objects.create(message=msg, user=request.user, emoji=emoji)
        reactions = {}
        for r in msg.reaction_set.all():
            reactions[r.emoji] = reactions.get(r.emoji, 0) + 1
        msg.reactions = reactions
        msg.save()
        from channels.layers import get_channel_layer
        from asgiref.sync import async_to_sync
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            f'chat_{msg.chat.id}',
            {
                'type': 'reaction_update',
                'message_id': str(msg.id),
                'emoji': emoji,
                'user': request.user.username,
            }
        )
        return Response(MessageReactionSerializer(reaction).data, status=201)
    def delete(self, request, message_id):
        msg = get_object_or_404(Message, id=message_id)
        if not msg.chat.participants.filter(id=request.user.id).exists():
            return Response({'error': 'Not in chat'}, status=403)
        emoji = request.data.get('emoji')
        if not emoji:
            return Response({'error': 'emoji required'}, status=400)
        MessageReaction.objects.filter(message=msg, user=request.user, emoji=emoji).delete()
        reactions = {}
        for r in msg.reaction_set.all():
            reactions[r.emoji] = reactions.get(r.emoji, 0) + 1
        msg.reactions = reactions
        msg.save()
        return Response(status=204)

class PinView(APIView):
    permission_classes = [IsAuthenticated]
    def post(self, request, message_id):
        msg = get_object_or_404(Message, id=message_id)
        if not msg.chat.participants.filter(id=request.user.id).exists():
            return Response({'error': 'Not in chat'}, status=403)
        if not (request.user.is_staff or msg.sender == request.user):
            return Response({'error': 'Permission denied'}, status=403)
        msg.is_pinned = not msg.is_pinned
        msg.save()
        return Response({'pinned': msg.is_pinned})

class ForwardView(APIView):
    permission_classes = [IsAuthenticated]
    def post(self, request):
        message_id = request.data.get('message_id')
        target_chat_id = request.data.get('chat_id')
        if not message_id or not target_chat_id:
            return Response({'error': 'message_id and chat_id required'}, status=400)
        msg = get_object_or_404(Message, id=message_id)
        target_chat = get_object_or_404(Chat, id=target_chat_id)
        if not target_chat.participants.filter(id=request.user.id).exists():
            return Response({'error': 'Not in target chat'}, status=403)
        new_msg = Message.objects.create(
            chat=target_chat, sender=request.user,
            text=msg.text, media_url=msg.media_url,
            reply_to=None, is_forwarded=True,
        )
        return Response(MessageSerializer(new_msg).data, status=201)

class SearchMessagesView(APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request):
        q = request.GET.get('q', '').strip()
        if len(q) < 2:
            return Response({'results': []})
        results = Message.objects.filter(
            search_vector=SearchQuery(q, config='russian'),
            chat__participants=request.user,
            is_deleted=False,
        ).distinct()[:30]
        serializer = MessageSerializer(results, many=True)
        return Response({'results': serializer.data})
