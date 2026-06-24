from django.urls import path
from . import views

urlpatterns = [
    path('health/', views.health, name='health'),
    path('register/', views.RegisterView.as_view(), name='register'),
    path('login/', views.LoginView.as_view(), name='login'),
    path('profile/', views.ProfileView.as_view(), name='profile'),
    path('users/search/', views.UserSearchView.as_view(), name='user-search'),
    path('chats/', views.ChatListView.as_view(), name='chat-list'),
    path('chats/<uuid:chat_id>/messages/', views.MessageListView.as_view(), name='message-list'),
    path('messages/<uuid:message_id>/', views.MessageDetailView.as_view(), name='message-detail'),
    path('upload/', views.UploadView.as_view(), name='upload'),
    path('messages/create/', views.MessageCreateView.as_view(), name='message-create'),
    path('messages/<uuid:message_id>/react/', views.ReactionView.as_view(), name='reaction'),
    path('messages/<uuid:message_id>/pin/', views.PinView.as_view(), name='pin'),
    path('messages/forward/', views.ForwardView.as_view(), name='forward'),
    path('messages/search/', views.SearchMessagesView.as_view(), name='search-messages'),
]
