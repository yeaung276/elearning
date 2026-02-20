from django.urls import path

from .views import message, threads
from .consumers import MessageConsumer

urlpatterns = [
    path("messages", threads, name="threads"),
    path("messages/<int:id>", message, name="message"),
]

websocket_urlpatterns = [
    path('ws/messages/<int:id>/', MessageConsumer.as_asgi(), name='message'), # type: ignore
]