"""Conversation orchestration services.

This module coordinates message persistence, context summarisation, and LLM
calls for both standard and streaming interactions. Docstrings follow PEP 257
and aim for a clear, neutral tone.
"""

import json
import logging
import time
from django.db import transaction
from django.db.models import Max, QuerySet

from core.ai.llm.client import LLMClient
from core.enums import MessageRolesEnum
from apps.conversations.models import Messages
from apps.scenarios.models import Scenario, LearningObjective
from apps.session.models import Session, SessionObjectiveProgress

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Thresholds for conversation summarisation
# ---------------------------------------------------------------------------

# Below this number of messages, send the full conversation verbatim; no summary needed
SUMMARY_THRESHOLD = 6

# Once a summary exists, re-summarise after this many new messages have been added
SUMMARY_INTERVAL = 10


# ---------------------------------------------------------------------------
# Prompts
# ---------------------------------------------------------------------------


def summarize_messages_prompt() -> str:
    """
    Returns the system prompt for summarising a conversation history.

    Instructs the AI to produce a concise but comprehensive summary suitable
    for context in continuing the scenario.
    """
    return """
    You are an AI assistant tasked with summarizing a learning scenario conversation.

    You will be given a list of message objects. Each has:
    - "role": "user" or "assistant"  
    - "content": the message text

    Your task:
    Produce a concise but comprehensive summary that another AI can use as context
    to continue the conversation accurately.

    Focus on:
    - What clinical information or history the learner has gathered so far
    - Which learning objectives appear to have been addressed
    - The current state of the scenario (what has happened, what is unresolved)
    - Key facts established (symptoms, timeline, environment, etc.)
    - The emotional tone and dynamic between the characters

    Rules:
    - Do NOT continue the conversation
    - Do NOT roleplay
    - Do NOT repeat large portions verbatim
    - Do NOT return JSON
    - Return only a clean plain-text summary paragraph
    """.strip()


def build_system_prompt(session: Session) -> str:
    """
    Constructs the LLM system prompt for a scenario.

    Includes persona, setting, context, instructions, and an explicit
    mandate to evaluate learner progress each turn.
    """
    scenario: Scenario = session.scenario
    prompt_parts: list[str] = [
        f"You are playing a role in a learning scenario. Your persona is:\n{scenario.persona}\n",
        f"The setting is:\n{scenario.setting}\n",
        f"Additional context you know:\n{scenario.context}\n",
    ]
    if scenario.conversation_instructions:
        prompt_parts.append(
            f"Conversation instructions:\n{scenario.conversation_instructions}\n"
        )
    prompt_parts.append(
        "Evaluate the learner's progress against the learning objectives using the provided tool. "
        "You MUST call the `evaluate_learner_progress` tool on every turn before you respond to the user "
        "to update the current scenario state."
    )
    return "\n".join(prompt_parts)


def build_tools(session: Session) -> tuple[list[dict] | None, dict | None]:
    """
    Builds the tool definitions for LLM evaluation of learner objectives.

    Returns:
        - tools: list of tool schemas
        - tool_choice: dict specifying the tool to invoke
    """
    objectives: QuerySet[LearningObjective] = session.scenario.learning_objectives.all()
    if not objectives:
        return None, None

    properties: dict[str, dict[str, str] | list[str]] = {
        "conversational_response": {
            "type": "string",
            "description": "Your in-character verbal response to the learner. Required.",
        }
    }
    required = ["conversational_response"]

    for obj in objectives:
        properties[obj.key]: dict[str, str] = {
            "type": "object",
            "properties": {
                "is_met": {
                    "type": "boolean",
                    "description": (
                        f"Whether the objective '{obj.label}' has been met. "
                        f"Description: {obj.description}"
                    ),
                },
                "justification": {
                    "type": "string",
                    "description": (
                        "Brief explanation of why this objective is or is not met, "
                        "based on the full conversation so far."
                    ),
                },
            },
            "required": ["is_met", "justification"],
        }
        required.append(obj.key)

    tools: list[dict] = [
        {
            "name": "evaluate_learner_progress",
            "description": (
                "Update the scenario state by evaluating which learning objectives "
                "the learner has met so far across the entire conversation."
            ),
            "input_schema": {
                "type": "object",
                "properties": properties,
                "required": required,
            },
        }
    ]
    tool_choice: dict[str, str] = {"type": "tool", "name": "evaluate_learner_progress"}
    return tools, tool_choice


# ---------------------------------------------------------------------------
# Context management
# ---------------------------------------------------------------------------


def _should_resummarise(session: Session, new_messages_since_summary: int) -> bool:
    """
    Determines whether a summary should be refreshed.

    Returns True if a summary exists and enough new messages have arrived
    since the last summarisation.
    """
    return (
        bool(session.context_summary) and new_messages_since_summary >= SUMMARY_INTERVAL
    )


def _generate_summary(messages: list[Messages]) -> str:
    """
    Generates a plain-text summary of the given messages by calling the LLM.

    This is isolated for easy testing/mocking.
    """
    summary_data: list[dict] = [
        {"role": msg.role, "content": msg.content} for msg in messages
    ]
    client = LLMClient()
    response = client.complete(
        system_prompt=summarize_messages_prompt(),
        messages=[
            {
                "role": "user",
                "content": (
                    f"Here is the conversation history:\n\n"
                    f"{json.dumps(summary_data, indent=2)}"
                ),
            }
        ],
    )
    return response["content"]


def _maybe_refresh_summary(session: Session, all_history: list[Messages]) -> None:
    """
    Checks whether the session summary needs updating and refreshes it if necessary.

    Updates `session.context_summary` and `session.summarised_up_to_sequence` in place.
    """
    # Messages available to summarise = everything except the current user message
    summarisable: list = all_history[:-1]

    if not summarisable:
        return

    total: int = len(summarisable)

    if not session.context_summary and total < SUMMARY_THRESHOLD:
        # Short conversation — no summary needed yet
        return

    if session.context_summary:
        # Count new messages since last summary
        new_count: int = sum(
            1
            for m in summarisable
            if m.sequence_number > (session.summarised_up_to_sequence or 0)
        )
        if not _should_resummarise(session, new_count):
            return
        # Re-summarise combining previous summary + new messages
        messages_since: list = [
            m
            for m in summarisable
            if m.sequence_number > (session.summarised_up_to_sequence or 0)
        ]
        combined_data: list[dict[str, str] | None] = [
            {
                "role": "user",
                "content": f"[Previous summary]: {session.context_summary}",
            },
            *[{"role": m.role, "content": m.content} for m in messages_since],
        ]
        client = LLMClient()
        response = client.complete(
            system_prompt=summarize_messages_prompt(),
            messages=[
                {
                    "role": "user",
                    "content": (
                        f"Here is the context to summarise:\n\n"
                        f"{json.dumps(combined_data, indent=2)}"
                    ),
                }
            ],
        )
        new_summary: str = response["content"]
    else:
        # First-time summarisation — process all summarisable messages
        new_summary: str = _generate_summary(summarisable)

    last_summarised_seq: int = summarisable[-1].sequence_number

    Session.objects.filter(pk=session.pk).update(
        context_summary=new_summary,
        summarised_up_to_sequence=last_summarised_seq,
    )
    session.context_summary = new_summary
    session.summarised_up_to_sequence = last_summarised_seq

    logger.info(
        "Context summary updated",
        extra={
            "session_id": str(session.pk),
            "summarised_up_to_sequence": last_summarised_seq,
        },
    )


def build_llm_messages(session: Session, all_history: list[Messages]) -> list[dict]:
    """
    Constructs the LLM message list using a tiered summarisation strategy.

    Tier 1 — short conversation (below threshold, no summary): send everything verbatim
    Tier 2 — summary exists: inject summary + only new messages since summary
    Always include the current user message raw.
    """
    current_msg = all_history[-1]
    previous_msgs = all_history[:-1]

    if not session.context_summary:
        # Short conversation, send everything
        return [{"role": msg.role, "content": msg.content} for msg in all_history]

    # Summary exists — inject it and append new messages
    cutoff = session.summarised_up_to_sequence or 0
    recent_msgs = [m for m in previous_msgs if m.sequence_number > cutoff]

    llm_messages = [
        {
            "role": "user",
            "content": f"[Summary of the conversation so far]:\n{session.context_summary}",
        },
        {
            "role": "assistant",
            "content": "Understood. I have the context from the earlier conversation and will continue from here.",
        },
        *[{"role": m.role, "content": m.content} for m in recent_msgs],
        {"role": "user", "content": current_msg.content},
    ]

    logger.debug(
        "Built LLM message list",
        extra={
            "session_id": str(session.pk),
            "total_history": len(all_history),
            "messages_sent_to_llm": len(llm_messages),
            "using_summary": True,
        },
    )

    return llm_messages


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------


@transaction.atomic
def send_message(*, session: Session, content: str) -> dict:
    """
    Handles a new user message: saves it, generates/refreshes summaries,
    calls the LLM, updates objective progress, and returns assistant response.

    Args:
        session (Session): The conversation session
        content (str): Text content from the user

    Returns:
        dict: {'user_message': Messages, 'assistant_message': Messages}
    """
    # 1. Save the incoming user message
    user_message = Messages.objects.create(
        session=session,
        role=MessageRolesEnum.USER.value,
        content=content,
    )

    # 2. Load full conversation history (including this message)
    all_history = list(
        Messages.objects.filter(session=session).order_by("sequence_number")
    )

    # 3. Update summary if needed (runs outside transaction locks if possible)
    _maybe_refresh_summary(session, all_history)

    # 4. Build context-optimised message list for LLM
    llm_messages = build_llm_messages(session, all_history)

    # 5. Build system prompt and tools
    system_prompt = build_system_prompt(session)
    tools, tool_choice = build_tools(session)

    # 6. Call the LLM
    client = LLMClient()
    llm_response = client.complete(
        system_prompt=system_prompt,
        messages=llm_messages,
        tools=tools,
        tool_choice=tool_choice,
    )

    assistant_content = llm_response.get("content", "")
    tool_data = llm_response.get("tool_data")

    # 7. Process tool data to update learning objectives
    if tool_data:
        if "conversational_response" in tool_data:
            assistant_content = tool_data.pop("conversational_response")

        for obj in session.scenario.learning_objectives.all():
            obj_data = tool_data.get(obj.key)
            if isinstance(obj_data, dict):
                SessionObjectiveProgress.objects.update_or_create(
                    session=session,
                    objective=obj,
                    defaults={
                        "is_met": obj_data.get("is_met", False),
                        "justification": obj_data.get("justification", ""),
                    },
                )

    # 8. Save assistant message with optional metadata and token tracking
    assistant_message = Messages.objects.create(
        session=session,
        role=MessageRolesEnum.ASSISTANT.value,
        content=assistant_content,
        metadata={"tool_data": tool_data} if tool_data else None,
        input_tokens=llm_response["usage"]["prompt_tokens"],
        output_tokens=llm_response["usage"]["completion_tokens"],
    )

    return {
        "user_message": user_message,
        "assistant_message": assistant_message,
    }


def stream_message(
    *, session: Session, content: str, chunk_size: int = 10, delay_seconds: float = 0.05
):
    """
    Streaming counterpart to send_message using provider-level streaming.
    Yields dict SSE payloads during generation and a final summary payload after persistence.

    Streamed events (each yielded value is a dict to be JSON-encoded by the view):
      - At the end: {"final": {"assistant_message": {...}, "objective_progress": [...]}}
      - On error: {"error": "..."}
    """
    # 1) Save user message up-front for ordering/history
    user_msg = Messages.objects.create(
        session=session,
        role=MessageRolesEnum.USER.value,
        content=content,
    )

    # 2) Build history and maybe refresh summary
    all_history = list(
        Messages.objects.filter(session=session).order_by("sequence_number")
    )
    _maybe_refresh_summary(session, all_history)

    # 3) LLM inputs
    llm_messages = build_llm_messages(session, all_history)
    system_prompt = build_system_prompt(session)
    tools, tool_choice = build_tools(session)

    client = LLMClient()

    # Chunking buffer
    word_buffer: list[str] = []
    sent_any: bool = False

    def flush(force: bool = False):
        nonlocal word_buffer, sent_any
        while len(word_buffer) >= chunk_size or (force and len(word_buffer) > 0):
            take = chunk_size if len(word_buffer) >= chunk_size else len(word_buffer)
            chunk_words = word_buffer[:take]
            word_buffer = word_buffer[take:]
            chunk_text = " ".join(chunk_words)
            if chunk_text:
                sent_any = True
                yield chunk_text
                time.sleep(delay_seconds)
            else:
                break

    final_payload = None
    try:
        # 4) Stream from LLM
        for evt in client.stream_complete(
            system_prompt=system_prompt,
            messages=llm_messages,
            tools=tools,
            tool_choice=tool_choice,
        ):  # yields dict events
            etype = evt.get("type")
            if etype == "text_delta":
                text_piece = evt.get("text", "") or ""
                if text_piece:
                    word_buffer.extend(text_piece.split())
                    for out in flush():
                        yield out
            elif etype == "final":
                # Flush any remaining buffered words
                for out in flush(force=True):
                    yield out
                final_payload = evt
                break

        if not final_payload:
            # Safety: no final received; end with a notice
            yield {"error": "Stream ended unexpectedly"}
            return

        assistant_content: str = final_payload.get("content", "") or ""
        tool_data = final_payload.get("tool_data")

        # 5) If nothing was streamed during deltas, stream the final content now in chunks
        if not sent_any and assistant_content:
            words_all = assistant_content.split()
            for i in range(0, len(words_all), chunk_size):
                chunk_text = " ".join(words_all[i : i + chunk_size])
                if chunk_text:
                    yield chunk_text
                    time.sleep(max(delay_seconds, 0.08))

        # 6) Persist objective progress if provided
        if tool_data:
            if isinstance(tool_data, dict) and "conversational_response" in tool_data:
                # ensure assistant_content aligns with tool
                assistant_content = (
                    tool_data.get("conversational_response") or assistant_content
                )
            for obj in session.scenario.learning_objectives.all():
                obj_data = (
                    tool_data.get(obj.key) if isinstance(tool_data, dict) else None
                )
                if isinstance(obj_data, dict):
                    SessionObjectiveProgress.objects.update_or_create(
                        session=session,
                        objective=obj,
                        defaults={
                            "is_met": obj_data.get("is_met", False),
                            "justification": obj_data.get("justification", ""),
                        },
                    )

        # 7) Save assistant message
        usage = (
            final_payload.get("usage", {}) if isinstance(final_payload, dict) else {}
        )
        Messages.objects.create(
            session=session,
            role=MessageRolesEnum.ASSISTANT.value,
            content=assistant_content,
            metadata={"tool_data": tool_data} if tool_data else None,
            input_tokens=usage.get("prompt_tokens"),
            output_tokens=usage.get("completion_tokens"),
        )

    except Exception as e:
        # Surface a readable error line to the stream consumer
        yield {"error": str(e)}
