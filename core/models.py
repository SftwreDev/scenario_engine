import uuid

from django.db import models


class BaseModel(models.Model):
    """
    BaseModel serves as an abstract base class for creating other models.

    This class provides common fields and functionality for maintaining
    identifier and timestamps in child models. It ensures each record has
    a unique identifier (`id`) and tracks creation and update timestamps
    (`created_at`, `updated_at`) automatically. It is not meant to be
    instantiated directly, as it is designed to be inherited by other
    Django models.

    Attributes:
        id: A UUIDField that serves as the primary key for uniquely
            identifying each record.
        created_at: A DateTimeField that stores the timestamp of when
            the record was created. Automatically set on creation.
        updated_at: A DateTimeField that stores the timestamp of when
            the record was last updated. Automatically updated on save.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True
