"""Append-only JSONL storage for readings, judgments and probes."""

from __future__ import annotations

import json
import threading
from datetime import UTC, datetime
from pathlib import Path

from pydantic import BaseModel

_lock = threading.Lock()


def now_iso() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def append_jsonl(path: str | Path, record: BaseModel) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    line = record.model_dump_json() + "\n"
    with _lock, path.open("a") as f:
        f.write(line)


def read_jsonl[M: BaseModel](path: str | Path, model: type[M]) -> list[M]:
    path = Path(path)
    if not path.exists():
        return []
    return [
        model.model_validate(json.loads(line))
        for line in path.read_text().splitlines()
        if line.strip()
    ]
