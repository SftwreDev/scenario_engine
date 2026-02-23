from django.db import transaction

from apps.scenarios.models import Scenario
from apps.session.models import Session


from django.conf import settings


@transaction.atomic
def session_create(*, scenario: Scenario, user=None) -> Session:
    """
    Create a new session for the given scenario.

    This function creates and returns a new session record in the database,
    associating it with the provided scenario and an optional user. The operation
    is wrapped in an atomic transaction to ensure database integrity.

    Args:
        scenario (Scenario): The scenario instance associated with the session.
        user (optional): The user to associate with the session. Defaults to None.

    Returns:
        Session: The newly created session instance.
    """
    return Session.objects.create(scenario=scenario, user=user)
