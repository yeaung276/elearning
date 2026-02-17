from django.urls import path

from .views import explore, course_detail, CourseCreateView, MaterialOverviewView, InstructorOverviewView, StudentOverviewView, enroll

urlpatterns = [
    path('courses/', explore),
    path('course/new/', CourseCreateView.as_view(), name="create_course"),
    path('course/<int:id>/', course_detail, name="course"),
    path('course/<int:id>/enroll/', enroll, name="enroll"),
    path('course/<int:cid>/material/', MaterialOverviewView.as_view(), name="material_overview"),
    path('course/<int:cid>/instructor/', InstructorOverviewView.as_view(), name="instructor_overview"),
    path('course/<int:cid>/student/', StudentOverviewView.as_view(), name="student_overview")
]