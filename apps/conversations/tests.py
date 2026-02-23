from unittest.mock import patch
import threading

from django.test import TestCase, TransactionTestCase
from django.urls import reverse
from django.db import IntegrityError
from rest_framework import status
from rest_framework.test import APIClient

from apps.conversations.models import Messages
from apps.conversations.services import send_message
from apps.scenarios.models import Scenario, LearningObjective
from apps.session.models import Session, SessionObjectiveProgress
from core.ai.llm.exceptions import LLMRateLimitError
from core.enums import MessageRolesEnum


class MessagesModelTests(TransactionTestCase):
    def setUp(self):
        self.scenario = Scenario.objects.create(
            title="Test Scenario",
            persona="Test Persona",
            setting="Test Setting",
            context="Test Context",
        )
        self.session = Session.objects.create(scenario=self.scenario)

    def test_sequence_number_auto_assigned(self):
        msg1 = Messages.objects.create(
            session=self.session, role=MessageRolesEnum.USER.value, content="Test 1"
        )
        msg2 = Messages.objects.create(
            session=self.session,
            role=MessageRolesEnum.ASSISTANT.value,
            content="Test 2",
        )

        self.assertEqual(msg1.sequence_number, 1)
        self.assertEqual(msg2.sequence_number, 2)

    def test_sequence_number_provided(self):
        msg = Messages.objects.create(
            session=self.session,
            role=MessageRolesEnum.USER.value,
            content="Test 1",
            sequence_number=10,
        )
        self.assertEqual(msg.sequence_number, 10)


class ConversationsServiceTests(TestCase):
    """
    Unit tests for the Conversations service layer, focusing on
    `send_message` functionality and objective progress updates.
    """

    def setUp(self):
        # Create a test scenario and learning objective
        self.scenario = Scenario.objects.create(
            title="Test Scenario",
            persona="Test Persona",
            setting="Test Setting",
            context="Test Context",
        )
        self.objective1 = LearningObjective.objects.create(
            scenario=self.scenario,
            label="objective_1",
            description="Test Objective 1",
            key="obj-1-key",
        )
        self.session = Session.objects.create(scenario=self.scenario)

    @patch("apps.conversations.services.LLMClient")
    def test_send_message_updates_objectives(self, mock_llm_client_class):
        """
        Verifies that sending a message:
        - Creates user and assistant messages
        - Updates learning objectives according to LLM tool data
        """
        # Mock the LLM client to return predefined tool data
        mock_client = mock_llm_client_class.return_value
        mock_client.complete.return_value = {
            "content": "",
            "tool_data": {
                "conversational_response": "Hello, I am the test persona.",
                "obj-1-key": {
                    "is_met": True,
                    "justification": "User asked good questions.",
                },
            },
            "usage": {"prompt_tokens": 10, "completion_tokens": 20},
            "model": "test-model",
        }

        # Act: send a message
        result = send_message(session=self.session, content="Hi Dave")

        # Assert user message
        user_msg = result["user_message"]
        self.assertEqual(user_msg.role, MessageRolesEnum.USER.value)
        self.assertEqual(user_msg.content, "Hi Dave")

        # Assert assistant message
        assistant_msg = result["assistant_message"]
        self.assertEqual(assistant_msg.role, MessageRolesEnum.ASSISTANT.value)
        self.assertEqual(assistant_msg.content, "Hello, I am the test persona.")

        # Assert objective progress
        progress = SessionObjectiveProgress.objects.get(
            session=self.session, objective=self.objective1
        )
        self.assertTrue(progress.is_met)
        self.assertEqual(progress.justification, "User asked good questions.")

    @patch("apps.conversations.services.LLMClient")
    def test_context_windowing(self, mock_llm_client_class):
        """
        Tests that long conversations correctly trigger summary-based
        context windowing, reducing the number of messages sent to the LLM.
        """
        # Create 15 previous messages (alternating user/assistant)
        for i in range(15):
            Messages.objects.create(
                session=self.session,
                role=(
                    MessageRolesEnum.USER.value
                    if i % 2 == 0
                    else MessageRolesEnum.ASSISTANT.value
                ),
                content=f"Old Message {i}",
            )

        # Mock LLM response
        mock_client = mock_llm_client_class.return_value
        mock_client.complete.return_value = {
            "content": "Test response",
            "usage": {"prompt_tokens": 10, "completion_tokens": 20},
            "model": "test-model",
        }

        # Act: send the latest message
        send_message(session=self.session, content="Latest message")

        # Expect two calls: one for summary generation, one for main turn
        self.assertEqual(mock_client.complete.call_count, 2)

        # Check the messages sent in the main call
        call_kwargs = mock_client.complete.call_args.kwargs
        messages_sent = call_kwargs["messages"]

        # Should include summary user msg, assistant acknowledgment, latest user message
        self.assertEqual(len(messages_sent), 3)
        self.assertEqual(messages_sent[-1]["content"], "Latest message")
        self.assertTrue(
            messages_sent[0]["content"].startswith(
                "[Summary of the conversation so far]:"
            )
        )


class ConversationsAPITests(TestCase):
    """
    Integration tests for the Conversations API endpoints.
    """

    def setUp(self):
        self.client = APIClient()
        self.scenario = Scenario.objects.create(
            title="Test Scenario",
            persona="Test Persona",
            setting="Test Setting",
            context="Test Context",
        )
        self.session = Session.objects.create(scenario=self.scenario)

    @patch("apps.conversations.views.v1.conversations.send_message")
    def test_create_conversation_turn(self, mock_send_message):
        """
        Tests POST /api/v1/conversations/ to create a new conversation turn.
        """
        # Mock the service layer response
        user_msg = Messages.objects.create(
            session=self.session, role=MessageRolesEnum.USER.value, content="Test"
        )
        assist_msg = Messages.objects.create(
            session=self.session, role=MessageRolesEnum.ASSISTANT.value, content="Reply"
        )

        mock_send_message.return_value = {
            "user_message": user_msg,
            "assistant_message": assist_msg,
        }

        url = "/api/v1/conversations/"
        data = {"session": self.session.id, "content": "Test"}

        response = self.client.post(url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["assistant_message"]["content"], "Reply")

    @patch("apps.conversations.views.v1.conversations.send_message")
    def test_rate_limit_error_handling(self, mock_send_message):
        """
        Ensures the API correctly returns 503 when the LLM service is rate-limited.
        """
        mock_send_message.side_effect = LLMRateLimitError("Rate limit exceeded")

        url = "/api/v1/conversations/"
        data = {"session": self.session.id, "content": "Test"}

        response = self.client.post(url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_503_SERVICE_UNAVAILABLE)
        self.assertEqual(
            response.data["detail"],
            "The AI provider is currently rate limited. Please try again soon.",
        )
