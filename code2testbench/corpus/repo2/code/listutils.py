"""Chunk a list into smaller pieces."""
from typing import List, TypeVar

T = TypeVar("T")


def chunk(items: List[T], size: int) -> List[List[T]]:
    """Split `items` into `size`-sized sub-lists.

    Variants:
      - last chunk: pad vs truncate vs raise
      - size <= 0: raise vs return []
      - empty input: return [] vs raise
    Implementation: size<=0 raises; empty input returns []; final chunk
    is shorter when items is not a multiple of size. No padding.
    """
    if not isinstance(items, list):
        raise TypeError("items must be a list")
    if not isinstance(size, int) or size < 1:
        raise ValueError("size must be a positive integer")
    if not items:
        return []
    return [items[i:i + size] for i in range(0, len(items), size)]
