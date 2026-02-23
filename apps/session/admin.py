from django.contrib import admin
from apps.session.models import Session, SessionObjectiveProgress


@admin.register(Session)
class SessionAdmin(admin.ModelAdmin):
    list_display = ("id", "scenario", "user", "is_active", "created_at")
    list_filter = ("is_active", "scenario")
    search_fields = ("id",)
    autocomplete_fields = ("scenario", "user")


@admin.register(SessionObjectiveProgress)
class SessionObjectiveProgressAdmin(admin.ModelAdmin):
    list_display = ("session", "objective", "is_met", "created_at")
    list_filter = ("objective", "is_met")
    search_fields = ("session__id", "objective__label")
    autocomplete_fields = ("session", "objective")
