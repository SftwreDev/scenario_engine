from django.urls import path
from apps.conversations.views.v1.conversations import ConversationsViewSet

urlpatterns = [
    path(
        "v1/conversations/",
        ConversationsViewSet.as_view({"post": "create"}),
        name="conversations-list",
    ),
    path(
        "v1/conversations/stream/",
        ConversationsViewSet.as_view({"post": "stream"}),
        name="conversations-stream",
    ),
]

"""
URL Configuration for Conversations API.

Endpoints:
    POST /v1/conversations/ 
        - Calls ConversationsViewSet.create
        - Used to send a new message in a session
        - Returns the user message, assistant response, and updated objective progress
"""
