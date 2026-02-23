"""Views for conversation endpoints.

Provides endpoints to create conversation turns and to stream assistant output
using Server-Sent Events (SSE).
"""

import json
import time

from django.db.models import QuerySet
from django.http import StreamingHttpResponse
from django.utils.encoding import smart_str
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.exceptions import APIException
from rest_framework.request import Request
from rest_framework.response import Response

from apps.conversations.serializers import (
    SendMessageSerializer,
    SendMessageResponseSerializer,
)
from apps.conversations.services import (
    send_message,
    stream_message,
)
from apps.session.models import SessionObjectiveProgress, Session
from core.ai.llm.exceptions import LLMError, LLMRateLimitError, LLMTimeoutError
from core.views.service_viewset import BaseAPIView


class ServiceUnavailable(APIException):
    """
    Exception class representing a service unavailability error.

    The ServiceUnavailable exception indicates that a requested service is
    temporarily unavailable, typically due to server overloading or maintenance.
    This exception is used to inform the client to retry later as the issue is
    expected to be temporary.
    """

    status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    default_detail = "Service temporarily unavailable, try again later."
    default_code = "service_unavailable"


# Helper to format Server-Sent Events lines
def _sse_event(data: dict | str) -> str:
    """Format a Server-Sent Events (SSE) data line.

    Accepts a dict (which is JSON-encoded) or a prebuilt string payload and
    returns a properly terminated SSE data line.
    """
    payload = data if isinstance(data, str) else json.dumps(data)
    return f"data: {smart_str(payload)}\n\n"


@extend_schema(tags=["Conversations"])
class ConversationsViewSet(BaseAPIView):
    """
    API endpoint for handling conversation messages within a session.

    This viewset is responsible for accepting user messages, passing them to
    the AI service, and returning both the user and assistant responses along
    with the current objective progress for the session.
    """

    # Serializer used to validate incoming message payloads
    input_serializer_class = SendMessageSerializer

    @extend_schema(
        request=SendMessageSerializer,
        responses={201: SendMessageResponseSerializer},
    )
    def create(self, request: Request) -> Response:
        """
        Create a new conversation message and process it through the AI service.

        The request payload is validated, the message is sent to the AI engine,
        and the resulting assistant response is returned together with the
        user's message and updated session objective progress.

        Args:
            request (Request): Incoming request containing the session and message content.

        Raises:
            ServiceUnavailable: If the AI service is rate-limited, times out,
            or encounters a communication error.

        Returns:
            Response: Serialized user message, assistant message, and objective progress.
        """
        serializer: SendMessageSerializer = self.input_serializer_class(
            data=request.data
        )
        serializer.is_valid(raise_exception=True)

        session: Session = serializer.validated_data["session"]
        content: str = serializer.validated_data["content"]

        try:
            # Send the message to the AI service and retrieve both messages
            result: dict = send_message(session=session, content=content)

        except LLMRateLimitError:
            # Provider is throttling requests
            raise ServiceUnavailable(
                detail="The AI provider is currently rate limited. Please try again soon."
            )

        except LLMTimeoutError:
            # Provider did not respond within the allowed time
            raise ServiceUnavailable(detail="The AI provider took too long to respond.")

        except LLMError as e:
            # Catch-all for unexpected AI communication issues
            raise ServiceUnavailable(
                detail=f"An error occurred communicating with the AI: {str(e)}"
            )

        # Retrieve the latest objective progress for the current session
        progress: QuerySet[SessionObjectiveProgress] = (
            SessionObjectiveProgress.objects.filter(session=session).select_related(
                "objective"
            )
        )

        response_data: dict = {
            "user_message": result["user_message"],
            "assistant_message": result["assistant_message"],
            "objective_progress": progress,
        }

        output_serializer: SendMessageResponseSerializer = (
            SendMessageResponseSerializer(response_data)
        )

        return Response(output_serializer.data, status=status.HTTP_201_CREATED)

    @extend_schema(
        request=SendMessageSerializer,
        responses=None,  # streaming response
        description="Streams assistant content in 10-word chunks using the same orchestration as create().",
    )
    @action(detail=False, methods=["post"], url_path="v1/conversations/stream")
    def stream(self, request: Request) -> StreamingHttpResponse:
        """Stream assistant output for a new user message via SSE.

        Validates the payload, then yields 10-word chunks of assistant text as
        they arrive from the provider. Each chunk is sent as an SSE data line.
        """
        serializer: SendMessageSerializer = self.input_serializer_class(
            data=request.data
        )
        serializer.is_valid(raise_exception=True)

        session: Session = serializer.validated_data["session"]
        content: str = serializer.validated_data["content"]

        def sse_lines():
            for chunk in stream_message(
                session=session, content=content, chunk_size=10
            ):
                yield _sse_event(chunk)

        response = StreamingHttpResponse(sse_lines(), content_type="text/event-stream")
        response["Cache-Control"] = "no-cache"
        response["X-Accel-Buffering"] = "no"
        return response
