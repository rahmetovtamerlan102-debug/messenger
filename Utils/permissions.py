from rest_framework.permissions import BasePermission

class IsChatParticipant(BasePermission):
    def has_object_permission(self, request, view, obj):
        if hasattr(obj, 'chat'):
            return obj.chat.participants.filter(id=request.user.id).exists()
        if hasattr(obj, 'participants'):
            return obj.participants.filter(id=request.user.id).exists()
        return False

class IsSenderOrAdmin(BasePermission):
    def has_object_permission(self, request, view, obj):
        if request.user.is_staff:
            return True
        if hasattr(obj, 'sender'):
            return obj.sender == request.user
        return False
