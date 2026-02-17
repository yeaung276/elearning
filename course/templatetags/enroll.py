from django import template
from datetime import date

from ..models import Enrollment

register = template.Library()

@register.filter
def can_enroll(course, user):
    if not user.is_authenticated:
        return False
    
    if hasattr(user, 'role') and user.role == 'teacher':
        return False
    
    today = date.today()
    if not (course.registration_start <= today <= course.registration_end):
        return False

    enrollment = Enrollment.objects.filter(user=user, course=course).first()
    if enrollment is None:
        return True
    
    if enrollment.status == "blocked":
        return False
    
    return enrollment.expired_at is not None and enrollment.expired_at < today