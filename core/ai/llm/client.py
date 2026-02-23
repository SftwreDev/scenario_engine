"""LLM client utilities.

Lightweight wrapper over the Anthropic SDK providing error handling, retries,
and optional server-side streaming.
"""

import time
import logging
import anthropic
from django.conf import settings
from .exceptions import LLMAPIError, LLMRateLimitError, LLMTimeoutError

logger = logging.getLogger(__name__)

MAX_RETRIES = 3
RETRY_BACKOFF_BASE = 2  # seconds


class LLMClient:
    """
    Thin, resilient wrapper around the Anthropic SDK.
    Handles retries, error normalisation, and response logging.
    Not responsible for prompt construction or response parsing.
    """

    def __init__(self, api_key: str = None, model: str = None):
        self.client = anthropic.Anthropic(api_key=api_key or settings.ANTHROPIC_API_KEY)
        self.default_model = model or settings.DEFAULT_LLM_MODEL

    def complete(
        self,
        system_prompt: str,
        messages: list[dict],
        model: str = None,
        temperature: float = 0.7,
        max_tokens: int = 500,
        tools: list[dict] = None,
        tool_choice: dict = None,
    ) -> dict[str, str | dict | None]:
        """
        Send a completion request. Returns a dict with:
          - content: str (raw text response)
          - usage: dict (prompt_tokens, completion_tokens)
          - model: str

        Raises LLMAPIError, LLMRateLimitError, or LLMTimeoutError on failure.
        """
        model = model or self.default_model
        attempt = 0

        while attempt < MAX_RETRIES:
            try:
                logger.info(
                    "LLM request",
                    extra={
                        "model": model,
                        "message_count": len(messages),
                        "attempt": attempt + 1,
                    },
                )
                kwargs = {
                    "model": model,
                    "max_tokens": max_tokens,
                    "temperature": temperature,
                    "system": system_prompt,
                    "messages": messages,
                }
                if tools:
                    kwargs["tools"] = tools
                if tool_choice:
                    kwargs["tool_choice"] = tool_choice

                response = self.client.messages.create(**kwargs)

                raw_text = ""
                tool_data = None

                for block in response.content:
                    if block.type == "text":
                        raw_text += block.text
                    elif block.type == "tool_use":
                        tool_data = block.input

                logger.info(
                    "LLM response received",
                    extra={
                        "prompt_tokens": response.usage.input_tokens,
                        "completion_tokens": response.usage.output_tokens,
                    },
                )
                return {
                    "content": raw_text.strip(),
                    "tool_data": tool_data,
                    "usage": {
                        "prompt_tokens": response.usage.input_tokens,
                        "completion_tokens": response.usage.output_tokens,
                    },
                    "model": response.model,
                }

            except anthropic.RateLimitError as e:
                attempt += 1
                if attempt >= MAX_RETRIES:
                    raise LLMRateLimitError("Rate limit exceeded after retries")
                wait = RETRY_BACKOFF_BASE**attempt
                logger.warning(f"Rate limited, retrying in {wait}s")
                time.sleep(wait)

            except anthropic.APITimeoutError:
                raise LLMTimeoutError("LLM request timed out")

            except anthropic.AuthenticationError as e:
                raise LLMAPIError(f"Authentication failed: {e}", status_code=401)

            except anthropic.BadRequestError as e:
                raise LLMAPIError(f"Bad request: {e}", status_code=400)

            except anthropic.APIError as e:
                raise LLMAPIError(f"Unexpected API error: {e}")

    def stream_complete(
        self,
        *,
        system_prompt: str,
        messages: list[dict],
        model: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 500,
        tools: list[dict] | None = None,
        tool_choice: dict | None = None,
    ):
        """
        Server-side generator for streaming completions.

        Yields dict events of the form:
          - {"type": "text_delta", "text": "..."}
          - {"type": "tool_delta", "path": [..], "value": "..."}  # JSON incremental
          - {"type": "final", "content": str, "tool_data": dict|None, "usage": {...}, "model": str}
        """
        model = model or self.default_model

        kwargs = {
            "model": model,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "system": system_prompt,
            "messages": messages,
        }
        if tools:
            kwargs["tools"] = tools
        if tool_choice:
            kwargs["tool_choice"] = tool_choice

        try:
            with self.client.messages.stream(**kwargs) as stream:
                tool_input_aggregate = None  # we’ll reconstruct final tool JSON
                raw_text_accum = []

                for event in stream:
                    etype = getattr(event, "type", None)

                    # Text content block deltas (if the model emits any plain text blocks)
                    if etype == "content_block_delta" and getattr(event, "delta", None):
                        if getattr(event.delta, "type", "") == "text_delta":
                            text = event.delta.text or ""
                            if text:
                                raw_text_accum.append(text)
                                yield {"type": "text_delta", "text": text}

                    # Tool input JSON deltas for tool_use blocks
                    elif etype == "input_json_delta":
                        # event.delta is a partial JSON diff; Anthropic SDK provides `partial_json` on some events.
                        # We conservatively maintain our own accumulator when provided.
                        try:
                            partial = getattr(event, "partial_json", None)
                            if partial is None:
                                # Fallback: some versions expose .delta as a Python object
                                partial = getattr(event, "delta", None)
                            if partial is not None:
                                # Merge strategy: let’s re-serialize as a string and keep last known
                                # For streaming to client, surface leaf updates that affect conversational_response
                                # (best-effort; clients can simply treat as text deltas)
                                # Capture conversational_response slices if present.
                                cr = None
                                if (
                                    isinstance(partial, dict)
                                    and "conversational_response" in partial
                                ):
                                    cr = partial["conversational_response"]
                                elif isinstance(partial, str):
                                    # Sometimes deltas are tiny string fragments for a single field
                                    cr = partial
                                if cr:
                                    yield {"type": "text_delta", "text": cr}

                                tool_input_aggregate = partial  # keep latest (SDK also supplies .final_message at end)
                        except Exception as e:
                            logger.debug("Ignoring malformed tool delta: %s", e)

                    # End of stream: collect and yield final payload
                    elif etype == "message_stop":
                        final = stream.get_final_message()
                        final_text = ""  # composed assistant visible content
                        tool_data = None
                        usage = {"prompt_tokens": 0, "completion_tokens": 0}

                        # Extract final tool input if any; else use aggregated text
                        for block in final.content:
                            if block.type == "tool_use":
                                tool_data = block.input
                                if (
                                    isinstance(tool_data, dict)
                                    and "conversational_response" in tool_data
                                ):
                                    final_text = (
                                        tool_data.get("conversational_response") or ""
                                    )
                            elif block.type == "text":
                                final_text += block.text or ""

                        try:
                            usage = {
                                "prompt_tokens": getattr(
                                    final.usage, "input_tokens", 0
                                ),
                                "completion_tokens": getattr(
                                    final.usage, "output_tokens", 0
                                ),
                            }
                        except Exception:
                            pass

                        yield {
                            "type": "final",
                            "content": final_text.strip(),
                            "tool_data": tool_data,
                            "usage": usage,
                            "model": getattr(final, "model", model),
                        }
                        return

        except anthropic.RateLimitError as e:
            raise LLMRateLimitError("Rate limited during stream")
        except anthropic.APITimeoutError:
            raise LLMTimeoutError("LLM stream timed out")
        except anthropic.AuthenticationError as e:
            raise LLMAPIError(f"Authentication failed: {e}", status_code=401)
        except anthropic.BadRequestError as e:
            raise LLMAPIError(f"Bad request: {e}", status_code=400)
        except anthropic.APIError as e:
            raise LLMAPIError(f"Unexpected API error: {e}")
