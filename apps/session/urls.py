"""
Routing configuration for the session app.
We use a DefaultRouter here to automatically generate the RESTful
URL patterns for our SessionViewSet (like /session/ and /session/<id>/).
"""

from rest_framework.routers import DefaultRouter

from apps.session.views.v1.session import SessionViewSet

router = DefaultRouter()
router.register(r"session", SessionViewSet, basename="session")
urlpatterns = router.urls
