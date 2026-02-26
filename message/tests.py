from unittest.mock import MagicMock, patch

import factory
from django.contrib.auth import get_user_model
from django.db import IntegrityError
from django.test import TestCase
from django.urls import reverse
from faker import Faker

from people.models import UserProfile

from .models import Conversation, ConversationParticipant, Message

User = get_user_model()
fake = Faker()

MOCK_CHANNEL = "message.views.get_channel_layer"
MOCK_ASYNC = "message.views.async_to_sync"

class UserFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = User

    username = factory.LazyFunction(lambda: fake.unique.user_name())
    email = factory.LazyFunction(lambda: fake.unique.email())
    password = factory.PostGenerationMethodCall("set_password", "testpass123")
    role = "student"


class UserProfileFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = UserProfile

    user = factory.SubFactory(UserFactory)
    name = factory.LazyFunction(fake.name)
    title = factory.LazyFunction(fake.job)
    location = factory.LazyFunction(fake.city)


class ConversationFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Conversation


class MessageFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Message

    conversation = factory.SubFactory(ConversationFactory)
    sender = factory.SubFactory(UserFactory)
    content = factory.LazyFunction(lambda: fake.sentence())


# ── Model Tests ────────────────────────────────────────────────────────────


class ConversationModelTest(TestCase):
    def test_duplicate_participant_raises_integrity_error(self):
        conv = ConversationFactory()
        user = UserFactory()
        ConversationParticipant.objects.create(conversation=conv, user=user)
        with self.assertRaises(IntegrityError):
            ConversationParticipant.objects.create(conversation=conv, user=user)

    def test_message_sender_becomes_null_on_user_delete(self):
        user = UserFactory()
        conv = ConversationFactory()
        msg = MessageFactory(conversation=conv, sender=user)
        user.delete()
        msg.refresh_from_db()
        self.assertIsNone(msg.sender)

    def test_cascade_delete_conversation_removes_messages(self):
        conv = ConversationFactory()
        MessageFactory(conversation=conv)
        MessageFactory(conversation=conv)
        cid = conv.id
        conv.delete()
        self.assertEqual(Message.objects.filter(conversation_id=cid).count(), 0)


class ThreadsViewTest(TestCase):
    def setUp(self):
        self.user = UserFactory()
        self.client.login(username=self.user.username, password="testpass123")
        self.url = reverse("threads")

    def test_unauthenticated_returns_4xx(self):
        self.client.logout()
        resp = self.client.get(self.url, HTTP_ACCEPT="text/html")
        self.assertGreaterEqual(resp.status_code, 400)

    def test_no_conversations_returns_empty_list(self):
        resp = self.client.get(self.url, HTTP_ACCEPT="text/html")
        self.assertEqual(resp.status_code, 200)
        self.assertQuerySetEqual(resp.context["threads"], [])

    def test_returns_conversation_partners(self):
        other = UserFactory()
        conv = ConversationFactory()
        ConversationParticipant.objects.create(conversation=conv, user=self.user)
        ConversationParticipant.objects.create(conversation=conv, user=other)

        resp = self.client.get(self.url, HTTP_ACCEPT="text/html")
        self.assertIn(other, resp.context["threads"])

    def test_excludes_current_user_from_threads(self):
        other = UserFactory()
        conv = ConversationFactory()
        ConversationParticipant.objects.create(conversation=conv, user=self.user)
        ConversationParticipant.objects.create(conversation=conv, user=other)

        resp = self.client.get(self.url, HTTP_ACCEPT="text/html")
        self.assertNotIn(self.user, resp.context["threads"])

class MessageViewTest(TestCase):
    def setUp(self):
        self.user = UserFactory()
        self.other = UserFactory()
        self.client.login(username=self.user.username, password="testpass123")

    def test_unauthenticated_returns_4xx(self):
        self.client.logout()
        url = reverse("message", kwargs={"id": self.other.id})
        resp = self.client.get(url, HTTP_ACCEPT="text/html")
        self.assertGreaterEqual(resp.status_code, 400)

    def test_nonexistent_user_returns_404(self):
        url = reverse("message", kwargs={"id": 99999})
        resp = self.client.get(url, HTTP_ACCEPT="text/html")
        self.assertEqual(resp.status_code, 404)

    def test_creates_new_conversation_when_none_exists(self):
        self.assertEqual(Conversation.objects.count(), 0)
        url = reverse("message", kwargs={"id": self.other.id})
        self.client.get(url, HTTP_ACCEPT="text/html")
        self.assertEqual(Conversation.objects.count(), 1)

    def test_reuses_existing_conversation(self):
        conv = ConversationFactory()
        ConversationParticipant.objects.create(conversation=conv, user=self.user)
        ConversationParticipant.objects.create(conversation=conv, user=self.other)

        url = reverse("message", kwargs={"id": self.other.id})
        self.client.get(url, HTTP_ACCEPT="text/html")
        self.assertEqual(Conversation.objects.count(), 1)

    def test_both_participants_added_to_new_conversation(self):
        url = reverse("message", kwargs={"id": self.other.id})
        self.client.get(url, HTTP_ACCEPT="text/html")
        conv = Conversation.objects.first()
        participant_users = list(conv.participants.values_list("user_id", flat=True))
        self.assertIn(self.user.id, participant_users)
        self.assertIn(self.other.id, participant_users)

    def test_context_contains_messages(self):
        conv = ConversationFactory()
        ConversationParticipant.objects.create(conversation=conv, user=self.user)
        ConversationParticipant.objects.create(conversation=conv, user=self.other)
        msg = MessageFactory(conversation=conv, sender=self.user)

        url = reverse("message", kwargs={"id": self.other.id})
        resp = self.client.get(url, HTTP_ACCEPT="text/html")
        self.assertIn(msg, resp.context["messages"])

class CallViewGetTest(TestCase):
    def setUp(self):
        self.user = UserFactory()
        self.other = UserFactory()
        self.conv = ConversationFactory()
        ConversationParticipant.objects.create(conversation=self.conv, user=self.user)
        ConversationParticipant.objects.create(conversation=self.conv, user=self.other)
        self.url = reverse("call", kwargs={"id": self.conv.id})

    def test_unauthenticated_redirects_to_login(self):
        resp = self.client.get(self.url)
        self.assertRedirects(resp, reverse("login"), fetch_redirect_response=False)

    def test_get_returns_200_for_participant(self):
        self.client.login(username=self.user.username, password="testpass123")
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, 200)

    def test_context_has_target_user(self):
        self.client.login(username=self.user.username, password="testpass123")
        resp = self.client.get(self.url)
        self.assertEqual(resp.context["target"], self.other)


class CallViewPostTest(TestCase):
    def setUp(self):
        self.user = UserFactory()
        UserProfileFactory(user=self.user)
        self.other = UserFactory()
        self.conv = ConversationFactory()
        ConversationParticipant.objects.create(conversation=self.conv, user=self.user)
        ConversationParticipant.objects.create(conversation=self.conv, user=self.other)
        self.url = reverse("call", kwargs={"id": self.conv.id})

    def _post(self):
        with patch(MOCK_CHANNEL, return_value=MagicMock()):
            with patch(MOCK_ASYNC, return_value=MagicMock()) as mock_a2s:
                resp = self.client.post(self.url)
                return resp, mock_a2s

    def test_unauthenticated_redirects_to_login(self):
        resp = self.client.post(self.url)
        self.assertRedirects(resp, reverse("login"), fetch_redirect_response=False)

    def test_post_redirects_to_call_url(self):
        self.client.login(username=self.user.username, password="testpass123")
        resp, _ = self._post()
        self.assertRedirects(
            resp,
            reverse("call", kwargs={"id": self.conv.id}),
            fetch_redirect_response=False,
        )

    def test_channel_group_send_called(self):
        self.client.login(username=self.user.username, password="testpass123")
        _, mock_a2s = self._post()
        self.assertTrue(mock_a2s.called)

    def test_notification_content_includes_caller_name(self):
        self.client.login(username=self.user.username, password="testpass123")
        caller_name = self.user.userprofile.name
        mock_layer = MagicMock()
        captured = {}

        def fake_a2s(fn):
            def inner(*args, **kwargs):
                captured["args"] = args
            return inner

        with patch(MOCK_CHANNEL, return_value=mock_layer):
            with patch(MOCK_ASYNC, side_effect=fake_a2s):
                self.client.post(self.url)

        payload = captured["args"][1]
        self.assertIn(caller_name, payload["data"]["content"])
