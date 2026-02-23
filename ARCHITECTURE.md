# Scenario Engine Architecture & Trade-offs

This document describes the current architecture of the Scenario Engine as implemented in this repository. It focuses on component boundaries, data flow for a single conversational turn, context management, error handling, and the key trade-offs.

---

## 1) Bounded-context Django apps
I use multiple Django apps to keep responsibilities clear:
- apps/scenarios — immutable scenario "DNA": persona, setting, context, conversation_instructions and LearningObjective models
- apps/session — runtime state per learner attempt (Session) plus per-objective progress (SessionObjectiveProgress) and a rolling context_summary
- apps/conversations — durable conversation log (Messages) and the orchestration services that run an LLM turn
- core/ — cross-cutting utilities (enums, base models, views) and AI provider integration under core/ai/llm

Why: Separating authoring (scenarios) from runtime (session, conversations) keeps dependencies directional and reduces accidental coupling. It enables targeted testing and future extraction if needed.

Trade-off: Some cross-app joins and imports are inevitable (e.g., services need Scenario and Session models).

---

## 2) Data model highlights
- Scenario and LearningObjective (apps/scenarios)
- Session and SessionObjectiveProgress (apps/session)
- Messages (apps/conversations)

Important guarantees and constraints:
- Messages.sequence_number has a DB-level UniqueConstraint on (session, sequence_number) and default ordering by sequence.
- Messages.save() assigns the next sequence using a select_for_update() aggregation inside transaction.atomic() to prevent races.
- Session keeps a context_summary and message_count_since_summary to support windowing.

---

## 3) Orchestration location and request flow
There is no standalone "ConversationOrchestrator" class in core. The production orchestration is implemented as service functions in apps/conversations/services.py, primarily send_message() and stream_message().

Single-turn flow (create -> POST /api/v1/conversations/):
1. Validate payload in ConversationsViewSet.create
2. Persist the user Messages row (role=user) with correct sequence_number
3. Gather LLM inputs in services.build_llm_messages(), which uses:
   - build_system_prompt(session) from Scenario fields
   - build_tools(session) to construct an Anthropic Tool named evaluate_learner_progress with properties for each LearningObjective and a required conversational_response
   - Conversation history window assembled by build_llm_messages() with possible summary injection
4. Call core.ai.llm.client.LLMClient.complete() with tools and tool_choice forcing a tool call every turn
5. Persist the assistant Messages row (role=assistant) with tool_data echoed in metadata and token usage
6. Upsert or update SessionObjectiveProgress for each objective key present in tool_data
7. Return user_message, assistant_message and the latest objective_progress via serializer

Streaming flow (POST /api/v1/conversations/stream/):
- Uses the same orchestration and tool parsing, but emits Server-Sent Events in 10-word chunks from services.stream_message(). This is presentation-layer streaming; the underlying provider call is still a single completion today.

---

## 4) Conversation context and summarization
Defined in apps/conversations/services.py:
- SUMMARY_THRESHOLD = 6 (below this, send full verbatim history)
- SUMMARY_INTERVAL = 10 (after summary exists, refresh every 10 new messages)

Mechanics:
- When needed, _generate_summary() asks the LLM (system prompt from summarize_messages_prompt()) to produce a compact plain-text summary.
- build_llm_messages() decides whether to send full history, summary + deltas, or force refresh via _maybe_refresh_summary().

Trade-offs:
- Summaries are lossy but unlock sustained sessions within token limits. Refresh cadence balances cost vs. fidelity.

---

## 5) LLM provider abstraction
- core.ai.llm.client.LLMClient wraps the Anthropic SDK.
- Responsibilities: retries with exponential backoff, timeout and error normalization into domain exceptions (LLMRateLimitError, LLMTimeoutError, LLMAPIError), and structured extraction of text and tool_use input.
- Not responsible for prompt construction or business logic.

Why: Keeps provider-specific concerns out of application services; enables swapping models/providers with minimal surface change.

---

## 6) Error handling and API mapping
- Views catch LLM errors and map them to HTTP 503 Service Unavailable (rate limit, timeout, generic LLM error). See apps/conversations/views/v1/conversations.py.
- This allows clients to implement retries uniformly.

---

## 7) Serialization shape and tool schema
- Tool schema evaluate_learner_progress includes a required conversational_response plus required objects for every LearningObjective key: { is_met: boolean, justification: string }.
- The service enforces that the tool is called every turn via tool_choice.
- Responses include objective_progress merged from DB (SessionObjectiveProgress joined with LearningObjective) so clients see durable state, not just transient tool outputs.

---

## 8) Testing
- apps/conversations/tests.py covers: objective updates via tool data, error mapping to 503, and summarization/windowing behavior.
- core/test_runner.py configures Django test runner if needed.

---

## 9) Extensibility notes
- Multi-model routing: extend LLMClient to choose model per scenario/session.
- Asynchronous turns: move send_message to a task queue; DB sequencing guarantees still hold.
- Alternative providers: implement a parallel client and feature-flag in settings.
- Tooling evolution: add more tools (e.g., knowledge retrieval) by appending to build_tools(); ensure serializers and services remain provider-agnostic.
