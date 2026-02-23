from django.db.models import QuerySet
from django.shortcuts import get_object_or_404

from apps.scenarios.models import Scenario, LearningObjective


def scenario_list() -> QuerySet[Scenario]:
    """Retrieve all scenarios. Prefetch learning objectives to avoid N+1 queries."""
    return Scenario.objects.prefetch_related("learning_objectives").all()


def scenario_get(*, id: int) -> Scenario:
    """Retrieve a scenario by ID."""
    return get_object_or_404(Scenario, id=id)


def learning_objective_list() -> QuerySet[LearningObjective]:
    """Retrieve all learning objectives."""
    return LearningObjective.objects.all()
