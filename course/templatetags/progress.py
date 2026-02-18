from django import template

from ..models import Progress

register = template.Library()

@register.filter
def has_progress(material, user):
    if not user.is_authenticated:
        return False
    return Progress.objects.filter(user=user, material=material).exists()
