from django.urls import path
from . import views

urlpatterns = [
    path('', views.chat_home, name='chat_home'),
    path('<int:other_id>/', views.chat_room, name='chat_room'),
    path('load-more/<int:conversation_id>/', views.load_more_messages, name='load_more_messages'),
    path('unread-count/', views.unread_count, name='unread_count'),
    path('unread-count-per-user/', views.unread_count_per_user, name='unread_count_per_user'),
    path('mark-read/<int:other_id>/', views.mark_messages_read, name='mark_messages_read'),
]