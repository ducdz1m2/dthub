import os
from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
import chat.routing

# Try to import ai_hub routing, but don't fail if it doesn't exist
try:
    import ai_hub.routing
    ai_hub_routing = ai_hub.routing.websocket_urlpatterns
except ImportError:
    ai_hub_routing = []

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'dthub.settings')

application = ProtocolTypeRouter({
    "http": get_asgi_application(),
    "websocket": AuthMiddlewareStack(
        URLRouter(chat.routing.websocket_urlpatterns + ai_hub_routing)
    ),
})
