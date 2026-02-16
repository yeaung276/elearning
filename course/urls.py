from django.urls import path

from .views import explore, course_detail, CourseCreateView, materials, enroll

urlpatterns = [
    path('courses/', explore),
    path('course/new', CourseCreateView.as_view(), name="create_course"),
    path('course/<int:id>', course_detail, name="course"),
    path('course/<int:id>/enroll', enroll, name="enroll"),
    path('course/<int:cid>/material', materials, name="materials")
]