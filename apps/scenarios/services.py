"""Service-layer helpers for scenarios and objectives.

Provide create/update functions with basic validation and transaction safety.
"""

import uuid
from typing import Optional

from django.db import transaction, IntegrityError
from django.utils.text import slugify
from rest_framework.exceptions import ValidationError

from apps.scenarios.models import Scenario, LearningObjective


@transaction.atomic
def scenario_create(
    *,
    title: str,
    description: str = "",
    persona: str,
    setting: str,
    context: str,
    conversation_instructions: str = "",
    is_active: bool = True,
) -> Scenario:
    """Create a new scenario."""
    scenario = Scenario.objects.create(
        title=title,
        description=description,
        persona=persona,
        setting=setting,
        context=context,
        conversation_instructions=conversation_instructions,
        is_active=is_active,
    )
    return scenario


@transaction.atomic
def scenario_update(*, scenario: Scenario, **kwargs) -> Scenario:
    """Update an existing scenario."""
    non_side_effect_fields = [
        "title",
        "description",
        "persona",
        "setting",
        "context",
        "conversation_instructions",
        "is_active",
    ]

    for field in non_side_effect_fields:
        if field in kwargs:
            setattr(scenario, field, kwargs[field])

    scenario.save(
        update_fields=[f for f in non_side_effect_fields if f in kwargs]
        + ["updated_at"]
    )
    return scenario


@transaction.atomic
def learning_objective_create(
    *,
    scenario: Scenario,
    label: str,
    description: str,
    order: Optional[int] = None,
    is_sequential: Optional[bool] = False,
) -> LearningObjective:
    """Create a new learning objective. Extra args like evaluation_guide are accepted for backward compatibility."""

    existing_los = LearningObjective.objects.filter(scenario=scenario).order_by(
        "created_at"
    )

    first_lo = existing_los.first()

    if first_lo and not first_lo.is_sequential and is_sequential:
        raise ValidationError(
            {
                "is_sequential": [
                    "This scenario is non-sequential. "
                    "Sequential learning objectives are not allowed."
                ],
                "code": "non_sequential_scenario_violation",
            }
        )

    return LearningObjective.objects.create(
        scenario=scenario,
        label=label,
        description=description,
        order=order,
        is_sequential=is_sequential,
    )


@transaction.atomic
def learning_objective_update(
    *, objective: LearningObjective, **kwargs
) -> LearningObjective:
    """Update an existing learning objective."""
    updatable_fields = [
        "label",
        "description",
        "order",
        "is_sequential",
        "is_met",
    ]

    for field in updatable_fields:
        if field in kwargs:
            setattr(objective, field, kwargs[field])

    objective.save(
        update_fields=[f for f in updatable_fields if f in kwargs] + ["updated_at"]
    )
    return objective
