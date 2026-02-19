from django.db import models

class Notifications(models.Model):
    NOTIFICATION_TYPES = [
        ("material", "Material"),
        ("enrollment", "Enrollment"),
        ("status", "Status"),
    ]
    user = models.ForeignKey(
        "people.User",
        on_delete=models.CASCADE,
        related_name="notifications"
    )
    content = models.TextField()
    redirect_url = models.CharField(max_length=255, blank=True)
    notification_type = models.CharField(max_length=20, choices=NOTIFICATION_TYPES)
    
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
