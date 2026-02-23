from rest_framework import mixins, viewsets, status
from rest_framework.response import Response

from rest_framework.viewsets import GenericViewSet

from core.views.response import APIResponseMixin


class BaseAPIView(GenericViewSet, APIResponseMixin):
    """
    BaseAPIView extends APIView and incorporates APIResponseMixin to provide
    a base structure for API views with response functionality.

    This class is designed for creating API views that require consistent
    response handling. It serves as a foundational building block that can
    be extended in other projects or applications.
    """

    pass
