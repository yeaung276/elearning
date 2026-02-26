from django.urls import path
from django.contrib.auth import views as auth_views

from .views import profile, dashboard, RegisterView, ProfileEditView, StatusView, search_user, UserSearchView, UserDetailView

urlpatterns = [
    path("login/", auth_views.LoginView.as_view(redirect_authenticated_user=True), name="login"),
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),
    path("register/", RegisterView.as_view(), name="register"),
    
    path("profile/edit", ProfileEditView.as_view(), name="profile_edit"),
    path('profile/search', search_user, name="search_user"),
    path('profile/<int:id>', profile, name="profile"),
    
    path("status/new", StatusView.as_view(), name="status"),
    
    path("dashboard/", dashboard, name="dashboard"),
    
    path("api/user/search", UserSearchView.as_view(), name="search_user_api"),
    path("api/user/<int:id>", UserDetailView.as_view(), name="detail_user_api"),
]