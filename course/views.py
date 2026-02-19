import json
from datetime import date

from django.views import View
from django.db.models import Q, Avg, Count, Prefetch
from django.utils.timezone import now
from django.http import Http404, JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import get_user_model
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.paginator import Paginator
from rest_framework.decorators import api_view, renderer_classes, permission_classes
from rest_framework.renderers import TemplateHTMLRenderer
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status

from .forms import CourseForm, RatingForm, VideoMaterialForm, ReadingMaterialForm
from .models import (
    Course, 
    Enrollment, 
    Instructor, 
    Rating, 
    Module, 
    Material,
    Progress
)
from people.mixin import TeacherRequiredMixin
from notification.signals import material_created, enrollment_created


User = get_user_model()

def is_enrolled(enrollment):
    return enrollment is not None and enrollment.expired_at > date.today() and enrollment.status != 'blocked'

def is_owner(course, user):
    return course.user == user

def is_instructor(course, user):
    return Instructor.objects.filter(course=course, user=user).exists()


@api_view(['GET'])
def explore(request):
    q = request.GET.get('q', '').strip()
    categories = request.GET.getlist('categories')
    sort_by = request.GET.get('sort_by', 'popular')

    courses = Course.objects.filter(status='published')

    # filter
    if q:
        courses = courses.filter(
            Q(title__icontains=q) | Q(description__icontains=q)
        )

    if categories:
        courses = courses.filter(category__in=categories)

    courses = courses.annotate(
        avg_rating=Avg('ratings__rating'),
        enrollment_count=Count('enrollments', distinct=True),
        rating_count=Count('ratings', distinct=True)
    )

    # Sort
    if sort_by == 'rating':
        courses = courses.order_by('-avg_rating', '-enrollment_count')
    elif sort_by == 'newest':
        courses = courses.order_by('-created_at')
    else:
        courses = courses.order_by('-enrollment_count', '-avg_rating')

    # Paginate
    page = Paginator(courses, 9).get_page(request.GET.get("page"))

    total_count = Course.objects.filter(status='published').count()
    category_counts = Course.objects.filter(status='published').values('category').annotate(count=Count('id'))
    category_dict = {item['category']: item['count'] for item in category_counts}

    # Prepare categories with counts for template
    categories_with_counts = [
        {
            'key': key,
            'label': label,
            'count': category_dict.get(key, 0)
        }
        for key, label in Course.CATEGORY_CHOICES
    ]

    return render(request, "courses.html", {
        'page': page,
        'total_count': total_count,
        'categories': categories_with_counts,
        'q': q,
        'selected_categories': categories,
        'sort_by': sort_by,
    })
    
@api_view(["GET"])
@renderer_classes([TemplateHTMLRenderer])
def course_detail(request, id: int):
    course = get_object_or_404(Course.objects.annotate(avg_rating=Avg("ratings__rating"), rating_count=Count("ratings__rating")), id=id)
    course = get_object_or_404(
        Course.objects
        .annotate(
            avg_rating=Avg("ratings__rating"),
            rating_count=Count("ratings__rating"),
            total_videos=Count(
                "modules__materials",
                filter=Q(modules__materials__type="video")
            ),
            total_readings=Count(
                "modules__materials",
                filter=Q(modules__materials__type="reading")
            ),
        )
        .prefetch_related(
            Prefetch(
                "modules",
                queryset=Module.objects.annotate(
                    total_materials=Count("materials"),
                    video_count=Count("materials", filter=Q(materials__type="video")),
                    reading_count=Count("materials", filter=Q(materials__type="reading")),
                )
            )
        ),
        id=id
    )


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
        if request.user.is_authenticated:
            enrollment = Enrollment.objects.filter(user=request.user, course=course).first()
            if is_enrolled(enrollment) or is_owner(course, request.user) or is_instructor(course, request.user):
                form = CourseForm(instance=course, show_status=True, disabled=request.user != course.user)
                return render(request, "materials/overview.html", {
                    "form": form, 
                    "course": course,
                })
        return redirect("course", id=course.id) # type: ignore
    
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
    
class StudentOverviewView(LoginRequiredMixin, View):
    login_url = "login"
    redirect_field_name = None
    
    def get(self, request, cid: int):
        course = get_object_or_404(Course, id=cid)
        enrollments = Enrollment.objects.filter(course=course)
        q = request.GET.get("q", "").strip()
        if q:
            enrollments = enrollments.filter(
                Q(user__username__icontains=q) | Q(user__userprofile__name__icontains=q)
        )
        return render(request, "materials/student.html", {
            "enrollments": enrollments,
            "course": course,
        })
        
    def patch(self, request, cid: int):
        course = get_object_or_404(Course, id=cid)
        if not Instructor.objects.filter(user=request.user, course=course).exists() and request.user != course.user:
            return JsonResponse({"error": "Only teacher can block or unblock a student."})
        data = json.loads(request.body)
        
        enrollment = get_object_or_404(Enrollment, id=data["enrollment_id"], course=course)
        enrollment.status = "blocked" if data["blocked"] else "enrolled"
        enrollment.save()
        return JsonResponse({"ok": True})
        
    def delete(self, request, cid: int):
        course = get_object_or_404(Course, id=cid)
        if not Instructor.objects.filter(user=request.user, course=course).exists() and request.user != course.user:
            return JsonResponse({"error": "Only teacher can remove a student."}, status=401)
        
        data = json.loads(request.body)
        enrollment = get_object_or_404(Enrollment, id=data["enrollment_id"], course=course)
        enrollment.delete()
        return JsonResponse({"ok": True})
        
class RatingOverviewView(LoginRequiredMixin, View):
    login_url = "login"
    redirect_field_name = None
    
    def get(self, request, cid):
        course = get_object_or_404(Course, id=cid)
        enrollment = Enrollment.objects.filter(user=request.user, course=course).last()
        if not is_enrolled(enrollment):
            return redirect("material_overview", cid=course.id) # type: ignore
        
        existing = Rating.objects.filter(user=request.user, course=course).last()
        form = RatingForm(instance=existing)

        return render(request, "materials/rating.html", {
            "course": course,
            "form": form,
        })
        
    def post(self, request, cid):
        course = get_object_or_404(Course, id=cid)
        enrollment = Enrollment.objects.filter(user=request.user, course=course).last()
        if not is_enrolled(enrollment):
            return redirect("material_overview", cid=course.id) # type: ignore
        
        existing = Rating.objects.filter(user=request.user, course=course).last()
        form = RatingForm(request.POST, instance=existing)
        if form.is_valid():
            rating = form.save(commit=False)
            rating.user = request.user
            rating.course = course
            rating.save()

        return redirect("material_overview", cid=course.id) # type: ignore
        
class ModuleView(LoginRequiredMixin, TeacherRequiredMixin, View):
    login_url = "login"
    redirect_field_name = None
    
    def post(self, request, cid: int):
        course = get_object_or_404(Course, id=cid)
        if course.user != request.user:
            return redirect("material_overview", cid=course.id) # type: ignore
        
        name = request.POST.get("name", "").strip()
        if name:
            Module.objects.create(course=course, name=name)
        return redirect("material_overview", cid=course.id) # type: ignore
        
    def delete(self, request, cid: int):
        course = get_object_or_404(Course, id=cid)
        if request.user != course.user:
            return JsonResponse({"error": "Only owner can remove a module."}, status=401)
        
        data = json.loads(request.body)
        module = get_object_or_404(Module, id=data["module_id"], course=course)
        module.delete()
        return JsonResponse({"ok": True})
    
class MaterialView(LoginRequiredMixin, View):
    login_url = "login"
    redirect_field_name = None
    
    def get(self, request, cid: int, mid: int):
        course = get_object_or_404(Course, id=cid)
        material = get_object_or_404(Material, id=mid)
        is_owner = request.user == course.user
        
        if material.module.course != course:
            raise Http404()

        if material.type == "video":
            form = VideoMaterialForm(instance=material.video.first(), initial={"due_date": material.due_date}) # type: ignore
            if is_owner:
                return render(request, "materials/video/form.html", {
                    "form": form,
                    "course": course,
                    "material": material,
                    "open_module": material.module.id, # type: ignore
                })
            return render(request, "materials/video/video.html", {
                "course": course,
                "material": material,
                "open_module": material.module.id, # type: ignore
            })

        if material.type == "reading":
            form = ReadingMaterialForm(instance=material.reading.first(), initial={"due_date": material.due_date}) # type: ignore
            if is_owner:
                return render(request, "materials/reading/form.html", {
                    "form": form,
                    "course": course,
                    "material": material,
                    "open_module": material.module.id, # type: ignore
                })
            return render(request, "materials/reading/reading.html", {
                "course": course,
                "material": material,
                "open_module": material.module.id, # type: ignore
            })
    
    def post(self, request, cid: int, mid: int):
        course = get_object_or_404(Course, id=cid)
        if course.user != request.user:
            return redirect("material_overview", cid=course.id) # type: ignore
        
        module = get_object_or_404(Module, id=request.POST.get("module_id"), course=course)
        if request.POST.get('sidebar'):
            material = Material.objects.create(
                module=module, 
                name=request.POST.get("name", "").strip(), 
                type=request.POST.get("type", "").strip()
            )
            return redirect("material", cid=course.id, mid=material.id) # type: ignore
        
        material = get_object_or_404(Material, id=mid)
        if material.module != module:
            return redirect("material", cid=course.id, mid=material.id) # type: ignore
        
        if material.type == "video":
            form = VideoMaterialForm(request.POST, request.FILES)
            if form.is_valid():
                video = form.save(commit=False)
                video.material = material
                video.save()
                material.due_date = form.cleaned_data["due_date"]
                material.save()
                material_created.send(sender=None, mid=material.id) # type: ignore
                return redirect("material", cid=course.id, mid=material.id) # type: ignore
            return render(request, "materials/video/form.html", {
                "form": form,
                "course": course,
                "material": material,
                "open_module": material.module.id # type: ignore
            })
        
        if material.type == "reading":
            form = ReadingMaterialForm(request.POST, request.FILES)
            if form.is_valid():
                reading = form.save(commit=False)
                reading.material = material
                reading.save()
                material.due_date = form.cleaned_data["due_date"]
                material.save()
                material_created.send(sender=None, mid=material.id) # type: ignore
                return redirect("material", cid=course.id, mid=material.id) # type: ignore
            return render(request, "materials/reading/form.html", {
                "form": form,
                "course": course,
                "material": material,
                "open_module": material.module.id # type: ignore
            })
        
        return redirect("material", cid=course.id, mid=material.id) # type: ignore

    def delete(self, request, cid: int, mid: int):
        course = get_object_or_404(Course, id=cid)
        if request.user != course.user:
            return JsonResponse({"error": "Only owner can remove a material."}, status=401)

        material = get_object_or_404(Material, id=mid, module__course=course)
        material.delete()
        return JsonResponse({"ok": True})

@api_view(["POST"])
@permission_classes([IsAuthenticated])
def enroll(request, id: int):
    course = get_object_or_404(Course, id=id, status="published")
    
    enrollment, created = Enrollment.objects.get_or_create(
        course=course,
        user=request.user,
        defaults={
            'expired_at': course.course_end,
            'status': 'enrolled'
        }
    )
    
    if not created and enrollment.status == 'blocked':
        return Response(
            {'error': 'You are blocked from this course'},
            status=status.HTTP_403_FORBIDDEN
        )
        
    if not created and enrollment.expired_at < now().date():
        enrollment.expired_at = course.course_end
        enrollment.save()
        
    enrollment_created.send(sender=None, enrollment_id=enrollment.id) # type: ignore
    return Response({'message': 'Enroll successfully'}, status=status.HTTP_200_OK)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def marked_as_complete(request, cid: int, mid: int):
    course = get_object_or_404(Course, id=cid)
    material = get_object_or_404(Material, id=mid)
    if material.module.course == course and Enrollment.objects.filter(user=request.user, course=course).exists(): # type: ignore
        Progress.objects.get_or_create(user=request.user, material=material)
        
    return redirect("material", cid=cid, mid=mid)
    