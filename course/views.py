from django.shortcuts import render
from rest_framework.decorators import api_view


@api_view(['GET'])
def explore(request):
    return render(request, "courses.html", {})
    
@api_view(["GET"])
def course_detail(request, id: int):
    return render(request, "detail.html", {})

@api_view(["GET"])
def new_course(request):
    return render(request, "create.html")

@api_view(["GET"])
def materials(request, cid: int, mid: int):
    return render(request, "material.html")