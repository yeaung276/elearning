from django.contrib.auth.mixins import UserPassesTestMixin
from django.shortcuts import redirect
from django.http import HttpRequest

# Mixins
class TeacherRequiredMixin(UserPassesTestMixin):
    """
    Mixin that restricts access to users with 'teacher' role only.
    """
    request: HttpRequest
    permission_denied_url = "dashboard"
    
    def test_func(self):
        return self.request.user.role == 'teacher'  # type: ignore
    
    def handle_no_permission(self):
        return redirect(self.permission_denied_url)
    
class StudentRequiredMixin(UserPassesTestMixin):
    """
    Mixin that restricts access to users with 'student' role only.
    """
    request: HttpRequest
    permission_denied_url = "dashboard"
    
    def test_func(self):
        return self.request.user.role == 'student'  # type: ignore
    
    def handle_no_permission(self):
        return redirect(self.permission_denied_url)
    
# Auth control
def is_teacher(user):
    if not user or not user.is_authenticated:
        return False
    return getattr(user, 'role', None) == 'teacher'


def is_student(user):
    if not user or not user.is_authenticated:
        return False
    return getattr(user, 'role', None) == 'student'


def is_owner(user, resource):
    if not user or not user.is_authenticated:
        return False
    return user == getattr(resource, 'user', None)