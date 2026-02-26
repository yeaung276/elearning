from rest_framework import serializers
from .models import Course, Rating, Module

class CourseSearchSerializer(serializers.ModelSerializer):
    avg_rating = serializers.FloatField(read_only=True)
    enrollment_count = serializers.IntegerField(read_only=True)
    rating_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Course
        fields = [
            'id',
            'title',
            'subtitle',
            'description',
            'category',
            'cover_img',
            'avg_rating',
            'enrollment_count',
            'rating_count',
            'created_at',
        ]
        
class RatingSerializer(serializers.ModelSerializer):
    class Meta:
        model  = Rating
        fields = ['rating', 'text', 'created_at']
        
class ModuleSerializer(serializers.ModelSerializer):
    video_count = serializers.IntegerField(read_only=True)
    reading_count = serializers.IntegerField(read_only=True)

    class Meta:
        model  = Module
        fields = ['name', 'video_count', 'reading_count']
        
class CourseDetailSerializer(serializers.ModelSerializer):
    avg_rating = serializers.FloatField(read_only=True)
    rating_count = serializers.IntegerField(read_only=True)
    modules = ModuleSerializer(many=True, read_only=True)
    reviews = RatingSerializer(many=True, read_only=True, source='ratings')

    class Meta:
        model  = Course
        fields = [
            'id',
            'title',
            'subtitle',
            'category',
            'description',
            'cover_img',
            'registration_start',
            'registration_end',
            'course_start',
            'course_end',
            'created_at',
            'avg_rating',
            'rating_count',
            'modules',
            'reviews',
        ]