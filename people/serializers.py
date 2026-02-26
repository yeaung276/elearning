from rest_framework import serializers
from rest_framework.pagination import PageNumberPagination
from django.contrib.auth import get_user_model
from django.db.models import Q, Avg

from course.models import Course
from .models import Status, UserProfile

User = get_user_model()

class UserSearchSerializer(serializers.ModelSerializer):
    name = serializers.CharField(source='userprofile.name')
    profile_img = serializers.SerializerMethodField()
    title = serializers.CharField(source='userprofile.title')

    class Meta:
        model = User
        fields = ['id', 'name', 'profile_img', 'title']

    def get_profile_img(self, obj):
        request = self.context.get('request')
        try:
            if obj.userprofile.picture:
                return request.build_absolute_uri(obj.userprofile.picture.url) # type: ignore
        except User.userprofile.RelatedObjectDoesNotExist: # type: ignore
            pass
        return None


class CourseSerializer(serializers.ModelSerializer):
    avg_rating = serializers.FloatField(read_only=True)

    class Meta:
        model = Course
        fields = ['title', 'subtitle', 'category', 'description', 'cover_img', 'avg_rating']
    
    def get_cover_img(self, obj):
        request = self.context.get('request')

        if obj.cover_img:
            return request.build_absolute_uri(obj.cover_img.url) # type: ignore

        return None


class UserProfileSerializer(serializers.ModelSerializer):
    courses = serializers.SerializerMethodField()

    class Meta:
        model = UserProfile
        fields = "__all__"

    def get_courses(self, obj):
        user = obj.user
        courses = Course.objects.filter(
            Q(user=user) |
            Q(enrollments__user=user) |
            Q(instructors__user=user)
        ).annotate(avg_rating=Avg("ratings__rating")).distinct()
        return CourseSerializer(courses, many=True).data