"""Append-only JSONL storage for readings, judgments and probes."""

from __future__ import annotations

import hashlib
import json
import threading
from datetime import UTC, datetime
from pathlib import Path

from pydantic import BaseModel

_lock = threading.Lock()


def now_iso() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def append_jsonl(path: str | Path, record: BaseModel) -> None:
    append_line(path, record.model_dump_json())


def append_line(path: str | Path, line: str) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with _lock, path.open("a") as f:
        f.write(line + "\n")


def read_jsonl[M: BaseModel](path: str | Path, model: type[M]) -> list[M]:
    path = Path(path)
    if not path.exists():
        return []
    return [
        model.model_validate(json.loads(line))
        for line in path.read_text().splitlines()
        if line.strip()
    ]


def fingerprint(model: str, messages: list[dict]) -> str:
    """Identity of a request: a stored record is reusable only if this still matches."""
    blob = json.dumps({"model": model, "messages": messages}, sort_keys=True)
    return hashlib.sha256(blob.encode()).hexdigest()[:16]


def is_current(stored: str | None, expected: str) -> bool:
    """Records written before fingerprints existed (None) are kept as they are."""
    return stored is None or stored == expected


def merge_usage(usages: list[dict | None]) -> dict | None:
    """Sum numeric usage fields over several attempts at the same request."""
    present = [u for u in usages if u]
    if not present:
        return None
    merged: dict = dict(present[-1])
    for k in {k for u in present for k, v in u.items() if _is_number(v)}:
        merged[k] = sum(u.get(k) or 0 for u in present if _is_number(u.get(k, 0)))
    merged["attempts"] = len(usages)
    return merged


def _is_number(v: object) -> bool:
    return isinstance(v, int | float) and not isinstance(v, bool)
