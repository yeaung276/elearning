from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth import get_user_model
from rest_framework.decorators import api_view, renderer_classes, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.renderers import TemplateHTMLRenderer

from .models import Conversation, ConversationParticipant


User = get_user_model()

@api_view(["GET"])
@permission_classes([IsAuthenticated])
@renderer_classes([TemplateHTMLRenderer])
def threads(request):
    all_threads = User.objects.filter(
        conversations__conversation__participants__user=request.user
    ).exclude(
        id=request.user.id
    ).distinct()

    return render(request, "threads.html", {
        "threads": all_threads,
    })

@api_view(["GET"])
@permission_classes([IsAuthenticated])
@renderer_classes([TemplateHTMLRenderer])
def message(request, id: int):
    target = get_object_or_404(User, id=id)
    
    # Thread
    conv = Conversation.objects.filter(
        participants__user=request.user
    ).filter(
        participants__user=target
    ).first()
    
    if not conv:
        conv = Conversation.objects.create()
        ConversationParticipant.objects.bulk_create([
            ConversationParticipant(conversation=conv, user=request.user),
            ConversationParticipant(conversation=conv, user=target)
        ])
        
    all_threads = User.objects.filter(
        conversations__conversation__participants__user=request.user
    ).exclude(
        id=request.user.id
    ).distinct()
    
    return render(request, "message.html", {
        "threads": all_threads,
        "conversation": conv,
        "messages": conv.messages.order_by("sent_at").all(), # type: ignore
        "target": target,
    })

@api_view(["GET"])
@permission_classes([IsAuthenticated])
@renderer_classes([TemplateHTMLRenderer])
def call(request, id: int):
    conv = get_object_or_404(Conversation, id=id)
    
    target = conv.participants.exclude(user=request.user).first().user # type: ignore
    
    return render(request, "call.html", {
        "conversation": conv,
        "target": target,
    })


