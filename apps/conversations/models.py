from django.db import models, transaction
from django.db.models import Max

from apps.session.models import Session
from core.enums import MessageRolesEnum
from core.models import BaseModel


# Create your models here.
class Messages(BaseModel):
    """
    Represents a single message within a conversation session.

    Messages are ordered by `sequence_number` to maintain conversation flow.
    Each message has a role (user, assistant, system, etc.), optional metadata,
    and optional scoring/token usage fields relevant for AI processing and billing.

    Attributes:
        session (ForeignKey): The conversation session this message belongs to.
        role (str): The role of the message sender (choices defined in MessageRolesEnum).
        metadata (JSONField, optional): Optional structured data, typically for AI outputs.
        sequence_number (int): The order of the message within the session.
        content (TextField): The main text content of the message.
        score (float, optional): Optional evaluation or scoring at the message level.
        input_tokens (int, optional): Number of tokens consumed as input by AI.
        output_tokens (int, optional): Number of tokens produced as output by AI.
    """

    session = models.ForeignKey(Session, on_delete=models.PROTECT)
    role = models.CharField(max_length=20, choices=MessageRolesEnum.choices())

    # Optional structured content, e.g., AI-generated JSON outputs
    metadata = models.JSONField(blank=True, null=True)

    # Maintains order of messages within a session
    sequence_number = models.PositiveIntegerField()

    content = models.TextField()

    # Optional message-level scoring
    score = models.FloatField(blank=True, null=True)

    # Token tracking for AI usage/billing
    input_tokens = models.IntegerField(blank=True, null=True)
    output_tokens = models.IntegerField(blank=True, null=True)

    class Meta:
        # Default ordering by sequence to preserve conversation flow
        ordering = ["sequence_number"]

        # Indexes for faster queries on session and role
        indexes = [
            models.Index(fields=["session"]),
            models.Index(fields=["role"]),
        ]

        # Ensure sequence_number is unique per session
        constraints = [
            models.UniqueConstraint(
                fields=["session", "sequence_number"],
                name="unique_sequence_per_session",
            )
        ]

    def save(self, *args, **kwargs):
        """
        Automatically assigns a sequence number if not provided.

        Uses a database transaction and `select_for_update` to safely
        handle concurrent writes and ensure sequence numbers are sequential
        within a session.
        """
        if self.sequence_number is None:
            with transaction.atomic():
                last_sequence = (
                    Messages.objects.select_for_update()
                    .filter(session=self.session)
                    .aggregate(max_seq=Max("sequence_number"))
                )["max_seq"]

                self.sequence_number = (last_sequence or 0) + 1

        super().save(*args, **kwargs)
