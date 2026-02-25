from django import template
from datetime import date

from ..models import Enrollment

register = template.Library()

@register.filter
def can_enroll(course, user):
    from course.views import is_eligible_to_enroll
    return is_eligible_to_enroll(user, course)