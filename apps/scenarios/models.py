import uuid

from django.db import models
from django.utils.text import slugify

from core.enums import StatusEnums
from core.models import BaseModel


class Scenario(BaseModel):
    """
    A reusable scenario template. One scenario can power many concurrent
    conversations (each conversation is a separate learner session).
    """

    # Human-facing metadata
    title = models.CharField(max_length=200)
    description = models.TextField(
        blank=True,
        help_text="Internal description for scenario authors. Not shown to learners.",
    )

    # -------------------------------------------------------------------
    # The "DNA" of the scenario — everything the LLM needs to play its role
    # -------------------------------------------------------------------

    persona = models.TextField(
        help_text=(
            "Describe the character the LLM will play. Include name, personality traits, "
            "knowledge level, emotional tendencies, and speech patterns. "
            "E.g. 'You are Dave, a 55-year-old cattle farmer from rural NSW. You speak in "
            "plain language, get anxious when the vet seems unsure, and occasionally go off "
            "on tangents about your other cattle or the weather.'"
        )
    )

    setting = models.TextField(
        help_text=(
            "Describe the physical and situational context. Where are we? What's happening? "
            "E.g. 'A remote property outside Armidale, NSW. It's a cool autumn morning. "
            "Dave called the university vet clinic because his prize Hereford isn't right.'"
        )
    )

    context = models.TextField(
        help_text=(
            "The background knowledge the LLM character possesses — facts they know, "
            "the current state of the scenario, and any information that should drive "
            "the conversation. This is distinct from persona (who they are) and setting "
            "(where we are). E.g. symptom details, recent events, hidden information "
            "the learner needs to uncover."
        )
    )

    # How the LLM should handle the conversation mechanics
    conversation_instructions = models.TextField(
        blank=True,
        help_text=(
            "Optional additional instructions for how the LLM should conduct the conversation. "
            "E.g. guidance on how forthcoming to be, whether to volunteer information or "
            "wait to be asked, emotional escalation triggers, etc."
        ),
    )

    # Whether this scenario is available for new sessions
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name_plural = "scenarios"
        verbose_name = "scenario"
        db_table = "scenarios"

    def __str__(self):
        return self.title


class LearningObjective(BaseModel):
    """
    An individual learning objective within a scenario.

    Keeping this as a proper model (rather than a JSON field on Scenario) lets us:
    - Reference objectives by ID in conversation progress tracking
    - Filter/query objectives independently
    - Give each objective its own evaluation description
    - Order them explicitly
    """

    scenario = models.ForeignKey(
        Scenario,
        on_delete=models.CASCADE,
        related_name="learning_objectives",
    )

    # Short label used when referencing this objective in LLM prompts and API responses.
    # Keeping it short helps with the token budget.
    label = models.CharField(
        max_length=100,
        help_text="Short identifier. E.g. 'gather_history', 'identify_differentials'",
    )

    key = models.SlugField(max_length=100)

    description = models.TextField(
        help_text="Full description of what the learner needs to demonstrate."
    )

    # Controls display order in prompts and API responses
    order = models.PositiveIntegerField(null=True, blank=True)
    is_sequential = models.BooleanField(default=False)

    class Meta:
        ordering = ["order", "label"]
        unique_together = [("scenario", "label")]
        verbose_name_plural = "learning objectives"
        verbose_name = "learning objective"
        db_table = "learning_objectives"
        constraints = [
            models.UniqueConstraint(
                fields=["scenario", "key"],
                name="unique_objective_key_per_scenario",
            )
        ]

    def __str__(self):
        return f"{self.scenario.title} — {self.label}"

    def save(self, *args, **kwargs):
        if not self.key:
            base_slug = slugify(self.label)
            # Appending a short UUID avoids race conditions where two concurrent saves compute the same count
            short_uuid = uuid.uuid4().hex[:6]
            self.key = f"{base_slug}-{short_uuid}"
        super().save(*args, **kwargs)
