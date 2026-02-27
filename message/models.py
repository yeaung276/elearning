from django.db import models
from django.conf import settings

# Thread in the report
class Conversation(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)

# ThreadParticipant in the report
class ConversationParticipant(models.Model):
    conversation = models.ForeignKey(
        Conversation,
        on_delete=models.CASCADE,
        related_name="participants"
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="conversations"
    )
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("conversation", "user")

# ThreadMessage in the report
class Message(models.Model):
    conversation = models.ForeignKey(
        Conversation,
        on_delete=models.CASCADE,
        related_name="messages"
    )
    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="sender",
        null=True,
    )
    content = models.TextField()
    sent_at = models.DateTimeField(auto_now_add=True)