# Scenario Engine

A Django-based backend for configurable, LLM-driven learning scenarios. It provides:
- Scenario authoring (persona, setting, context, objectives)
- Multi-turn conversations with an LLM persona
- Structured, per-objective assessment each turn via LLM tools
- Conversation history management with summarization
- OpenAPI docs via drf-spectacular

## Quickstart

### Requirements
- Python 3.11+
- PostgreSQL (recommended) or SQLite for local quickstart
- Anthropic API key (Claude 3.5 Haiku suggested)

### Setup
1. Clone the repo and create a virtual env
   ```bash
   git clone https://github.com/SftwreDev/scenario_engine.git
   cd scenario_engine
   python -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```

2. Configure environment variables (create a `.env` file in project root):
   ```env
   ANTHROPIC_API_KEY=your_key_here
   DEFAULT_LLM_MODEL=claude-3-5-haiku-latest
   DATABASE_URL=postgres://user:pass@localhost:5432/scenario_engine  # optional; sqlite by default
   ```

3. Run migrations
   ```bash
   python manage.py migrate
   ```

4. (Optional) Create a superuser to use Django Admin
   ```bash
   python manage.py createsuperuser
   ```

5. Seed the sample veterinary scenario (Dave & Duchess)
   ```bash
   python manage.py seed_vet_scenario
   ```

6. Start the server
   ```bash
   python manage.py runserver
   ```

7. Explore API docs
   - Swagger UI: http://localhost:8000/api/docs/
   - ReDoc: http://localhost:8000/api/redoc/

## Using the API

### 1) Create a session for a scenario
Find the scenario ID via Admin or API (GET /api/scenarios/). Then:
```bash
curl -X POST http://localhost:8000/api/v1/sessions/ \
  -H 'Content-Type: application/json' \
  -d '{"scenario": "<SCENARIO_UUID>"}'
```
Response contains the session UUID.

### 2) Send a message in a session (non-streaming)
```bash
curl -X POST http://localhost:8000/api/v1/conversations/ \
  -H 'Content-Type: application/json' \
  -d '{"session": "<SESSION_UUID>", "content": "Hi Dave, can you tell me when Duchess went off her feed?"}'
```bash
Response includes:
- user_message and assistant_message (ordered, with timestamps)
- objective_progress: array of per-objective { objective_key, label, is_met, justification }

The backend uses an Anthropic Tool named `evaluate_learner_progress` that the LLM must call every turn. The tool input includes a `conversational_response` plus an object for each learning objective to update `{ is_met, justification }`.

### 3) Stream the assistant message (Server-Sent Events)
```bash
curl -N -X POST http://localhost:8000/api/v1/conversations/stream/ \
  -H 'Content-Type: application/json' \
  -d '{"session": "<SESSION_UUID>", "content": "Start streaming, please."}'
```bash
- Emits `text/event-stream` lines of the form: `data: {"content_chunk": "..."}` (chunked by ~10 words) sourced directly from provider-level streaming.
- Ends with a final event containing the full assistant_message and objective_progress

### Conversation context management
- Messages are persisted with monotonically increasing `sequence_number` (DB-guarded).
- Context summarization (see ARCHITECTURE.md for details):
  - Below 6 total messages: send all history to the LLM
  - Once a summary exists: send summary + only messages since last summary, plus the current user turn
  - Refresh the summary every 10 new messages

## Admin authoring
Django Admin is enabled for quick authoring:
- Scenarios and Learning Objectives
- Sessions and Session Objective Progress
- Messages (conversation log)

Visit http://localhost:8000/admin/ to create/edit scenarios and objectives without code changes.

## Tests
Run tests with:
```bash
python manage.py test
```bash

Covers:
- Objective updates via tool data
- API mapping to 503 for LLM rate-limit/timeout/errors
- Summarization/windowing behavior

## Architecture overview
- The active orchestration path lives in `apps/conversations/services.py` (send_message, stream_message).
- `core/ai/llm/` contains the provider wrapper and utilities; prompt construction and tool schema are built in the conversations service layer.
For deeper rationale and trade-offs, see ARCHITECTURE.md.
