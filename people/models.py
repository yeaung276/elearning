from django.contrib.auth.models import AbstractUser
from django.db import models

class User(AbstractUser):
    ROLES = (
        ('student', 'Student'),
        ('teacher', 'Teacher'),
    )
    role = models.CharField(max_length=20, choices=ROLES, default='user')
    

class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    name = models.TextField(max_length=50, blank=False)
    title = models.TextField(max_length=50, blank=False)
    location = models.TextField(max_length=50, blank=False)
    bio = models.TextField(blank=True)
    picture = models.ImageField(upload_to="profiles/", blank=True)
    
class Status(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="statuses"
    )
    text = models.TextField(max_length=512, blank=False)
    image = models.ImageField(upload_to="status/", blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
