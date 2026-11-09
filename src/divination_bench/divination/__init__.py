"""Deterministic divination casts. The cast depends only on (question_id, method, seed)."""

from __future__ import annotations

from ..schemas import Method, base_method
from .iching import cast_iching, format_iching
from .thoth import cast_tarot, format_tarot

__all__ = ["cast", "cast_iching", "cast_tarot", "format_iching", "format_tarot"]


def cast(question_id: str, method: Method, seed: int) -> tuple[dict | None, str | None]:
    """Return (structured cast, formatted text), or (None, None) for `predict`.
    Reading-only methods get exactly the draw of their base method."""
    method = base_method(method)
    if method == Method.tarot:
        c = cast_tarot(question_id, seed)
        return c, format_tarot(c)
    if method == Method.iching:
        c = cast_iching(question_id, seed)
        return c, format_iching(c)
    return None, None
