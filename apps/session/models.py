"""Session and progress tracking models.

Stores per-learner session state and objective progress updated during
conversations.
"""

from django.conf import settings
from django.db import models

from apps.scenarios.models import Scenario, LearningObjective
from core.models import BaseModel


# Create your models here.
class Session(BaseModel):
    """
    Represents an active learning session for a specific scenario.

    This ties a user to a scenario and keeps track of the conversation's context.
    We cache summarized messages here to keep the LLM context window manageable
    while still giving it enough history to make the conversation feel natural.
    """

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="sessions",
        null=True,
        blank=True,
        help_text="The learner/user who is participating in this session.",
    )
    scenario = models.ForeignKey(
        Scenario, on_delete=models.PROTECT, related_name="scenario_sessions"
    )
    is_active = models.BooleanField(default=True)

    # Context management fields
    context_summary = models.TextField(
        blank=True,
        help_text="Cached summary of messages before the summarisation threshold.",
    )
    summarised_up_to_sequence = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="The sequence_number of the last message included in context_summary.",
    )

    class Meta:
        ordering = ["-created_at"]
        verbose_name_plural = "sessions"
        verbose_name = "session"
        db_table = "sessions"

    def __str__(self):
        return self.scenario.title


class SessionObjectiveProgress(BaseModel):
    """
    Tracks how well a user is doing against a specific learning objective
    in their current session.

    The LLM updates these records as the conversation unfolds, letting us
    know if the user hit the goal and why, which is great for building out
    post-session feedback.
    """

    session = models.ForeignKey(
        Session, on_delete=models.CASCADE, related_name="objective_progress"
    )
    objective = models.ForeignKey(
        LearningObjective, on_delete=models.CASCADE, related_name="session_progress"
    )
    is_met = models.BooleanField(default=False)
    justification = models.TextField(
        blank=True,
        help_text="The LLM's explanation for why this objective was considered met (or not).",
    )

    class Meta:
        ordering = ["created_at"]
        verbose_name_plural = "session objective progress"
        verbose_name = "session objective progress"
        db_table = "session_objective_progress"
        constraints = [
            models.UniqueConstraint(
                fields=["session", "objective"], name="unique_objective_per_session"
            )
        ]

    def __str__(self):
        return f"Session {self.session_id} - {self.objective.label}: {'Met' if self.is_met else 'Not Met'}"
