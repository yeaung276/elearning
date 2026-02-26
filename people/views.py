from datetime import timedelta

from rest_framework.decorators import api_view, renderer_classes, permission_classes
from rest_framework.renderers import TemplateHTMLRenderer
from rest_framework.permissions import IsAdminUser
from rest_framework.generics import ListAPIView, RetrieveAPIView
from rest_framework.filters import SearchFilter
from rest_framework.decorators import api_view
from rest_framework.pagination import PageNumberPagination
from django.shortcuts import get_object_or_404
from django.contrib.auth import get_user_model
from django.shortcuts import render, redirect
from django.http import Http404, JsonResponse
from django.core.paginator import Paginator
from django.contrib.auth import login
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.decorators import login_required
from django.db.models import Q, Avg
from django.utils import timezone
from django.views import View
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

from course.models import Course, Material
from notification.signals import status_created
from notification.models import Notifications
from .forms import RegistrationForm, ProfileUpdateForm, StatusForm
from .models import UserProfile, Status
from .serializers import UserSearchSerializer, UserProfileSerializer


User = get_user_model()

# ============ Dashboard ===================
@swagger_auto_schema(methods=["GET"], auto_schema=None)
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
    ).annotate(avg_rating=Avg("ratings__rating")).distinct()
    
    deadlines = Material.objects.filter(
        module__course__enrollments__user=request.user,
        module__course__enrollments__expired_at__gte=timezone.now(),
        due_date__lte=timezone.now() + timedelta(days=10)
    ).exclude(
        progress__user=request.user
    ).distinct()
    
    notifications = Notifications.objects.filter(user=request.user).order_by("-created_at").all()
    
    return render(request, "dashboard.html", {
        "page": page, 
        "courses": courses,
        "deadlines": deadlines,
        "notifications": notifications,
    })

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
@swagger_auto_schema(methods=["GET"], auto_schema=None)
@api_view(["GET"])
@renderer_classes([TemplateHTMLRenderer])
def profile(request, id: int):
    user = get_object_or_404(User, id=id)
    profile = getattr(user, "userprofile", None)
    if not profile:
        raise Http404()

    courses = Course.objects.filter(
        Q(user=user) |                          # Own course 
        Q(enrollments__user=user) |             # Enrolled course
        Q(instructors__user=user)               # Instructor course
    ).annotate(avg_rating=Avg("ratings__rating")).distinct()
    
    paginator = Paginator(Status.objects.filter(user=user).order_by("-created_at"), 5)
    page_number = request.GET.get("page")
    page = paginator.get_page(page_number)
    return render(request, "profile/profile.html", {
        "profile": profile, 
        "page": page,
        "courses": courses
    })

# Protected route
@swagger_auto_schema(methods=["GET"], auto_schema=None)
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
class ProfileEditView(LoginRequiredMixin, View):
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
class StatusView(LoginRequiredMixin, View):
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
            status_created.send(sender=None, status_id=status.id) # type: ignore
            return redirect("dashboard")
        
        return render(request, "status/new.html", {"form": form})
    
    
# ================= SWAGGER =========================
class UserSearchPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 50
    
class UserSearchView(ListAPIView):
    serializer_class = UserSearchSerializer
    permission_classes = [IsAdminUser]
    filter_backends = [SearchFilter]
    search_fields = ['username', 'userprofile__name']
    pagination_class = UserSearchPagination
    
    @swagger_auto_schema(
        manual_parameters=[
            openapi.Parameter('search', openapi.IN_QUERY, type=openapi.TYPE_STRING, description='Search by username or name'),
            openapi.Parameter('role', openapi.IN_QUERY, type=openapi.TYPE_STRING, description='Filter by role', enum=['teacher', 'student']),
        ]
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    def get_queryset(self):
        return User.objects.filter(
            role=self.request.GET.get('role', 'teacher')
        ).select_related('userprofile').distinct()


class UserDetailView(RetrieveAPIView):
    serializer_class = UserProfileSerializer
    permission_classes = [IsAdminUser]
    queryset = UserProfile.objects.select_related("user")
    
    def get_object(self):
       user = get_object_or_404(User, id=self.kwargs["id"])
       profile = get_object_or_404(UserProfile, user=user)
       return profile