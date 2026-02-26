"""
URL configuration for elearning project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.conf import settings
from django.contrib import admin
from django.urls import path, include
from django.conf.urls.static import static
from django.views.generic import RedirectView

from rest_framework.authentication import SessionAuthentication

from drf_yasg import openapi
from drf_yasg.views import get_schema_view as get_swagger_schema_view

schema_view = get_swagger_schema_view(
    openapi.Info(
        title="Elearning API",
        default_version="1.0.0",
        description="API documentation Elearning application"
    ),
    public=True,
    authentication_classes=[
        SessionAuthentication
    ]
)


urlpatterns = [
    path('admin/', admin.site.urls),
    path("", include("course.urls")),
    path("", include("people.urls")),
    path("", include("message.urls")),
    path("", RedirectView.as_view(pattern_name="dashboard", permanent=False)),
    path("docs/", schema_view.with_ui("swagger", cache_timeout=10), name="docs"),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
