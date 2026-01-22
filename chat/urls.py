from django.urls import path
from . import views

urlpatterns = [
    path('', views.chat_home, name='chat_home'),
    path('<int:other_id>/', views.chat_room, name='chat_room'),
    path('load-more/<int:conversation_id>/', views.load_more_messages, name='load_more_messages'),
]