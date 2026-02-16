from django import template

register = template.Library()

@register.filter
def is_teacher(user):
    if not user or not user.is_authenticated:
        return False
    return getattr(user, 'role', None) == 'teacher'

@register.filter
def is_student(user):
    if not user or not user.is_authenticated:
        return False
    return getattr(user, 'role', None) == 'student'