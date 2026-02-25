import json
from datetime import date, timedelta
from unittest.mock import patch

import factory
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from faker import Faker

from .forms import CourseForm
from .models import Course, Enrollment, Instructor, Module, Material, Progress, Rating
from .views import is_enrolled, is_eligible_to_enroll

User = get_user_model()
fake = Faker()

def _today(days=0):
    return date.today() + timedelta(days=days)


class UserFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = User

    username = factory.LazyFunction(lambda: fake.unique.user_name())
    email = factory.LazyFunction(lambda: fake.unique.email())
    password = factory.PostGenerationMethodCall("set_password", "testpass123")
    role = "student"


class TeacherFactory(UserFactory):
    role = "teacher"


class CourseFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Course

    user = factory.SubFactory(TeacherFactory)
    title = factory.LazyFunction(lambda: fake.sentence(nb_words=4))
    category = "computer-science"
    description = factory.LazyFunction(fake.paragraph)
    registration_start = factory.LazyFunction(lambda: _today(-5))
    registration_end = factory.LazyFunction(lambda: _today(5))
    course_start = factory.LazyFunction(lambda: _today(10))
    course_end = factory.LazyFunction(lambda: _today(100))
    status = "published"


class EnrollmentFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Enrollment

    user = factory.SubFactory(UserFactory)
    course = factory.SubFactory(CourseFactory)
    expired_at = factory.LazyFunction(lambda: _today(90))
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
    name = factory.LazyFunction(lambda: fake.sentence(nb_words=3)[:200])
    type = "reading"


class IsEnrolledTest(TestCase):
    def setUp(self):
        self.student = UserFactory()
        self.course = CourseFactory()

    def test_expired_enrollment_returns_false(self):
        EnrollmentFactory(user=self.student, course=self.course,
                          status="enrolled", expired_at=date.today())
        self.assertFalse(is_enrolled(self.student, self.course))

    def test_blocked_enrollment_returns_false(self):
        EnrollmentFactory(user=self.student, course=self.course,
                          status="blocked", expired_at=_today(10))
        self.assertFalse(is_enrolled(self.student, self.course))


class IsEligibleToEnrollTest(TestCase):
    def setUp(self):
        self.student = UserFactory(role="student")
        self.course = CourseFactory()

    def test_teacher_cannot_enroll(self):
        self.assertFalse(is_eligible_to_enroll(TeacherFactory(), self.course))

    def test_blocked_and_expired_student_still_cannot_enroll(self):
        EnrollmentFactory(user=self.student, course=self.course,
                          status="blocked", expired_at=_today(-10))
        self.assertFalse(is_eligible_to_enroll(self.student, self.course))

    def test_expired_enrollment_allows_reenroll(self):
        EnrollmentFactory(user=self.student, course=self.course,
                          status="enrolled", expired_at=_today(-1))
        self.assertTrue(is_eligible_to_enroll(self.student, self.course))


class CourseFormValidationTest(TestCase):
    def _data(self, **overrides):
        data = {
            "title": "Test Course",
            "category": "computer-science",
            "description": "A detailed description of the course.",
            "registration_start": _today(0).isoformat(),
            "registration_end": _today(5).isoformat(),
            "course_start": _today(10).isoformat(),
            "course_end": _today(100).isoformat(),
        }
        data.update(overrides)
        return data

    def test_reg_end_before_reg_start_is_invalid(self):
        form = CourseForm(self._data(
            registration_start=_today(5).isoformat(),
            registration_end=_today(0).isoformat(),
        ))
        self.assertFalse(form.is_valid())
        self.assertIn("registration_end", form.errors)

    def test_reg_end_equal_to_course_start_is_valid(self):
        same_day = _today(10).isoformat()
        form = CourseForm(self._data(registration_end=same_day, course_start=same_day))
        self.assertTrue(form.is_valid(), form.errors)


class EnrollViewTest(TestCase):
    def setUp(self):
        self.student = UserFactory(role="student")
        self.course = CourseFactory()

    def _url(self, course_id=None):
        return reverse("enroll", kwargs={"id": course_id or self.course.id})

    def test_draft_course_returns_404(self):
        draft = CourseFactory(status="draft")
        self.client.force_login(self.student)
        self.assertEqual(self.client.post(self._url(draft.id)).status_code, 404)

    def test_reenrollment_refreshes_expired_at(self):
        enrollment = EnrollmentFactory(user=self.student, course=self.course,
                                       status="enrolled", expired_at=_today(-1))
        self.client.force_login(self.student)
        with patch("course.views.enrollment_created.send"):
            self.client.post(self._url())
        enrollment.refresh_from_db()
        self.assertEqual(enrollment.expired_at, self.course.course_end)



class CourseDetailViewTest(TestCase):
    def setUp(self):
        self.teacher = TeacherFactory()
        self.student = UserFactory(role="student")
        self.course = CourseFactory(user=self.teacher)

    def _url(self, course_id=None):
        return reverse("course", kwargs={"id": course_id or self.course.id})

    def test_anonymous_gets_404_for_draft(self):
        draft = CourseFactory(status="draft")
        self.assertEqual(
            self.client.get(self._url(draft.id), HTTP_ACCEPT="text/html").status_code,
            404,
        )

    def test_owner_bypasses_draft_404_and_is_redirected(self):
        draft = CourseFactory(user=self.teacher, status="draft")
        self.client.force_login(self.teacher)
        response = self.client.get(self._url(draft.id), HTTP_ACCEPT="text/html")
        self.assertRedirects(
            response,
            reverse("material_overview", kwargs={"cid": draft.id}),
            fetch_redirect_response=False,
        )


class MaterialOverviewViewTest(TestCase):
    def setUp(self):
        self.owner = TeacherFactory()
        self.student = UserFactory(role="student")
        self.course = CourseFactory(user=self.owner)

    def _url(self):
        return reverse("material_overview", kwargs={"cid": self.course.id})

    def test_blocked_student_is_redirected_to_course_detail(self):
        EnrollmentFactory(user=self.student, course=self.course,
                          status="blocked", expired_at=_today(90))
        self.client.force_login(self.student)
        self.assertRedirects(
            self.client.get(self._url()),
            reverse("course", kwargs={"id": self.course.id}),
            fetch_redirect_response=False,
        )

    def test_expired_student_is_redirected_to_course_detail(self):
        EnrollmentFactory(user=self.student, course=self.course,
                          status="enrolled", expired_at=_today(-1))
        self.client.force_login(self.student)
        self.assertRedirects(
            self.client.get(self._url()),
            reverse("course", kwargs={"id": self.course.id}),
            fetch_redirect_response=False,
        )


class StudentOverviewPermissionTest(TestCase):
    """
    BUG: StudentOverviewView uses StudentRequiredMixin (role=student).
    This means: the course owner (teacher) is blocked from their own student
    list, while any unrelated student can freely browse it.
    """

    def setUp(self):
        self.owner = TeacherFactory()
        self.course = CourseFactory(user=self.owner)
        EnrollmentFactory(course=self.course)
        self.other_student = UserFactory(role="student")  # no relation to course

    def _url(self):
        return reverse("student_overview", kwargs={"cid": self.course.id})

    def test_owner_is_blocked_from_their_own_student_list(self):
        self.client.force_login(self.owner)
        self.assertEqual(self.client.get(self._url()).status_code, 302)

    def test_unrelated_student_can_read_full_enrollment_list(self):
        self.client.force_login(self.other_student)
        self.assertEqual(self.client.get(self._url()).status_code, 200)


class MarkedAsCompleteTest(TestCase):
    """
    BUG: The view uses Enrollment.objects.filter(...).exists() instead of
    is_enrolled(), so blocked and expired students can still record progress.
    """

    def setUp(self):
        self.student = UserFactory(role="student")
        self.course = CourseFactory()
        self.module = ModuleFactory(course=self.course)
        self.material = MaterialFactory(module=self.module)

    def _url(self):
        return reverse("marked_as_complete",
                       kwargs={"cid": self.course.id, "mid": self.material.id})

    def test_blocked_student_can_mark_progress(self):
        EnrollmentFactory(user=self.student, course=self.course,
                          status="blocked", expired_at=_today(90))
        self.client.force_login(self.student)
        self.client.post(self._url())
        self.assertTrue(
            Progress.objects.filter(user=self.student, material=self.material).exists()
        )

    def test_expired_student_can_mark_progress(self):
        EnrollmentFactory(user=self.student, course=self.course,
                          status="enrolled", expired_at=_today(-1))
        self.client.force_login(self.student)
        self.client.post(self._url())
        self.assertTrue(
            Progress.objects.filter(user=self.student, material=self.material).exists()
        )

class RatingViewTest(TestCase):
    def setUp(self):
        self.student = UserFactory(role="student")
        self.course = CourseFactory()
        EnrollmentFactory(user=self.student, course=self.course,
                          status="enrolled", expired_at=_today(90))

    def _url(self):
        return reverse("rating_overview", kwargs={"cid": self.course.id})

    def test_second_rating_adds_new_row_and_last_is_used(self):
        self.client.force_login(self.student)
        self.client.post(self._url(), {"rating": 3, "text": "It was okay I guess."})
        self.client.post(self._url(), {"rating": 5, "text": "Actually it was amazing!"})
        self.assertEqual(
            Rating.objects.filter(user=self.student, course=self.course).count(), 2
        )
        latest = Rating.objects.filter(user=self.student, course=self.course).last()
        self.assertIsNotNone(latest)
        self.assertEqual(latest.rating, 5)  # type: ignore[union-attr]


class ModuleDeleteCascadeTest(TestCase):
    def setUp(self):
        self.owner = TeacherFactory()
        self.course = CourseFactory(user=self.owner)
        self.module = ModuleFactory(course=self.course)
        self.material = MaterialFactory(module=self.module)
        student = UserFactory(role="student")
        EnrollmentFactory(user=student, course=self.course)
        Progress.objects.create(user=student, material=self.material)

    def test_delete_cascades_to_material_and_progress(self):
        material_id = self.material.id
        self.client.force_login(self.owner)
        self.client.delete(
            reverse("module", kwargs={"cid": self.course.id}),
            data=json.dumps({"module_id": self.module.id}),
            content_type="application/json",
        )
        self.assertFalse(Material.objects.filter(id=material_id).exists())
        self.assertFalse(Progress.objects.filter(material_id=material_id).exists())



class InstructorManagementTest(TestCase):
    def setUp(self):
        self.owner = TeacherFactory()
        self.course = CourseFactory(user=self.owner)
        self.new_instructor = TeacherFactory()

    def _url(self):
        return reverse("instructor_overview", kwargs={"cid": self.course.id})

    def test_adding_same_instructor_twice_creates_no_duplicate(self):
        Instructor.objects.create(user=self.new_instructor, course=self.course)
        self.client.force_login(self.owner)
        self.client.post(self._url(), {"user_id": self.new_instructor.id})
        self.assertEqual(
            Instructor.objects.filter(
                user=self.new_instructor, course=self.course
            ).count(),
            1,
        )