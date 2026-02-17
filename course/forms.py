from django import forms
from .models import Course, Rating, Module


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
            "status": forms.Select(attrs={
                "class": "w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent",
            }),
        }
    
    def __init__(self, *args, show_status=False, disabled=False, **kwargs):
        super().__init__(*args, **kwargs)
    
        if not show_status:
            self.fields.pop('status', None)
        
        if disabled:
            for field in self.fields.values():
                field.widget.attrs['disabled'] = 'disabled'
        
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
    
    
class RatingForm(forms.ModelForm):
    class Meta:
        model = Rating
        fields = ["rating", "text"]

        widgets = {
            "rating": forms.HiddenInput(attrs={
                "id": "rating-input",
            }),
            "text": forms.Textarea(attrs={
                "rows": 5,
                "class": "w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition resize-none",
                "placeholder": "Write your thoughts about this course...",
            }),
        }
        
    def clean_rating(self):
        rating = self.cleaned_data.get("rating")
        if rating is None:
            raise forms.ValidationError("Please select a star rating.")
        if not (1 <= rating <= 5):
            raise forms.ValidationError("Rating must be between 1 and 5.")
        return rating

    def clean_text(self):
        text = self.cleaned_data.get("text", "").strip()
        if not text:
            raise forms.ValidationError("Please write a review.")
        if len(text) < 10:
            raise forms.ValidationError("Review must be at least 10 characters.")
        return text
