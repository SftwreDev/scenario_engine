from typing import Type

from django.db.models import QuerySet
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.request import Request
from rest_framework.response import Response

from apps.session import selectors, services
from apps.session.models import Session
from apps.session.serializers import SessionOutputSerializer, SessionInputSerializer
from core.views.service_viewset import BaseAPIView


@extend_schema(tags=["Sessions"])
class SessionViewSet(
    BaseAPIView,
):
    """
    Set of views for handling session-related operations.

    This class provides endpoints for interacting with session resources. It enables
    listing all active sessions and creating new sessions. Primarily intended for use
    in administrative purposes or features requiring session management.
    """

    serializer_class = SessionOutputSerializer
    input_serializer_class: Type[SessionInputSerializer] = SessionInputSerializer

    def list(self, request: Request) -> Response:
        """
        Handles the retrieval and serialization of session data and returns a successful
        response containing the serialized data.

        Parameters:
        request (Request): The HTTP request instance.

        Returns:
        Response: An HTTP response with serialized session data and a success message.
        """
        queryset: QuerySet[Session] = selectors.session_list()
        serializer = self.get_serializer(queryset, many=True)

        return self.success_response(
            data=serializer.data, message="Sessions retrieved successfully."
        )

    @extend_schema(
        request=SessionInputSerializer,
        responses=SessionOutputSerializer,
    )
    def create(self, request: Request) -> Response:
        """
        Handles the creation of a new session based on the provided scenario and
        authenticates the user if available. This function processes the input
        data, validates it, and uses a service to create a session object.
        The output serializer subsequently formats the created session object,
        and a success response is returned with appropriate details.

        Arguments:
            request (Request): The HTTP request object containing data to create
                a new session. This request also determines user authentication status.

        Raises:
            serializers.ValidationError: Raised if the provided input data is
                invalid or does not pass validation.

        Returns:
            Response: An HTTP response object containing details of the newly
                created session, along with success message and status code.
        """
        serializer = self.input_serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)

        session = services.session_create(
            scenario=serializer.validated_data["scenario"],
            user=request.user if request.user.is_authenticated else None,
        )

        output_serializer = self.get_serializer(session)

        return self.success_response(
            data=output_serializer.data,
            message="Session created successfully.",
            status_code=status.HTTP_201_CREATED,
        )
