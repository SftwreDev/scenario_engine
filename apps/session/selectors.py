from django.db.models import QuerySet
from django.shortcuts import get_object_or_404

from apps.session.models import Session


def session_list() -> QuerySet[Session]:
    """
    Grabs all the learning sessions from the database.
    We're using select_related here to hook in the scenario data
    right away, which saves us from hitting the dreaded N+1 query problem later.
    """
    return Session.objects.select_related("scenario").all()


def session_get(*, id: int) -> Session:
    """
    Fetches a specific session by its ID. It'll safely throw a 404
    if someone tries to look up a session that doesn't exist.
    """
    return get_object_or_404(Session, id=id)
