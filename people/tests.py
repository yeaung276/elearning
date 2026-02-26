import shutil
import tempfile
from unittest.mock import patch

import factory
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from faker import Faker

from .forms import RegistrationForm, StatusForm
from .models import Status, UserProfile
from .templatetags.role_check import is_owner, is_teacher

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
    def _data(self, **overrides):
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

    def test_duplicate_email_rejected(self):
        existing = UserFactory()
        form = RegistrationForm(self._data(email=existing.email))
        self.assertFalse(form.is_valid())
        self.assertIn("email", form.errors)

    def test_password_mismatch_rejected(self):
        data = self._data()
        data["password2"] = fake.password(length=12)
        form = RegistrationForm(data)
        self.assertFalse(form.is_valid())
        self.assertIn("password2", form.errors)


class StatusFormTest(TestCase):
    def test_text_required(self):
        form = StatusForm({"text": ""})
        self.assertFalse(form.is_valid())
        self.assertIn("text", form.errors)


class RoleCheckTagsTest(TestCase):
    def setUp(self):
        self.teacher = TeacherFactory()
        self.student = UserFactory(role="student")

    def test_is_teacher_true(self):
        self.assertTrue(is_teacher(self.teacher))

    def test_is_teacher_false_for_anonymous(self):
        from django.contrib.auth.models import AnonymousUser
        self.assertFalse(is_teacher(AnonymousUser()))

    def test_is_owner_true(self):
        resource = Status(user=self.teacher)
        self.assertTrue(is_owner(self.teacher, resource))


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


class DashboardViewTest(TestCase):
    URL = "/dashboard/"

    def setUp(self):
        self.student = UserFactory(role="student")

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


class PublicProfileViewTest(TestCase):
    def setUp(self):
        self.user = UserFactory(role="student")
        UserProfileFactory(user=self.user)

    def _url(self, user_id=None):
        return reverse("profile", kwargs={"id": user_id or self.user.pk})

    def test_anonymous_user_can_access(self):
        response = self.client.get(self._url(), HTTP_ACCEPT="text/html")
        self.assertEqual(response.status_code, 200)

    def test_nonexistent_user_returns_404(self):
        response = self.client.get(self._url(99999), HTTP_ACCEPT="text/html")
        self.assertEqual(response.status_code, 404)

    def test_user_without_profile_returns_404(self):
        no_profile = UserFactory()
        response = self.client.get(self._url(no_profile.pk), HTTP_ACCEPT="text/html")
        self.assertEqual(response.status_code, 404)


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

    def test_unauthenticated_cannot_access(self):
        self.assertEqual(self.client.get(self.URL).status_code, 302)

    def test_post_creates_new_profile(self):
        self.client.force_login(self.user)
        response = self.client.post(self.URL, {
            "name": fake.name(), "title": fake.job(), "location": fake.city(), "bio": "",
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
        self.assertEqual(UserProfile.objects.get(user=self.user).name, new_name)

    def test_post_with_profile_picture_upload(self):
        self.client.force_login(self.user)
        self.client.post(self.URL, {
            "name": fake.name(),
            "title": fake.job(),
            "location": fake.city(),
            "bio": "",
            "picture": SimpleUploadedFile("profile.png", fake.image(size=(10, 10), image_format="png"), content_type="image/png"),
        })
        self.assertTrue(bool(UserProfile.objects.get(user=self.user).picture))

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
        self.assertEqual(self.client.get(self.URL).status_code, 302)

    def test_post_text_only_creates_status(self):
        text = fake.sentence()
        self.client.force_login(self.user)
        with patch("people.views.status_created.send"):
            self.client.post(self.URL, {"text": text})
        self.assertTrue(Status.objects.filter(user=self.user, text=text).exists())

    def test_post_with_image_creates_status(self):
        text = fake.sentence()
        self.client.force_login(self.user)
        with patch("people.views.status_created.send"):
            self.client.post(self.URL, {"text": text, "image": SimpleUploadedFile("status.png", fake.image(size=(10, 10), image_format="png"), content_type="image/png")})
        self.assertTrue(bool(Status.objects.get(user=self.user, text=text).image))

    def test_status_created_signal_sent(self):
        text = fake.sentence()
        self.client.force_login(self.user)
        with patch("people.views.status_created.send") as mock_send:
            self.client.post(self.URL, {"text": text})
            mock_send.assert_called_once()
            self.assertEqual(mock_send.call_args[1]["status_id"], Status.objects.get(text=text).pk)