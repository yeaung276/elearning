"""
ASGI config for elearning project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/6.0/howto/deployment/asgi/
"""

import os

from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack

from notification.urls import websocket_urlpatterns as notification_websocket_urlpatterns
from message.urls import websocket_urlpatterns as message_websocket_urlpatterns

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'elearning.settings')

application = ProtocolTypeRouter({
    "http": get_asgi_application(),
    "websocket": AuthMiddlewareStack(
        URLRouter(message_websocket_urlpatterns + notification_websocket_urlpatterns)
    ),
})
