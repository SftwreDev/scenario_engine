from django.contrib import admin
from apps.scenarios.models import Scenario, LearningObjective


@admin.register(Scenario)
class ScenarioAdmin(admin.ModelAdmin):
    list_display = ("title", "is_active", "created_at")
    list_filter = ("is_active",)
    search_fields = ("title", "persona", "setting")


@admin.register(LearningObjective)
class LearningObjectiveAdmin(admin.ModelAdmin):
    list_display = ("label", "scenario", "order", "created_at")
    list_filter = ("scenario",)
    search_fields = ("label", "description")
    autocomplete_fields = ("scenario",)
