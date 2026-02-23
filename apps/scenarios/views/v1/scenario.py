from django.db.models import QuerySet
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.request import Request
from rest_framework.response import Response

from apps.scenarios import selectors, services
from apps.scenarios.serializers import ScenarioSerializer
from core.views.service_viewset import BaseAPIView


@extend_schema(tags=["Scenarios"])
class ScenarioViewSet(BaseAPIView):
    """
    Handles retrieval and creation of scenarios.

    This class provides endpoints to list all scenarios and create a new
    scenario. It uses the `ScenarioSerializer` for serializing and
    deserializing scenario data, and interacts with the appropriate
    selectors and services for data retrieval and creation.

    Attributes:
        serializer_class: The serializer class used for data validation
            and serialization of scenario data.

    Methods:
        list(request: Request) -> Response:
            Handles the GET request to retrieve a list of scenarios.

        create(request: Request, *args, **kwargs) -> Response:
            Handles the POST request to create a new scenario.
    """

    serializer_class = ScenarioSerializer

    def list(self, request: Request) -> Response:
        """
        Retrieves a list of scenarios and serializes the data for the response.

        Args:
            request (Request): The HTTP request object.

        Returns:
            Response: A response object containing the serialized scenario data
            and a success message.
        """
        queryset: QuerySet = selectors.scenario_list()
        serializer = self.get_serializer(queryset, many=True)

        return self.success_response(
            data=serializer.data,
            message="Scenarios retrieved successfully.",
        )

    def create(self, request: Request) -> Response:
        """
        Handles the creation of a new scenario object based on the request data, performs
        validation using a serializer, and returns a success response with the serialized
        output of the created scenario.

        Args:
            request (Request): The HTTP request object containing the data for creating
                the scenario.
            *args: Additional positional arguments.
            **kwargs: Additional keyword arguments.

        Returns:
            Response: A success response containing the serialized output data of
            the created scenario, a success message, and the HTTP 201 Created status code.
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        scenario = services.scenario_create(
            title=serializer.validated_data["title"],
            description=serializer.validated_data.get("description", ""),
            persona=serializer.validated_data["persona"],
            setting=serializer.validated_data["setting"],
            context=serializer.validated_data["context"],
            conversation_instructions=serializer.validated_data.get(
                "conversation_instructions", ""
            ),
            is_active=serializer.validated_data.get("is_active", True),
        )

        output_serializer = self.serializer_class(scenario)

        return self.success_response(
            data=output_serializer.data,
            message="Scenario created successfully.",
            status_code=status.HTTP_201_CREATED,
        )

    def retrieve(self, request: Request, pk: str = None) -> Response:
        """
        Retrieves a specific scenario by its ID.
        """
        # We can leverage the existing list selector then filter, or simply fetch the object
        from apps.scenarios.models import Scenario
        from django.shortcuts import get_object_or_404

        scenario = get_object_or_404(Scenario, pk=pk)

        serializer = self.get_serializer(scenario)
        return self.success_response(
            data=serializer.data, message="Scenario retrieved successfully."
        )

    def update(self, request: Request, pk: str = None) -> Response:
        """
        Updates an existing scenario completely.
        """
        from apps.scenarios.models import Scenario
        from django.shortcuts import get_object_or_404

        scenario = get_object_or_404(Scenario, pk=pk)

        serializer = self.get_serializer(scenario, data=request.data, partial=False)
        serializer.is_valid(raise_exception=True)

        updated_scenario = services.scenario_update(
            scenario=scenario,
            title=serializer.validated_data.get("title", scenario.title),
            description=serializer.validated_data.get(
                "description", scenario.description
            ),
            persona=serializer.validated_data.get("persona", scenario.persona),
            setting=serializer.validated_data.get("setting", scenario.setting),
            context=serializer.validated_data.get("context", scenario.context),
            conversation_instructions=serializer.validated_data.get(
                "conversation_instructions", scenario.conversation_instructions
            ),
            is_active=serializer.validated_data.get("is_active", scenario.is_active),
        )

        output_serializer = self.get_serializer(updated_scenario)
        return self.success_response(
            data=output_serializer.data, message="Scenario updated successfully."
        )
