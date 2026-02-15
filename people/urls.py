from django.urls import path
from django.contrib.auth import views as auth_views

from .views import profile, dashboard, RegisterView, ProfileEditView, StatusEditView

urlpatterns = [
    path("login/", auth_views.LoginView.as_view(redirect_authenticated_user=True), name="login"),
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),
    path("register/", RegisterView.as_view(), name="register"),
    
    path("profile/edit", ProfileEditView.as_view(), name="profile_edit"),
    path('profile/<int:id>', profile, name="profile"),
    
    path("status/new", StatusEditView.as_view(), name="status_edit"),
    
    path("dashboard/", dashboard, name="dashboard")
]