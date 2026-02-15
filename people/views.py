from django.contrib.auth.mixins import LoginRequiredMixin
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from rest_framework.decorators import api_view
from django.contrib.auth import get_user_model
from django.shortcuts import render, redirect
from django.contrib.auth import login
from django.views import View
from django.http import Http404

from .forms import RegistrationForm, ProfileUpdateForm
from .models import UserProfile


User = get_user_model()

# ============ Dashboard ===================
@api_view(["GET"])
def dashboard(request):
    if not request.user.is_authenticated:
        return redirect("login")

    if not UserProfile.objects.filter(user=request.user).exists():
        return redirect("profile_edit")

    return render(request, "dashboard.html")

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

# ============== Profile =================
# Public route
@api_view(["GET"])
def profile(request, id: int):
    user = get_object_or_404(User, id=id)
    profile = getattr(user, "userprofile", None)
    if not profile:
        raise Http404

    return render(request, "profile/profile.html", {"profile": profile})



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
            return redirect("profile_me")

        return render(request, "profile/edit.html", {"form": form})
       