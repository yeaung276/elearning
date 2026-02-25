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
        self.room_name = f"chat_{conversation.id}" # type:  ignore
        await self.channel_layer.group_add(self.room_name, self.channel_name)
        await self.accept()

    async def disconnect(self, code):
        await self.channel_layer.group_discard(self.room_name, self.channel_name)

    async def receive(self, text_data=None, bytes_data=None):
        data = json.loads(text_data or "{}")
        msg = await database_sync_to_async(Message.objects.create)(
            conversation=self.conversation,
            sender=self.scope["user"],  # type: ignore
            content=data["message"],
        )
        await self.channel_layer.group_send(self.room_name, {
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


class CallConsumer(AsyncWebsocketConsumer):
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
        
        self.room_name = f"call_{self.scope['url_route']['kwargs']['id']}" # type: ignore
        await self.channel_layer.group_add(self.room_name, self.channel_name)
        await self.accept()

    async def disconnect(self, code):
        await self.channel_layer.group_discard(self.room_name, self.channel_name)


    async def receive(self, text_data=None, bytes_data=None):
        data = json.loads(text_data or "{}")
        # Broadcast the signaling data to all participants in the call
        await self.channel_layer.group_send(
            self.room_name,
            {"type": "call_signal", "data": data, "sender": self.channel_name}
        )

    async def call_signal(self, event):
        if event["sender"] == self.channel_name:
            return
        await self.send(text_data=json.dumps(event["data"]))