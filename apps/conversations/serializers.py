from rest_framework import serializers

from apps.session.models import Session


class SendMessageSerializer(serializers.Serializer):
    """
    Serializer for sending a new message within a session.

    Validates the session and the message content provided by the user.
    """

    session = serializers.PrimaryKeyRelatedField(
        queryset=Session.objects.all(),
        required=True,
        help_text="The session ID this message belongs to.",
    )
    content = serializers.CharField(
        help_text="The text content of the message to be sent."
    )


class MessageOutputSerializer(serializers.Serializer):
    """
    Serializer for representing a message in responses.

    Includes basic information about the message such as its ID, role,
    content, sequence order, and timestamp.
    """

    id = serializers.UUIDField()
    role = serializers.CharField()
    content = serializers.CharField()
    sequence_number = serializers.IntegerField()
    created_at = serializers.DateTimeField()


class SessionObjectiveProgressSerializer(serializers.Serializer):
    """
    Serializer for tracking the progress of objectives within a session.

    Maps to the related objective and provides its key, label, whether it
    has been met, and any justification or explanation.
    """

    objective_key = serializers.CharField(source="objective.key")
    label = serializers.CharField(source="objective.label")
    is_met = serializers.BooleanField()
    justification = serializers.CharField()


class SendMessageResponseSerializer(serializers.Serializer):
    """
    Serializer for the response after sending a message.

    Returns both the user and assistant messages, as well as the current
    progress of session objectives.
    """

    user_message = MessageOutputSerializer()
    assistant_message = MessageOutputSerializer()
    objective_progress = SessionObjectiveProgressSerializer(many=True)
