from django.urls import path

from .views import profile, dashboard

urlpatterns = [
    path('profile/<int:id>', profile),
    path("dashboard/", dashboard)
]