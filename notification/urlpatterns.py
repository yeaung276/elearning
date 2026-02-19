from django.urls import path
from consumers import Notifications

websocket_urlpatterns = [
    path('ws/notification/', Notifications.as_asgi(), name='notification'), # type: ignore
]