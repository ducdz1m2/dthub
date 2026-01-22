from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    re_path(r'ws/chat/(?P<other_id>\d+)/$', consumers.ChatConsumer.as_asgi()),
    re_path(r'ws/global/$', consumers.GlobalConsumer.as_asgi()),
]