from django import template

register = template.Library()

@register.filter
def is_teacher(user):
    from people.mixin import is_teacher
    return is_teacher(user)

@register.filter
def is_student(user):
    from people.mixin import is_student
    return is_student(user)

@register.filter
def is_owner(user, resource):
    from people.mixin import is_owner
    return is_owner(user, resource)