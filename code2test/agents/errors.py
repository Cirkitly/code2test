"""
Errors that must stop a run instead of being logged per component.

The agents fall back to an empty result when one LLM call fails, so one bad
component does not sink the whole run. A rejected API key or an unknown model
fails every call the same way, though, and swallowing it turns a broken setup
into a "successful" run that generated nothing.
"""

from typing import Optional

# 401: bad API key, 403: key lacks access, 404: unknown model name
FATAL_STATUS_CODES = {401, 403, 404}


class ModelAccessError(RuntimeError):
    """The LLM provider rejected the request in a way retrying cannot fix."""


def _status_code(error: BaseException) -> Optional[int]:
    code = getattr(error, "status_code", None)
    return code if isinstance(code, int) else None


def raise_if_fatal(error: BaseException) -> None:
    """Re-raise `error` as ModelAccessError if no later LLM call can succeed."""
    if isinstance(error, ModelAccessError):
        raise error
    code = _status_code(error)
    if code in FATAL_STATUS_CODES:
        raise ModelAccessError(
            f"The model provider rejected the request (HTTP {code}). "
            "Check the API key and CODE2TEST_MODEL. Details: "
            f"{error}"
        ) from error
