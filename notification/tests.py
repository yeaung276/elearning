from datetime import date, timedelta
from unittest.mock import MagicMock, patch

import factory
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from faker import Faker

from course.models import Course, Enrollment, Instructor, Material, Module
from people.models import Status, UserProfile

from .models import Notifications
from .signals import enrollment_created, material_created, status_created

User = get_user_model()
fake = Faker()

MOCK_CHANNEL = "notification.consumers.get_channel_layer"
MOCK_ASYNC = "notification.consumers.async_to_sync"


# ── Factories ──────────────────────────────────────────────────────────────


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


class CourseFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Course

    user = factory.SubFactory(TeacherFactory)
    title = factory.LazyFunction(lambda: fake.sentence(nb_words=4))
    category = "computer-science"
    description = factory.LazyFunction(fake.paragraph)
    registration_start = factory.LazyFunction(lambda: date.today() - timedelta(days=30))
    registration_end = factory.LazyFunction(lambda: date.today() - timedelta(days=10))
    course_start = factory.LazyFunction(lambda: date.today() - timedelta(days=5))
    course_end = factory.LazyFunction(lambda: date.today() + timedelta(days=60))
    status = "published"


class EnrollmentFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Enrollment

    user = factory.SubFactory(UserFactory)
    course = factory.SubFactory(CourseFactory)
    expired_at = factory.LazyFunction(lambda: date.today() + timedelta(days=60))
    status = "enrolled"


class ModuleFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Module

    course = factory.SubFactory(CourseFactory)
    name = factory.LazyFunction(lambda: fake.word()[:20])


class MaterialFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Material

    module = factory.SubFactory(ModuleFactory)
    name = factory.LazyFunction(lambda: fake.sentence(nb_words=3))
    type = "reading"


class StatusFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Status

    user = factory.SubFactory(UserFactory)
    text = factory.LazyFunction(lambda: fake.text(max_nb_chars=200))


# ── Tests ──────────────────────────────────────────────────────────────────


class NotificationModelTest(TestCase):
    def test_default_is_read_is_false(self):
        user = UserFactory()
        noti = Notifications.objects.create(
            user=user,
            content="New material available.",
            notification_type="material",
            redirect_url="/",
        )
        self.assertFalse(noti.is_read)

    def test_cascade_delete_removes_notifications(self):
        user = UserFactory()
        Notifications.objects.create(
            user=user,
            content="You enrolled.",
            notification_type="enrollment",
            redirect_url="/",
        )
        uid = user.id
        user.delete()
        self.assertEqual(Notifications.objects.filter(user_id=uid).count(), 0)


class MaterialCreatedSignalTest(TestCase):
    def setUp(self):
        self.teacher = TeacherFactory()
        self.course = CourseFactory(user=self.teacher)
        self.module = ModuleFactory(course=self.course)
        self.material = MaterialFactory(module=self.module)
        self.student = UserFactory()
        self.enrollment = EnrollmentFactory(user=self.student, course=self.course)

    def _fire(self):
        with patch(MOCK_CHANNEL, return_value=MagicMock()):
            with patch(MOCK_ASYNC, return_value=MagicMock()):
                material_created.send(sender=None, mid=self.material.id)

    def test_enrolled_student_gets_notification(self):
        self._fire()
        self.assertEqual(Notifications.objects.filter(user=self.student).count(), 1)

    def test_blocked_student_excluded(self):
        self.enrollment.status = "blocked"
        self.enrollment.save()
        self._fire()
        self.assertEqual(Notifications.objects.filter(user=self.student).count(), 0)

    def test_expired_enrollment_excluded(self):
        self.enrollment.expired_at = date.today() - timedelta(days=1)
        self.enrollment.save()
        self._fire()
        self.assertEqual(Notifications.objects.filter(user=self.student).count(), 0)

    def test_notification_content_mentions_course_title(self):
        self._fire()
        noti = Notifications.objects.get(user=self.student)
        self.assertIn(self.course.title, noti.content)

    def test_notification_redirect_url_correct(self):
        self._fire()
        noti = Notifications.objects.get(user=self.student)
        expected = reverse(
            "material",
            kwargs={"cid": self.course.id, "mid": self.material.id},
        )
        self.assertEqual(noti.redirect_url, expected)


class EnrollmentCreatedSignalTest(TestCase):
    def setUp(self):
        self.teacher = TeacherFactory()
        UserProfileFactory(user=self.teacher)
        self.course = CourseFactory(user=self.teacher)
        self.student = UserFactory()
        UserProfileFactory(user=self.student)
        self.enrollment = EnrollmentFactory(user=self.student, course=self.course)

    def _fire(self):
        with patch(MOCK_CHANNEL, return_value=MagicMock()):
            with patch(MOCK_ASYNC, return_value=MagicMock()):
                enrollment_created.send(sender=None, enrollment_id=self.enrollment.id)

    def test_owner_gets_notification(self):
        self._fire()
        self.assertEqual(Notifications.objects.filter(user=self.teacher).count(), 1)

    def test_notification_content_mentions_student_name_and_course(self):
        self._fire()
        noti = Notifications.objects.get(user=self.teacher)
        self.assertIn(self.student.userprofile.name, noti.content)
        self.assertIn(self.course.title, noti.content)

    def test_instructor_gets_notification(self):
        instructor_user = TeacherFactory()
        Instructor.objects.create(user=instructor_user, course=self.course)
        self._fire()
        self.assertEqual(Notifications.objects.filter(user=instructor_user).count(), 1)

    def test_no_instructors_creates_one_notification(self):
        self._fire()
        self.assertEqual(Notifications.objects.count(), 1)


class TeacherStatusSignalTest(TestCase):
    def setUp(self):
        self.teacher = TeacherFactory()
        UserProfileFactory(user=self.teacher)
        self.course = CourseFactory(user=self.teacher)
        self.student = UserFactory()
        self.enrollment = EnrollmentFactory(user=self.student, course=self.course)
        self.status = StatusFactory(user=self.teacher)

    def _fire(self):
        with patch(MOCK_CHANNEL, return_value=MagicMock()):
            with patch(MOCK_ASYNC, return_value=MagicMock()):
                status_created.send(sender=None, status_id=self.status.id)

    def test_enrolled_students_notified(self):
        self._fire()
        self.assertEqual(Notifications.objects.filter(user=self.student).count(), 1)

    def test_blocked_student_excluded(self):
        self.enrollment.status = "blocked"
        self.enrollment.save()
        self._fire()
        self.assertEqual(Notifications.objects.filter(user=self.student).count(), 0)

    def test_expired_enrollment_excluded(self):
        self.enrollment.expired_at = date.today() - timedelta(days=1)
        self.enrollment.save()
        self._fire()
        self.assertEqual(Notifications.objects.filter(user=self.student).count(), 0)

    def test_notification_content_has_teacher_name(self):
        self._fire()
        noti = Notifications.objects.get(user=self.student)
        self.assertIn(self.teacher.userprofile.name, noti.content)

    def test_notification_type_is_status(self):
        self._fire()
        noti = Notifications.objects.get(user=self.student)
        self.assertEqual(noti.notification_type, "status")


class StudentStatusSignalTest(TestCase):
    def setUp(self):
        self.teacher = TeacherFactory()
        self.course = CourseFactory(user=self.teacher)
        self.poster = UserFactory()
        self.classmate = UserFactory()
        EnrollmentFactory(user=self.poster, course=self.course)
        EnrollmentFactory(user=self.classmate, course=self.course)
        self.status = StatusFactory(user=self.poster)

    def _fire(self):
        with patch(MOCK_CHANNEL, return_value=MagicMock()):
            with patch(MOCK_ASYNC, return_value=MagicMock()):
                status_created.send(sender=None, status_id=self.status.id)

    def test_classmates_notified(self):
        self._fire()
        self.assertEqual(Notifications.objects.filter(user=self.classmate).count(), 1)

    def test_poster_excluded(self):
        self._fire()
        self.assertEqual(Notifications.objects.filter(user=self.poster).count(), 0)

    def test_blocked_classmate_excluded(self):
        blocked = UserFactory()
        EnrollmentFactory(user=blocked, course=self.course, status="blocked")
        self._fire()
        self.assertEqual(Notifications.objects.filter(user=blocked).count(), 0)

    def test_redirect_url_points_to_poster_profile(self):
        self._fire()
        noti = Notifications.objects.get(user=self.classmate)
        expected = reverse("profile", kwargs={"id": self.poster.id})
        self.assertEqual(noti.redirect_url, expected)
