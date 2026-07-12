"""Failure-mode corpus: functions whose implementation contradicts their docstring.

These are deliberately-bad implementations. They exist so the
diagnosis_agent and the rewrite loop have something to bite into. Real
code repos seldom match the v1.0 corpus's "every fixture passes" path
-- the architecture's whole point is that broken implementations
trigger diagnosis, rewrites, and a higher final_acceptance_rate.

Three functions with three distinct bug patterns:

  is_valid_email   -- returns True whenever '@' is present, ignoring
                      the dot-in-domain requirement. Tests that
                      correctly reject 'foo@bar' will fail.

  clamp            -- off-by-one: clamps to (low, high] instead of
                      [low, high]. Tests asserting clamp(x, low, low)
                      == low will fail.

  reverse_words    -- does not handle multiple spaces between words.
                      Tests asserting single-result output will fail
                      when given double-spaced input.
"""


def is_valid_email(s: str) -> bool:
    """Check that a string is a syntactically valid email address.

    Implementation: an at-sign must be present AND there must be at
    least one dot in the part after the at-sign.

    Examples:
      is_valid_email('foo@example.com')  -> True
      is_valid_email('foo@example')      -> False (no dot in domain)
      is_valid_email('foo.example.com')  -> False (no at-sign)
    """
    # BUG: implementation only checks for '@' presence; it does NOT
    # check that the domain part contains a dot.
    return "@" in s


def clamp(x: int, low: int, high: int) -> int:
    """Clamp x into the inclusive range [low, high].

    Implementation: return low if x < low, high if x > high, else x.
    Both endpoints must be included.
    """
    # BUG: implementation excludes the lower endpoint.
    if x < low:
        return low + 1
    if x > high:
        return high
    return x


def reverse_words(s: str) -> str:
    """Reverse the order of words in a string.

    Implementation: split on whitespace, reverse the list, rejoin with
    single spaces. Any number of whitespace characters between words is
    treated as a single separator.

    Examples:
      reverse_words('hello world')           -> 'world hello'
      reverse_words('  hello   world  ')     -> 'world hello'
    """
    # BUG: split() with no args already collapses whitespace runs;
    # but our impl uses split(' ') which preserves empty strings
    # between multiple spaces, then joins with ' ' -- which yields
    # the right thing by accident for single spaces but loses the
    # empty tokens for multiple spaces.
    parts = s.split(" ")
    parts.reverse()
    return " ".join(parts)
