import json
from datetime import date

from django.views import View
from django.utils.timezone import now
from django.http import Http404, JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import get_user_model
from django.contrib.auth.mixins import LoginRequiredMixin
from rest_framework.decorators import api_view, renderer_classes, permission_classes
from rest_framework.renderers import TemplateHTMLRenderer
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status

from .forms import CourseForm
from .models import Course, Enrollment, Instructor
from people.mixin import TeacherRequiredMixin


User = get_user_model()

def is_enrolled(enrollment):
    return enrollment is not None and enrollment.expired_at > date.today() and enrollment.status != 'blocked'

def is_owner(course, user):
    return course.user == user

def is_instructor(course, user):
    return Instructor.objects.filter(course=course, user=user).exists()


@api_view(['GET'])
def explore(request):
    return render(request, "courses.html", {})
    
@api_view(["GET"])
@renderer_classes([TemplateHTMLRenderer])
def course_detail(request, id: int):
    course = get_object_or_404(Course, id=id)

    if request.user.is_authenticated:
        enrollment = Enrollment.objects.filter(user=request.user, course=course).first()
        if is_enrolled(enrollment) or is_owner(course, request.user) or is_instructor(course, request.user):
            return redirect("material_overview", cid=course.id) # type: ignore
    
    if course.status == "draft":
        raise Http404()

    instructors = Instructor.objects.filter(course=course).all()
    return render(request, "detail.html", {
        "course": course, 
        "instructors": instructors
    })

class CourseCreateView(LoginRequiredMixin, TeacherRequiredMixin, View):
    login_url = "login"
    redirect_field_name = None
    
    def get(self, request):
        form = CourseForm()
        return render(request, "create.html", {"form": form})
    
    def post(self, request):
        form = CourseForm(request.POST, request.FILES)
        if form.is_valid():
            course = form.save(commit=False)
            course.user = request.user
            course.save()
            return redirect("material_overview", cid=course.id)
        
        return render(request, "create.html", {"form": form})
    
class MaterialOverviewView(LoginRequiredMixin, View):
    login_url = "login"
    redirect_field_name = None
    
    def get(self, request, cid: int):
        course = get_object_or_404(Course, id=cid)
        form = CourseForm(instance=course, show_status=True, disabled=request.user != course.user)
        return render(request, "materials/overview.html", {
            "form": form, 
            "course": course
        })
    
    def post(self, request, cid: int):
        course = get_object_or_404(Course, id=cid)
        if course.user != request.user:
            return redirect("material_overview", cid=course.id) # type: ignore
        
        form = CourseForm(request.POST, request.FILES, instance=course, show_status=True)
        if form.is_valid():
            profile = form.save(commit=False)
            profile.user = request.user
            profile.save()

        return render(request, "materials/overview.html", {
            "form": form, 
            "course": course
        })

class InstructorOverviewView(LoginRequiredMixin, TeacherRequiredMixin, View):
    login_url = "login"
    redirect_field_name = None
    
    def get(self, request, cid: int):
        course = get_object_or_404(Course, id=cid)
        if course.user != request.user:
            return redirect("material_overview", cid=course.id) # type: ignore
        
        instructors = Instructor.objects.filter(course=course).all()
        return render(request, "materials/instructor.html", {
            "course": course,
            "instructors": instructors,
        })
        
    def post(self, request, cid: int):
        course = get_object_or_404(Course, id=cid)
        if course.user != request.user:
            return redirect("material_overview", cid=course.id) # type: ignore
        
        user = get_object_or_404(User, id=request.POST.get("user_id"))
        
        Instructor.objects.get_or_create(user=user, course=course)
        
        return redirect("instructor_overview", cid=course.id) # type: ignore
    
    def delete(self, request, cid: int):
        course = get_object_or_404(Course, id=cid)
        if course.user != request.user:
            return JsonResponse({"error": "Forbidden"}, status=403)
        data = json.loads(request.body)
        instructor = get_object_or_404(Instructor, id=data.get("instructor_id"))
        instructor.delete()
        
        return JsonResponse({"ok": True})
    
@api_view(["POST"])
@permission_classes([IsAuthenticated])
def enroll(request, id: int):
    course = get_object_or_404(Course, id=id, status="publish")
    
    enrollment, created = Enrollment.objects.get_or_create(
        course=course,
        user=request.user,
        defaults={
            'expired_at': course.course_end,
            'status': 'enrolled'
        }
    )
    
    if not created:
        if enrollment.status == 'blocked':
            return Response(
                {'error': 'You are blocked from this course'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        if enrollment.expired_at < now().date():
            enrollment.expired_at = course.course_end
            enrollment.save()
            return Response({'message': 'Enrollment renewed'}, status=status.HTTP_200_OK)
        
        return Response({'message': 'Already enrolled'}, status=status.HTTP_200_OK)
    
    return Response({'message': 'Enrolled successfully'}, status=status.HTTP_201_CREATED)
