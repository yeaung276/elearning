import json

from django.utils.timezone import localtime

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer
from .models import Conversation, Message, ConversationParticipant


class MessageConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        user = self.scope["user"]  # type: ignore
        if not user.is_authenticated:  # type: ignore
            await self.close()
            return

        conversation = await database_sync_to_async(
            Conversation.objects.filter(id=self.scope["url_route"]["kwargs"]["id"]).first  # type: ignore
        )()
        if conversation is None:
            await self.close()
            return
        
        has_access = await database_sync_to_async(
            ConversationParticipant.objects.filter(
                conversation_id=conversation.id, user=user # type: ignore
            ).exists
        )()
        if not has_access:
            await self.close()
            return

        self.conversation = conversation
        await self.channel_layer.group_add(f"chat_{self.conversation.id}", self.channel_name)  # type: ignore
        await self.accept()

    async def disconnect(self, code):
        await self.channel_layer.group_discard(f"chat_{self.conversation.id}", self.channel_name)  # type: ignore

    async def receive(self, text_data):
        data = json.loads(text_data)
        msg = await database_sync_to_async(Message.objects.create)(
            conversation=self.conversation,
            sender=self.scope["user"],  # type: ignore
            content=data["message"],
        )
        await self.channel_layer.group_send(
            f"chat_{self.conversation.id}", # type: ignore
            {
                "type": "chat_message",
                "message": msg.content,
                "sent_at": localtime(msg.sent_at).strftime("%b. %-d, %-I:%M %p"),
                "sender_id": msg.sender.id, # type: ignore
            },
        )

    async def chat_message(self, event):
        await self.send(
            text_data=json.dumps({
                "message": event["message"],
                "sent_at": event["sent_at"],
                "sender_id": event["sender_id"],
            })
        )
