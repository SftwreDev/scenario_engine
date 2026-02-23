"""Exception hierarchy for LLM client errors.

Defines narrow exception types used by the LLM client so callers can handle
rate limits, timeouts, and API problems explicitly.
"""

class LLMError(Exception):
    """Base for all LLM service errors."""


class LLMAPIError(LLMError):
    """Unrecoverable API error (auth, bad request)."""

    def __init__(self, message, status_code=None):
        super().__init__(message)
        self.status_code = status_code


class LLMRateLimitError(LLMError):
    """Rate limited — caller should back off."""


class LLMTimeoutError(LLMError):
    """Request timed out."""


class LLMResponseParseError(LLMError):
    """Got a response but couldn't extract structured data from it."""

    def __init__(self, message, raw_response=None):
        super().__init__(message)
        self.raw_response = raw_response
