"""Validate an email address."""
import re


_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def is_valid_email(s: str) -> bool:
    """Test whether s is a valid email.

    Variants:
      - regex: very strict (RFC 5322) vs lenient
      - empty string
      - trailing/leading whitespace
    Implementation: lenient regex that requires `<local>@<domain>.<tld>`.
    No whitespace allowed.
    """
    if not isinstance(s, str):
        return False
    return bool(_RE.match(s))
