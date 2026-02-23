from rest_framework import serializers

from apps.scenarios.models import Scenario, LearningObjective


class ScenarioInputSerializer(serializers.ModelSerializer):
    class Meta:
        model = Scenario
        fields = [
            "title",
            "description",
            "persona",
            "setting",
            "context",
            "conversation_instructions",
            "is_active",
        ]


class LearningObjectiveMinimalSerializer(serializers.ModelSerializer):
    class Meta:
        model = LearningObjective
        fields = [
            "id",
            "label",
            "description",
            "order",
            "is_sequential",
        ]


class ScenarioSerializer(serializers.ModelSerializer):
    learning_objectives = LearningObjectiveMinimalSerializer(many=True, read_only=True)

    class Meta:
        model = Scenario
        fields = [
            "id",
            "title",
            "description",
            "persona",
            "setting",
            "context",
            "conversation_instructions",
            "is_active",
            "learning_objectives",
            "created_at",
            "updated_at",
        ]


class LearningObjectiveInputSerializer(serializers.Serializer):
    """
    Serializer for learning objective creation and updates.
    """

    scenario = serializers.PrimaryKeyRelatedField(
        queryset=Scenario.objects.all(), required=False
    )
    label = serializers.CharField(max_length=100)
    description = serializers.CharField()
    order = serializers.IntegerField(default=0, allow_null=True)
    is_sequential = serializers.BooleanField(default=False)


class LearningObjectiveOutputSerializer(serializers.ModelSerializer):
    scenario = ScenarioSerializer(read_only=True)

    class Meta:
        model = LearningObjective
        fields = [
            "id",
            "scenario",
            "label",
            "description",
            "order",
            "is_sequential",
            "created_at",
            "updated_at",
        ]
