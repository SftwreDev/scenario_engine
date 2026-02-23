from rest_framework import serializers

from apps.scenarios.models import Scenario
from apps.scenarios.serializers import ScenarioSerializer
from apps.session.models import Session


class SessionInputSerializer(serializers.Serializer):
    """
    Handles the incoming data when a user wants to start a new session.
    Right now, we simply need to know which scenario they're trying to play.
    """

    scenario = serializers.PrimaryKeyRelatedField(
        queryset=Scenario.objects.all(), required=True
    )


class SessionOutputSerializer(serializers.ModelSerializer):
    """
    Formats the session data we send back out to the frontend.
    We nest the full scenario details inside so the client doesn't
    have to make a second round trip to get them.
    """

    scenario = ScenarioSerializer(read_only=True)

    class Meta:
        model = Session
        fields = ["id", "scenario", "is_active", "created_at", "updated_at"]
