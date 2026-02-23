from django.contrib import admin
from apps.conversations.models import Messages


@admin.register(Messages)
class MessagesAdmin(admin.ModelAdmin):
    list_display = ("session", "sequence_number", "role", "created_at")
    list_filter = ("role",)
    search_fields = ("content",)
    autocomplete_fields = ("session",)
