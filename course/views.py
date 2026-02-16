from datetime import date

from django.views import View
from django.utils.timezone import now
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.decorators import login_required
from rest_framework.decorators import api_view, renderer_classes, permission_classes
from rest_framework.renderers import TemplateHTMLRenderer
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status

from .forms import CourseForm
from .models import Course, Enrollment
from people.mixin import TeacherRequiredMixin

def is_enrolled(enrollment):
    return enrollment is not None and enrollment.expired_at > date.today() and enrollment.status != 'blocked'


@api_view(['GET'])
def explore(request):
    return render(request, "courses.html", {})
    
@api_view(["GET"])
@renderer_classes([TemplateHTMLRenderer])
def course_detail(request, id: int):
    course = get_object_or_404(Course, id=id)
    enrollment = Enrollment.objects.filter(user=request.user, course=course).first()
    if is_enrolled(enrollment):
        return redirect("materials", cid=course.id) # type: ignore
    return render(request, "detail.html", {
        "course": course,
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
            return redirect("materials", cid=course.id)
        
        return render(request, "create.html", {"form": form})
    
@api_view(["POST"])
@permission_classes([IsAuthenticated])
def enroll(request, id: int):
    course = get_object_or_404(Course, id=id)
    
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


@api_view(["GET"])
def materials(request, cid: int):
    return render(request, "material.html")