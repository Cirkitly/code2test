"""Truncate a string to a maximum length without breaking words."""
from typing import Optional


def truncate(text: str, max_chars: int = 100, ellipsis: str = "...") -> str:
    """Return a shortened version of text.

    Variants:
      - cut mid-word vs at last space before limit
      - include ellipsis suffix vs not
      - max_chars is len(text) before OR after truncation
    Implementation: short-circuit on text shorter than limit; cut to last
    space before limit and append ellipsis. max_chars is the output bound
    (post-ellipsis).
    """
    if not isinstance(text, str):
        raise TypeError("text must be a string")
    if not isinstance(max_chars, int) or max_chars < 1:
        raise ValueError("max_chars must be a positive integer")
    if len(text) <= max_chars:
        return text
    keep = max_chars - len(ellipsis)
    if keep <= 0:
        return ellipsis[:max_chars]
    truncated = text[:keep]
    last_space = truncated.rfind(" ")
    if last_space > 0:
        truncated = truncated[:last_space]
    return truncated.rstrip() + ellipsis
