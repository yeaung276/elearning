import json

from django.urls import reverse
from django.utils import timezone
from django.dispatch import receiver
from django.contrib.auth import get_user_model

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from channels.generic.websocket import AsyncWebsocketConsumer

from course.models import Material, Enrollment
from people.models import Status

from .signals import material_created, enrollment_created, status_created
from .models import Notifications


@receiver(material_created)
def handle_material_created(sender, mid: int, **kwargs):
    User = get_user_model()
    material = Material.objects.get(id=mid)
    # find all student of the course which the material belongs to
    students = User.objects.filter(
        enrollments__course__modules__materials=material,
        enrollments__expired_at__gte=timezone.now().date()
    ).exclude(
        enrollments__status="blocked"
    ).distinct()
    
    channel_layer = get_channel_layer()
    assert channel_layer is not None
    for std in students:
        noti = Notifications.objects.create(
            user=std,
            content=f"You have updated content in '{material.module.course.title}'.",
            notification_type="material",
            redirect_url=reverse("material", kwargs={"cid": material.module.course.id, "mid": material.id}) # type: ignore
        )
        async_to_sync(channel_layer.group_send)(
            f"notifications_{noti.user.id}", # type: ignore
            {
                "type": "send_notification",
                "data": {
                    "type": "material",
                    "content": noti.content,
                    "redirect_url": noti.redirect_url,
                },
            },
        )
        
        
@receiver(status_created)
def handle_status_created(sender, status_id: int, **kwargs):
    User = get_user_model()
    status = Status.objects.get(id=status_id)
    
    channel_layer = get_channel_layer()
    assert channel_layer is not None
    
    if status.user.role == "teacher":
        # notify all active students in teacher's courses
        students = User.objects.filter(
            enrollments__course__user=status.user,
            enrollments__expired_at__gte=timezone.now().date()
        ).exclude(
            enrollments__status="blocked"
        ).distinct()
        
        for std in students:
            noti = Notifications.objects.create(
                user=std,
                content=f"{status.user.userprofile.name} posted a new status.", # type: ignore
                notification_type="status",
                redirect_url=reverse("profile", kwargs={"id": status.user.id}) # type: ignore
            )
            async_to_sync(channel_layer.group_send)(
            f"notifications_{noti.user.id}", # type: ignore
            {
                "type": "send_notification",
                "data": {
                    "type": "status",
                    "content": noti.content,
                    "redirect_url": noti.redirect_url,
                },
            },
        )
            
    else:
        # notify all active students in same courses as this student
        students = User.objects.filter(
            enrollments__course__enrollments__user=status.user,
            enrollments__expired_at__gte=timezone.now().date()
        ).exclude(
            enrollments__status="blocked"
        ).exclude(
            id=status.user.id # type: ignore
        ).distinct()
        for std in students:
            noti = Notifications.objects.create(
                user=std,
                content=f"{status.user.get_full_name()} posted a new status.",
                notification_type="status_update",
                redirect_url=reverse("profile", kwargs={"id": status.user.id}) # type: ignore
            )
            async_to_sync(channel_layer.group_send)(
            f"notifications_{noti.user.id}", # type: ignore
            {
                "type": "send_notification",
                "data": {
                    "type": "status",
                    "content": noti.content,
                    "redirect_url": noti.redirect_url,
                },
            },
        )
    
@receiver(enrollment_created)
def handle_enrollment_created(sender, enrollment_id: int, **kwargs):
    enrollment = Enrollment.objects.get(id=enrollment_id)
    channel_layer = get_channel_layer()
    assert channel_layer is not None
    
    # Notification to owner and instructor of the course
    noti = Notifications.objects.create(
        user=enrollment.course.user, # type: ignore
        content=f"{enrollment.user.userprofile.name} enrolled in your course '{enrollment.course.title}'.",
        notification_type="enrollment",
        redirect_url=reverse("profile", kwargs={"id": enrollment.user.id}) # type:
    )
    async_to_sync(channel_layer.group_send)(
            f"notifications_{noti.user.id}", # type: ignore
            {
                "type": "send_notification",
                "data": {
                    "type": "enrollment",
                    "content": noti.content,
                    "redirect_url": noti.redirect_url,
                },
            },
        )
    
    
    instructors = enrollment.course.instructors.all() # type: ignore
    for instructor in instructors:
        noti = Notifications.objects.create(
            user=instructor.user, # type: ignore
            content=f"{enrollment.user.userprofile.name} enrolled in '{enrollment.course.title}'.",
            notification_type="enrollment",
            redirect_url=reverse("profile", kwargs={"id": enrollment.user.id}) # type: ignore
        )
        async_to_sync(channel_layer.group_send)(
            f"notifications_{noti.user.id}", # type: ignore
            {
                "type": "send_notification",
                "data": {
                    "type": "enrollment",
                    "content": noti.content,
                    "redirect_url": noti.redirect_url,
                },
            },
        )
        
        


class NotificationConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        user = self.scope["user"]  # type: ignore
        if not user.is_authenticated:  # type: ignore
            await self.close()
            return

        self.group_name = f"notifications_{user.id}" # type: ignore
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, code):
        await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def send_notification(self, event):
        await self.send(text_data=json.dumps(event["data"]))
