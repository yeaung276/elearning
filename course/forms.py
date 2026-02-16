from django import forms
from .models import Course


class CourseForm(forms.ModelForm):
    class Meta:
        model = Course        
        exclude = ["user", "created_at"]

        widgets = {
            "title": forms.TextInput(attrs={
                "class": "w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent",
                "placeholder": "e.g., Introduction to Machine Learning",
            }),
            "subtitle": forms.TextInput(attrs={
                "class": "w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent",
                "placeholder": "Brief description of your course",
            }),
            "category": forms.Select(attrs={
                "class": "w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent",
            }),
            "cover_img": forms.ClearableFileInput(attrs={
                "class": "w-full px-4 py-3 border border-gray-300 rounded-lg",
            }),
            "description": forms.Textarea(attrs={
                "rows": 6,
                "class": "w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent",
                "placeholder": "Describe what students will learn in this course...",
            }),
            "registration_start": forms.DateInput(attrs={
                "type": "date",
                "class": "w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent",
            }),
            "registration_end": forms.DateInput(attrs={
                "type": "date",
                "class": "w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent",
            }),
            "course_start": forms.DateInput(attrs={
                "type": "date",
                "class": "w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent",
            }),
            "course_end": forms.DateInput(attrs={
                "type": "date",
                "class": "w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent",
            }),
        }
        
    def clean(self):
        cleaned = super().clean()

        reg_start = cleaned.get("registration_start")
        reg_end = cleaned.get("registration_end")
        course_start = cleaned.get("course_start")
        course_end = cleaned.get("course_end")

        if reg_start and reg_end and reg_start > reg_end:
            self.add_error("registration_end", "Registration end must be after start.")

        if course_start and course_end and course_start > course_end:
            self.add_error("course_end", "Course end must be after start.")

        if reg_end and course_start and reg_end > course_start:
            self.add_error("registration_end", "Registration must end before course starts.")

        return cleaned