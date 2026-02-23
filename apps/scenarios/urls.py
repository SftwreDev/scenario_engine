from rest_framework.routers import DefaultRouter

from apps.scenarios.views.v1.learning_objectives import LearningObjectivesViewSet
from apps.scenarios.views.v1.scenario import ScenarioViewSet

router = DefaultRouter()
router.register(r"scenarios", ScenarioViewSet, basename="scenario")
router.register(
    r"learning-objectives", LearningObjectivesViewSet, basename="learning-objective"
)

urlpatterns = router.urls
