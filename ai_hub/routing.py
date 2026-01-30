from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    re_path(r'ws/ai-chat/$', consumers.RAGMCPConsumer.as_asgi()),
    re_path(r'ws/sensor-dashboard/$', consumers.SensorDashboardConsumer.as_asgi()),
]
