from django.contrib.auth.mixins import UserPassesTestMixin
from django.shortcuts import redirect
from django.http import HttpRequest

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