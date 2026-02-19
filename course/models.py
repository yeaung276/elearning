from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator

class Course(models.Model):
    CATEGORY_CHOICES = [
        ("computer-science", "Computer Science"),
        ("data-science", "Data Science"),
        ("business", "Business"),
        ("design", "Design"),
        ("marketing", "Marketing"),
        ("photography", "Photography"),
    ]
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('published', 'Published'),
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
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')

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
    
class Instructor(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
    )
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="instructors")
    
class Rating(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
    )
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="ratings")
    rating = models.IntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
    text = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
class Module(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="modules")
    name =  models.CharField(max_length=20, blank=False)
    
class Material(models.Model):
    class Type(models.TextChoices):
        QUIZ = "quiz", "Quiz"
        VIDEO = "video", "Video"
        READING = "reading", "Reading"

    module = models.ForeignKey(Module, on_delete=models.CASCADE, related_name="materials")
    name = models.CharField(max_length=200, blank=False)
    due_date = models.DateField(null=True, blank=True)
    type = models.CharField(max_length=10, choices=Type.choices, blank=False)
    
class VideoMaterial(models.Model):
    material = models.ForeignKey(Material, on_delete=models.CASCADE, related_name="video")
    path = models.FileField(upload_to='videos/')
    title = models.CharField(max_length=255, blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)


class ReadingMaterial(models.Model):
    material = models.ForeignKey(Material, on_delete=models.CASCADE, related_name="reading")
    title = models.CharField(max_length=255, blank=True)
    text = models.TextField(blank=True)
    file = models.FileField(upload_to='reading_materials/', blank=True, null=True)

    uploaded_at = models.DateTimeField(auto_now_add=True)
    
class Progress(models.Model):
    material = models.ForeignKey(Material, on_delete=models.CASCADE, related_name="progress")
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
    )
    created_at =  models.DateTimeField(auto_now_add=True)
