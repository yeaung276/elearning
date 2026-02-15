from django.urls import path

from .views import explore, course_detail, new_course, materials

urlpatterns = [
    path('courses/', explore),
    path('course/new', new_course),
    path('course/<int:id>', course_detail),
    path('course/<int:cid>/material/<int:mid>', materials)
]