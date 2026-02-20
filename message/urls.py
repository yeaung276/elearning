from django.urls import path

from .views import message, threads, call
from .consumers import MessageConsumer, CallConsumer

urlpatterns = [
    path("messages", threads, name="threads"),
    path("messages/call/<int:id>", call, name="call"),
    path("messages/<int:id>", message, name="message"),
]

websocket_urlpatterns = [
    path('ws/messages/<int:id>/', MessageConsumer.as_asgi(), name='message'), # type: ignore
    path('ws/call/<int:id>/', CallConsumer.as_asgi(), name='call'), # type: ignore
]