from django import template
from datetime import date

from ..models import Enrollment

register = template.Library()

@register.filter
def can_enroll(course, user):
    today = date.today()
    not_teacher = not (hasattr(user, 'role') and user.role == 'teacher')
    is_in_registration_period = course.registration_start <= today <= course.registration_end
    enrollment = Enrollment.objects.filter(user=user, course=course).first()
    not_block = enrollment is None or enrollment.status != "blocked"
    not_enrolled = enrollment is None or enrollment.expired_at < today
    return not_teacher and is_in_registration_period and not_block and not_enrolled