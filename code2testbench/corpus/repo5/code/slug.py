"""Slugify a string for URL use."""
import re


_NON_SLUG = re.compile(r"[^a-z0-9]+")
_M_DASHES = re.compile(r"-+")


def slugify(text: str) -> str:
    """Convert a string to a URL-safe slug.

    Variants:
      - case: lowercase vs preserve
      - separators: '-' vs '_'
      - accents: strip vs preserve-as-is
      - empty input
    Implementation: lowercase; replace runs of non-alphanumeric with '-';
    strip leading/trailing dashes; remove duplicate dashes; ASCII-only.
    """
    if not isinstance(text, str):
        raise TypeError("text must be a string")
    s = text.lower()
    s = _NON_SLUG.sub("-", s)
    s = _M_DASHES.sub("-", s)
    return s.strip("-")
