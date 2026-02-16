from django.db import models
from django.conf import settings

class Course(models.Model):
    CATEGORY_CHOICES = [
        ("computer-science", "Computer Science"),
        ("data-science", "Data Science"),
        ("business", "Business"),
        ("design", "Design"),
        ("marketing", "Marketing"),
        ("photography", "Photography"),
    ]
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="courses"
    )

    title = models.CharField(max_length=255)
    subtitle = models.CharField(max_length=255, blank=True)
    category = models.CharField(
        max_length=50,
        choices=CATEGORY_CHOICES
    )
    description = models.TextField()
    cover_img = models.ImageField(
        upload_to="course/",
        blank=True,
        null=True
    )

    registration_start = models.DateField()
    registration_end = models.DateField()
    course_start = models.DateField()
    course_end = models.DateField()

    created_at = models.DateTimeField(auto_now_add=True)


class Enrollment(models.Model):
    STATUS_CHOICES = [
        ("enrolled", "Enrolled"),
        ("blocked", "Blocked"),
    ]
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="enrollments"
    )
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="enrollments")
    expired_at = models.DateField()
    status = models.CharField(max_length=10, choices=STATUS_CHOICES)