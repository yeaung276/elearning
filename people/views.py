from rest_framework.decorators import api_view, renderer_classes
from django.contrib.auth.decorators import login_required
from rest_framework.renderers import TemplateHTMLRenderer
from django.contrib.auth.mixins import LoginRequiredMixin
from rest_framework.decorators import api_view
from django.shortcuts import get_object_or_404
from django.contrib.auth import get_user_model
from django.shortcuts import render, redirect
from django.http import Http404, JsonResponse
from django.core.paginator import Paginator
from django.contrib.auth import login
from django.db.models import Q
from django.views import View

from .forms import RegistrationForm, ProfileUpdateForm, StatusForm
from .models import UserProfile, Status
from course.models import Course


User = get_user_model()

# ============ Dashboard ===================
@api_view(["GET"])
@login_required(login_url='/login/')
@renderer_classes([TemplateHTMLRenderer])
def dashboard(request):
    if not UserProfile.objects.filter(user=request.user).exists():
        return redirect("profile_edit")

    page = Paginator(
        Status.objects.filter(user=request.user).order_by("-created_at"), 5
    ).get_page(request.GET.get("page"))
    
    courses = Course.objects.filter(
        Q(user=request.user) |                          # Own course 
        Q(enrollments__user=request.user) |             # Enrolled course
        Q(instructors__user=request.user)               # Instructor cause
    ).distinct()

    
    return render(request, "dashboard.html", {"page": page, "courses": courses })

# ============= Authentication ===============
class RegisterView(View):
    def get(self, request):
        if request.user.is_authenticated:
            return redirect('dashboard')
        form = RegistrationForm()
        return render(request, 'registration/register.html', {'form': form})
    
    def post(self, request):
        form = RegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('dashboard')
        return render(request, 'registration/register.html', {'form': form})

# ============== Profile ====================
# Public route
@api_view(["GET"])
@renderer_classes([TemplateHTMLRenderer])
def profile(request, id: int):
    user = get_object_or_404(User, id=id)
    profile = getattr(user, "userprofile", None)
    if not profile:
        raise Http404

    status = Status.objects.filter(user=request.user).order_by("-created_at")

    courses = Course.objects.filter(
        Q(user=request.user) |                          # Own course 
        Q(enrollments__user=request.user) |             # Enrolled course
        Q(instructors__user=request.user)               # Instructor cause
    ).distinct()
    
    paginator = Paginator(status, 5)
    page_number = request.GET.get("page")
    page = paginator.get_page(page_number)
    return render(request, "profile/profile.html", {
        "profile": profile, 
        "page": page,
        "courses": courses
    })

# Protected route
@api_view(["GET"])
@login_required(login_url="/login/")
def search_user(request):
    if request.user.role != "teacher":
        return JsonResponse({"error": "Only teachers can access this endpoint"}, status=403)
    
    query = request.GET.get('q', '').strip()
    if not query:
        return JsonResponse({'results': []}, status=200)
    
    users = User.objects.filter(
        role=request.GET.get('role', 'teacher')
    ).filter(
        Q(username__icontains=query) | 
        Q(userprofile__name__icontains=query)
    ).select_related('userprofile').distinct()[:10]
    
    results = []
    for user in users:
        try:
            profile = user.userprofile # type: ignore
            results.append({
                'id': user.id, # type: ignore
                'name': profile.name,
                'profile_img': request.build_absolute_uri(profile.picture.url) if profile.picture else None,
                'title': profile.title
            })
        except User.userprofile.RelatedObjectDoesNotExist: # type: ignore
            continue

    return JsonResponse({'results': results}, status=200)
    

# Protected route
class ProfileEditView(View, LoginRequiredMixin):
    login_url = "login"
    redirect_field_name = None
    
    def get(self, request):
        profile = getattr(request.user, "userprofile", None)
        form = ProfileUpdateForm(instance=profile)
        return render(request, "profile/edit.html", {"form": form})
    
    def post(self, request):
        profile = getattr(request.user, "userprofile", None)
        form = ProfileUpdateForm(request.POST, request.FILES, instance=profile)

        if form.is_valid():
            profile = form.save(commit=False)
            profile.user = request.user
            profile.save()
            return redirect("profile", id=request.user.id)

        return render(request, "profile/edit.html", {"form": form})

# ============== Status ======================
class StatusView(View, LoginRequiredMixin):
    login_url = "login"
    redirect_field_name = None
    
    def get(self, request):
        form = StatusForm()
        return render(request, "status/new.html", {"form": form})
    
    def post(self, request):
        form = StatusForm(request.POST, request.FILES)
        if form.is_valid():
            status = form.save(commit=False)
            status.user = request.user
            status.save()
            return redirect("dashboard")
        
        return render(request, "status/new.html", {"form": form})