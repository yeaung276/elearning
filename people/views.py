import random
from django.shortcuts import render
from rest_framework.decorators import api_view


@api_view(["GET"])
def profile(request, id: int):
    return render(request, "profile.html", {})

@api_view(["GET"])
def dashboard(request):
    return render(request, "dashboard.html")