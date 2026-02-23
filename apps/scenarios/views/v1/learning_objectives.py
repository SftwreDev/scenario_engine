from typing import Type

from django.db.models import QuerySet
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.request import Request
from rest_framework.response import Response

from apps.scenarios import selectors, services
from apps.scenarios.models import LearningObjective
from apps.scenarios.serializers import (
    LearningObjectiveOutputSerializer,
    LearningObjectiveInputSerializer,
)
from core.views.service_viewset import BaseAPIView


@extend_schema(tags=["Learning Objectives"])
class LearningObjectivesViewSet(BaseAPIView):
    """
    View set for managing learning objectives.

    This class provides functionality to retrieve a list of learning objectives or create
    a new learning objective. It extends BaseAPIView and leverages serializers to validate
    input and format output data.

    Attributes:
        serializer_class: The serializer used for output serialization.
        input_serializer_class: The serializer class used for validating input data and
            providing the necessary structure for creation.
    """

    serializer_class = LearningObjectiveOutputSerializer
    input_serializer_class: Type[LearningObjectiveInputSerializer] = (
        LearningObjectiveInputSerializer
    )

    def list(self, request: Request) -> Response:
        """
        Handles the retrieval of a list of learning objectives.

        Fetches a list of learning objectives using the provided selector function,
        serializes the data, and returns a structured success response.

        Parameters:
            request (Request): The HTTP request object.

        Returns:
            Response: A response object containing serialized learning objectives data
            and a success message.
        """
        queryset: QuerySet[LearningObjective] = selectors.learning_objective_list()
        serializer = self.get_serializer(queryset, many=True)

        return self.success_response(
            data=serializer.data,
            message="Learning objectives retrieved successfully.",
        )

    @extend_schema(
        request=LearningObjectiveInputSerializer,
        responses=LearningObjectiveOutputSerializer,
    )
    def create(self, request: Request) -> Response:
        """
        Creates a new learning objective.

        This method processes the HTTP request, validates input data, and creates a new
        learning objective using the provided parameters. Upon successful creation,
        it returns a response with the created learning objective data.

        Parameters:
            request (Request): The HTTP request containing data for the creation
                of a learning objective.

        Returns:
            Response: The HTTP response containing the serialized data of the newly
                created learning objective, along with a success message and a status
                code of HTTP 201 Created.

        Raises:
            ValidationError: If the input data fails validation.
            Exception: Any other exceptions that may occur during the processing
                or creation of the learning objective.
        """
        input_serializer = self.input_serializer_class(data=request.data)
        input_serializer.is_valid(raise_exception=True)

        learning_objective = services.learning_objective_create(
            scenario=input_serializer.validated_data.get("scenario"),
            label=input_serializer.validated_data["label"],
            description=input_serializer.validated_data["description"],
            order=input_serializer.validated_data.get("order"),
            is_sequential=input_serializer.validated_data.get("is_sequential", False),
        )

        output_serializer = self.get_serializer(learning_objective)

        return self.success_response(
            data=output_serializer.data,
            message="Learning objective created successfully.",
            status_code=status.HTTP_201_CREATED,
        )
