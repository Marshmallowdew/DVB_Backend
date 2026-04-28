import os
from django.core.asgi import get_asgi_application
from django.urls import path

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')

django_asgi_app = get_asgi_application()

from channels.routing import ProtocolTypeRouter, URLRouter
from channels.security.websocket import AllowedHostsOriginValidator
from core.middleware import JWTAuthMiddleware
from users.consumers import NotificationConsumer

application = ProtocolTypeRouter({
    "http": django_asgi_app,
    
    "websocket": AllowedHostsOriginValidator(
        JWTAuthMiddleware(
            URLRouter([
                path('ws/notifications/', NotificationConsumer.as_asgi()),
            ])
        )
    ),
})
