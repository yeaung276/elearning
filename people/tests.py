import json
import shutil
import tempfile
from unittest.mock import patch

import factory
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from faker import Faker

from .forms import ProfileUpdateForm, RegistrationForm, StatusForm
from .models import Status, UserProfile
from .templatetags.role_check import is_owner, is_student, is_teacher

User = get_user_model()
fake = Faker()


class UserFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = User

    username = factory.LazyFunction(lambda: fake.unique.user_name())
    email = factory.LazyFunction(lambda: fake.unique.email())
    password = factory.PostGenerationMethodCall("set_password", "testpass123")
    role = "student"


class TeacherFactory(UserFactory):
    role = "teacher"


class UserProfileFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = UserProfile

    user = factory.SubFactory(UserFactory)
    name = factory.LazyFunction(fake.name)
    title = factory.LazyFunction(fake.job)
    location = factory.LazyFunction(fake.city)
    bio = factory.LazyFunction(fake.paragraph)


class StatusFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Status

    user = factory.SubFactory(UserFactory)
    text = factory.LazyFunction(lambda: fake.text(max_nb_chars=200))


class RegistrationFormTest(TestCase):
    def _valid_data(self, **overrides):
        password = fake.password(length=12, special_chars=True, digits=True)
        data = {
            "username": fake.unique.user_name(),
            "email": fake.unique.email(),
            "role": "student",
            "password1": password,
            "password2": password,
        }
        data.update(overrides)
        return data

    def test_valid_form(self):
        form = RegistrationForm(self._valid_data())
        self.assertTrue(form.is_valid(), form.errors)

    def test_duplicate_email_rejected(self):
        existing = UserFactory()
        form = RegistrationForm(self._valid_data(email=existing.email))
        self.assertFalse(form.is_valid())
        self.assertIn("email", form.errors)

    def test_missing_email_rejected(self):
        form = RegistrationForm(self._valid_data(email=""))
        self.assertFalse(form.is_valid())
        self.assertIn("email", form.errors)

    def test_password_mismatch_rejected(self):
        data = self._valid_data()
        data["password2"] = fake.password(length=12)
        form = RegistrationForm(data)
        self.assertFalse(form.is_valid())
        self.assertIn("password2", form.errors)

    def test_student_role_accepted(self):
        form = RegistrationForm(self._valid_data(role="student"))
        self.assertTrue(form.is_valid(), form.errors)

    def test_teacher_role_accepted(self):
        form = RegistrationForm(self._valid_data(role="teacher"))
        self.assertTrue(form.is_valid(), form.errors)

class ProfileUpdateFormTest(TestCase):
    def _valid_data(self, **overrides):
        data = {
            "name": fake.name(),
            "title": fake.job(),
            "location": fake.city(),
            "bio": "",
        }
        data.update(overrides)
        return data

    def test_valid_without_bio_and_picture(self):
        form = ProfileUpdateForm(self._valid_data())
        self.assertTrue(form.is_valid(), form.errors)

    def test_bio_is_optional(self):
        form = ProfileUpdateForm(self._valid_data(bio=""))
        self.assertTrue(form.is_valid(), form.errors)

    def test_missing_name_invalid(self):
        form = ProfileUpdateForm(self._valid_data(name=""))
        self.assertFalse(form.is_valid())
        self.assertIn("name", form.errors)

    def test_missing_title_invalid(self):
        form = ProfileUpdateForm(self._valid_data(title=""))
        self.assertFalse(form.is_valid())
        self.assertIn("title", form.errors)

    def test_missing_location_invalid(self):
        form = ProfileUpdateForm(self._valid_data(location=""))
        self.assertFalse(form.is_valid())
        self.assertIn("location", form.errors)

    def test_valid_with_picture(self):
        form = ProfileUpdateForm(
            self._valid_data(),
            files={"picture": SimpleUploadedFile("pic.png", fake.image(size=(10, 10), image_format="png"), content_type="image/png")},
        )
        self.assertTrue(form.is_valid(), form.errors)

class StatusFormTest(TestCase):
    def test_valid_text_only(self):
        form = StatusForm({"text": fake.sentence()})
        self.assertTrue(form.is_valid(), form.errors)

    def test_text_required(self):
        form = StatusForm({"text": ""})
        self.assertFalse(form.is_valid())
        self.assertIn("text", form.errors)

    def test_image_is_optional(self):
        form = StatusForm({"text": fake.sentence()})
        self.assertTrue(form.is_valid(), form.errors)

    def test_valid_with_image(self):
        form = StatusForm(
            {"text": fake.sentence()},
            files={"image": SimpleUploadedFile("img.png", fake.image(size=(10, 10), image_format="png"), content_type="image/png")},
        )
        self.assertTrue(form.is_valid(), form.errors)

class RoleCheckTagsTest(TestCase):
    def setUp(self):
        self.teacher = TeacherFactory()
        self.student = UserFactory(role="student")

    def test_is_teacher_true(self):
        self.assertTrue(is_teacher(self.teacher))

    def test_is_teacher_false_for_student(self):
        self.assertFalse(is_teacher(self.student))

    def test_is_teacher_false_for_anonymous(self):
        from django.contrib.auth.models import AnonymousUser
        self.assertFalse(is_teacher(AnonymousUser()))

    def test_is_student_true(self):
        self.assertTrue(is_student(self.student))

    def test_is_student_false_for_teacher(self):
        self.assertFalse(is_student(self.teacher))

    def test_is_student_false_for_anonymous(self):
        from django.contrib.auth.models import AnonymousUser
        self.assertFalse(is_student(AnonymousUser()))

    def test_is_owner_true(self):
        resource = Status(user=self.teacher)
        self.assertTrue(is_owner(self.teacher, resource))

    def test_is_owner_false_for_different_user(self):
        resource = Status(user=self.teacher)
        self.assertFalse(is_owner(self.student, resource))

    def test_is_owner_false_for_anonymous(self):
        from django.contrib.auth.models import AnonymousUser
        resource = Status(user=self.teacher)
        self.assertFalse(is_owner(AnonymousUser(), resource))

class RegisterViewTest(TestCase):
    URL = "/register/"

    def _post_data(self, **overrides):
        password = fake.password(length=12, special_chars=True, digits=True)
        data = {
            "username": fake.unique.user_name(),
            "email": fake.unique.email(),
            "role": "student",
            "password1": password,
            "password2": password,
        }
        data.update(overrides)
        return data

    def test_get_renders_form(self):
        response = self.client.get(self.URL)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "registration/register.html")

    def test_authenticated_user_redirected_to_dashboard(self):
        self.client.force_login(UserFactory())
        response = self.client.get(self.URL)
        self.assertRedirects(response, reverse("dashboard"), fetch_redirect_response=False)

    def test_post_valid_creates_user_and_logs_in(self):
        data = self._post_data()
        response = self.client.post(self.URL, data)
        self.assertRedirects(response, reverse("dashboard"), fetch_redirect_response=False)
        self.assertTrue(User.objects.filter(username=data["username"]).exists())
        self.assertIn("_auth_user_id", self.client.session)

    def test_post_invalid_rerenders_form(self):
        before = User.objects.count()
        response = self.client.post(self.URL, {"username": "", "email": "", "role": "student"})
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "registration/register.html")
        self.assertEqual(User.objects.count(), before)

    def test_post_duplicate_email_fails(self):
        existing = UserFactory()
        before = User.objects.count()
        response = self.client.post(self.URL, self._post_data(email=existing.email))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(User.objects.count(), before)

class LoginViewTest(TestCase):
    URL = "/login/"

    def setUp(self):
        self.password = "testpass123"
        self.user = UserFactory(password=self.password)

    def test_get_renders_login_form(self):
        response = self.client.get(self.URL)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "registration/login.html")

    def test_valid_credentials_log_in(self):
        response = self.client.post(self.URL, {
            "username": self.user.username,
            "password": self.password,
        })
        self.assertEqual(response.status_code, 302)
        self.assertIn("_auth_user_id", self.client.session)

    def test_invalid_credentials_rejected(self):
        response = self.client.post(self.URL, {
            "username": self.user.username,
            "password": fake.password(),
        })
        self.assertEqual(response.status_code, 200)
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_already_authenticated_redirected(self):
        # redirect_authenticated_user=True is set on LoginView in people/urls.py
        self.client.force_login(self.user)
        response = self.client.get(self.URL)
        self.assertEqual(response.status_code, 302)

class DashboardViewTest(TestCase):
    URL = "/dashboard/"

    def setUp(self):
        self.student = UserFactory(role="student")
        self.teacher = TeacherFactory()

    def test_unauthenticated_redirects_to_login(self):
        response = self.client.get(self.URL)
        self.assertEqual(response.status_code, 302)
        self.assertIn("/login/", response["Location"])

    def test_user_without_profile_redirected_to_profile_edit(self):
        self.client.force_login(self.student)
        response = self.client.get(self.URL, HTTP_ACCEPT="text/html")
        self.assertRedirects(response, reverse("profile_edit"), fetch_redirect_response=False)

    def test_user_with_profile_sees_dashboard(self):
        UserProfileFactory(user=self.student)
        self.client.force_login(self.student)
        response = self.client.get(self.URL, HTTP_ACCEPT="text/html")
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "dashboard.html")

    def test_statuses_paginated_at_five(self):
        UserProfileFactory(user=self.student)
        StatusFactory.create_batch(7, user=self.student)
        self.client.force_login(self.student)
        response = self.client.get(self.URL, HTTP_ACCEPT="text/html")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context["page"].object_list), 5)

    def test_teacher_can_access_dashboard(self):
        UserProfileFactory(user=self.teacher)
        self.client.force_login(self.teacher)
        response = self.client.get(self.URL, HTTP_ACCEPT="text/html")
        self.assertEqual(response.status_code, 200)

    def test_student_can_access_dashboard(self):
        UserProfileFactory(user=self.student)
        self.client.force_login(self.student)
        response = self.client.get(self.URL, HTTP_ACCEPT="text/html")
        self.assertEqual(response.status_code, 200)

class PublicProfileViewTest(TestCase):
    def setUp(self):
        self.user = UserFactory(role="student")
        self.profile = UserProfileFactory(user=self.user)

    def _url(self, user_id=None):
        return reverse("profile", kwargs={"id": user_id or self.user.pk})

    def test_anonymous_user_can_access(self):
        response = self.client.get(self._url(), HTTP_ACCEPT="text/html")
        self.assertEqual(response.status_code, 200)

    def test_authenticated_user_can_access(self):
        self.client.force_login(UserFactory())
        response = self.client.get(self._url(), HTTP_ACCEPT="text/html")
        self.assertEqual(response.status_code, 200)

    def test_nonexistent_user_returns_404(self):
        response = self.client.get(self._url(99999), HTTP_ACCEPT="text/html")
        self.assertEqual(response.status_code, 404)

    def test_user_without_profile_returns_404(self):
        user_without_profile = UserFactory()
        response = self.client.get(self._url(user_without_profile.pk), HTTP_ACCEPT="text/html")
        self.assertEqual(response.status_code, 404)

    def test_profile_data_in_context(self):
        response = self.client.get(self._url(), HTTP_ACCEPT="text/html")
        self.assertEqual(response.context["profile"], self.profile)

    def test_statuses_appear_in_context(self):
        StatusFactory(user=self.user)
        response = self.client.get(self._url(), HTTP_ACCEPT="text/html")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context["page"].object_list), 1)

    def test_uses_profile_template(self):
        response = self.client.get(self._url(), HTTP_ACCEPT="text/html")
        self.assertTemplateUsed(response, "profile/profile.html")

class ProfileEditViewTest(TestCase):
    URL = "/profile/edit"

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self._override = override_settings(MEDIA_ROOT=self.tmp)
        self._override.enable()
        self.user = UserFactory()

    def tearDown(self):
        self._override.disable()
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_unauthenticated_cannot_access_get(self):
        response = self.client.get(self.URL)
        self.assertEqual(response.status_code, 302)

    def test_unauthenticated_cannot_access_post(self):
        response = self.client.post(self.URL, {
            "name": fake.name(), "title": fake.job(), "location": fake.city(),
        })
        self.assertEqual(response.status_code, 302)

    def test_get_renders_blank_form_for_new_user(self):
        self.client.force_login(self.user)
        response = self.client.get(self.URL)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "profile/edit.html")

    def test_get_renders_prefilled_form_for_existing_profile(self):
        profile = UserProfileFactory(user=self.user, name="Prefilled Name")
        self.client.force_login(self.user)
        response = self.client.get(self.URL)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, profile.name)

    def test_post_creates_new_profile(self):
        self.client.force_login(self.user)
        response = self.client.post(self.URL, {
            "name": fake.name(),
            "title": fake.job(),
            "location": fake.city(),
            "bio": "",
        })
        self.assertRedirects(
            response,
            reverse("profile", kwargs={"id": self.user.pk}),
            fetch_redirect_response=False,
        )
        self.assertTrue(UserProfile.objects.filter(user=self.user).exists())

    def test_post_updates_existing_profile(self):
        UserProfileFactory(user=self.user, name="Old Name")
        new_name = fake.name()
        self.client.force_login(self.user)
        self.client.post(self.URL, {
            "name": new_name, "title": fake.job(), "location": fake.city(), "bio": "",
        })
        profile = UserProfile.objects.get(user=self.user)
        self.assertEqual(profile.name, new_name)

    def test_post_invalid_data_rerenders_form(self):
        self.client.force_login(self.user)
        response = self.client.post(self.URL, {"name": "", "title": "", "location": ""})
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "profile/edit.html")
        self.assertFalse(UserProfile.objects.filter(user=self.user).exists())

    def test_post_with_profile_picture_upload(self):
        self.client.force_login(self.user)
        self.client.post(self.URL, {
            "name": fake.name(),
            "title": fake.job(),
            "location": fake.city(),
            "bio": "",
            "picture": SimpleUploadedFile("profile.png", fake.image(size=(10, 10), image_format="png"), content_type="image/png"),
        })
        profile = UserProfile.objects.get(user=self.user)
        self.assertTrue(bool(profile.picture))

    def test_profile_linked_to_correct_user(self):
        self.client.force_login(self.user)
        self.client.post(self.URL, {
            "name": fake.name(), "title": fake.job(), "location": fake.city(), "bio": "",
        })
        profile = UserProfile.objects.get(user=self.user)
        self.assertEqual(profile.user, self.user)

class StatusViewTest(TestCase):
    URL = "/status/new"

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self._override = override_settings(MEDIA_ROOT=self.tmp)
        self._override.enable()
        self.user = UserFactory()
        UserProfileFactory(user=self.user)

    def tearDown(self):
        self._override.disable()
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_unauthenticated_redirected(self):
        response = self.client.get(self.URL)
        self.assertEqual(response.status_code, 302)

    def test_get_renders_form(self):
        self.client.force_login(self.user)
        response = self.client.get(self.URL)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "status/new.html")

    def test_post_text_only_creates_status(self):
        text = fake.sentence()
        self.client.force_login(self.user)
        with patch("people.views.status_created.send"):
            response = self.client.post(self.URL, {"text": text})
        self.assertRedirects(response, reverse("dashboard"), fetch_redirect_response=False)
        self.assertTrue(Status.objects.filter(user=self.user, text=text).exists())

    def test_post_with_image_creates_status(self):
        text = fake.sentence()
        self.client.force_login(self.user)
        with patch("people.views.status_created.send"):
            self.client.post(self.URL, {"text": text, "image": SimpleUploadedFile("status.png", fake.image(size=(10, 10), image_format="png"), content_type="image/png")})
        status = Status.objects.get(user=self.user, text=text)
        self.assertTrue(bool(status.image))

    def test_post_empty_text_fails(self):
        self.client.force_login(self.user)
        before = Status.objects.count()
        response = self.client.post(self.URL, {"text": ""})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Status.objects.count(), before)

    def test_status_linked_to_current_user(self):
        text = fake.sentence()
        self.client.force_login(self.user)
        with patch("people.views.status_created.send"):
            self.client.post(self.URL, {"text": text})
        self.assertEqual(Status.objects.get(text=text).user, self.user)

    def test_status_created_signal_sent(self):
        text = fake.sentence()
        self.client.force_login(self.user)
        with patch("people.views.status_created.send") as mock_send:
            self.client.post(self.URL, {"text": text})
            mock_send.assert_called_once()
            status = Status.objects.get(text=text)
            self.assertEqual(mock_send.call_args[1]["status_id"], status.pk)
