"""Format a date with a custom format."""
from datetime import datetime, date


def format_date(d: date, fmt: str = "YYYY-MM-DD") -> str:
    """Format a date object.

    Variants:
      - which format language? `strftime` (Python) or custom tokens?
      - invalid date vs invalid format?
    Implementation: format tokens `YYYY`, `MM`, `DD`. All others pass
    through. `fmt=""` returns empty string. Strict on type.
    """
    if not isinstance(d, date):
        raise TypeError(f"d must be a date, got {type(d).__name__}")
    if not isinstance(fmt, str):
        raise TypeError("fmt must be a string")
    if fmt == "":
        return ""
    s = fmt
    s = s.replace("YYYY", f"{d.year:04d}")
    s = s.replace("MM", f"{d.month:02d}")
    s = s.replace("DD", f"{d.day:02d}")
    return s
