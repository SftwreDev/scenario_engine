from typing import Dict

from rest_framework.response import Response
from rest_framework import status


class APIResponseMixin:
    """
    Mix-in class providing standardized API response structure.

    This class is designed to be used as a mix-in to provide utility methods
    for generating consistent success and failure responses in API endpoints.
    It includes predefined structures for responses, supported by success and
    failure statuses, ensuring uniformity in API communication.

    Attributes:
        SUCCESS (str): The status value representing a successful response.
        FAILURE (str): The status value representing a failure response.
    """

    SUCCESS: str = "success"
    FAILURE: str = "failure"

    @classmethod
    def success_response(
        cls, data=None, message=None, status_code=status.HTTP_200_OK
    ) -> Response:
        """
        Generates a standardized success response for API endpoints.

        This method constructs a response with a predefined structure that
        includes status code, status message, optional message, and optional
        data. It ensures consistency in API responses across the application.

        Args:
            data (Optional[Any]): Optional payload or data to include in the response.
            message (Optional[str]): Optional descriptive message for the response.
            status_code (int): HTTP status code to be included in the response.
                               Defaults to status.HTTP_200_OK.

        Returns:
            Response: A Response object containing the structured success response.
        """
        response_data: Dict[str, any] = {
            "status_code": status_code,
            "status": cls.SUCCESS,
        }
        if message is not None:
            response_data["message"] = message
        if data is not None:
            response_data["data"] = data
        return Response(response_data, status=status_code)

    @classmethod
    def failure_response(
        cls, data=None, message=None, status_code=status.HTTP_400_BAD_REQUEST
    ) -> Response:
        """
        Generate a failure response with a standardized structure.

        This method constructs a failure response containing a status code, status,
        message, and optionally data. It is returned as a Django REST framework
        Response object. The default status code is set to 400 (BAD REQUEST).

        Parameters:
            data (Optional[any]): Optional additional data to include in the response.
            message (Optional[str]): Optional message to include in the response.
            status_code (int): HTTP status code for the response, defaults to 400
                (BAD REQUEST).

        Returns:
            Response: A Response object containing the failure response data.
        """
        response_data: Dict[str, any] = {
            "status_code": status_code,
            "status": cls.FAILURE,
        }
        if message is not None:
            response_data["message"] = message
        if data is not None:
            response_data["data"] = data
        return Response(response_data, status=status_code)
