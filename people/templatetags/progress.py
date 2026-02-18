from django import template

from course.models import Material

register = template.Library()

@register.filter
def progress_percentage(course, user):
    if not user.is_authenticated:
        return 0

    all_materials = Material.objects.filter(module__course=course)
    total_materials = all_materials.count()

    if total_materials == 0:
        return 0

    completed_materials = all_materials.filter(progress__user=user).distinct().count()

    percentage = (completed_materials / total_materials) * 100
    return round(percentage)
