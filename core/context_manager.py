import logging
from apps.conversations.models import Messages
from core.enums import MessageRolesEnum

logger = logging.getLogger(__name__)


class ContextManager:
    """
    Manages the context of messages for a conversation, particularly for limiting the number
    of messages sent to a language model for processing.

    The class is designed to construct a message history from a conversation, filtering and
    organizing messages such that only exchanges between the user and the assistant are included.
    Its primary purpose is to maintain a manageable context window by truncating the list of
    messages if the total exceeds a specified limit. This is especially useful for systems
    where the context size needs to be controlled due to constraints or performance reasons.
    """

    def __init__(self, max_messages: int = 20):
        self.max_messages = max_messages

    def build_message_history(self, conversation) -> list[dict]:
        """
        Builds and returns a message history for a given conversation consisting of messages
        from the user and assistant. The function applies a context window to truncate the
        message history if it exceeds the specified maximum number of messages.

        Arguments:
            conversation: The conversation whose messages should be fetched
            and processed.

        Returns:
            A list of dictionaries where each dictionary represents a message
            with keys 'role' and 'content'.
        """
        messages = Messages.objects.filter(
            session=conversation,
            role__in=[MessageRolesEnum.USER.value, MessageRolesEnum.ASSISTANT.value],
        ).order_by("created_at")

        # Apply window
        if messages.count() > self.max_messages:
            logger.info(
                "Context window truncated",
                extra={
                    "conversation_id": str(conversation.id),
                    "total_messages": messages.count(),
                    "window": self.max_messages,
                },
            )
            messages = messages[messages.count() - self.max_messages :]

        return [{"role": msg.role, "content": msg.content} for msg in messages]
