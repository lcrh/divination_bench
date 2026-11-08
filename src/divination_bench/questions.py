"""Load and validate the question set (one YAML file per question)."""

from __future__ import annotations

import sys
from pathlib import Path

import yaml

from .schemas import Question


def load_question(path: Path) -> Question:
    q = Question.model_validate(yaml.safe_load(path.read_text()))
    problems = check_question(q)
    if problems:
        raise ValueError(f"{path}: " + "; ".join(problems))
    return q


def load_questions(
    directory: str | Path, ids: list[str] | None = None
) -> list[Question]:
    paths = sorted(Path(directory).rglob("*.yaml"))
    qs = [load_question(p) for p in paths]
    seen: set[str] = set()
    for q in qs:
        if q.id in seen:
            raise ValueError(f"Duplicate question id {q.id}")
        seen.add(q.id)
    if ids:
        qs = [q for q in qs if q.id in ids]
    return qs


def check_question(q: Question) -> list[str]:
    problems = []
    if q.question_type in ("binary", "multiple_choice"):
        if not q.options:
            problems.append("binary/multiple_choice question needs options")
        elif q.resolved_answer not in q.options:
            problems.append(f"resolved_answer {q.resolved_answer!r} not in options")
    if not q.context_sources:
        problems.append("no context sources")
    if not q.outcome_sources:
        problems.append("no outcome sources")
    if q.context_sources and q.latest_context_source_date > q.event_date:
        problems.append("a context source is dated after the event")
    return problems


def main() -> None:
    directory = sys.argv[1] if len(sys.argv) > 1 else "data/questions"
    qs = load_questions(directory)
    for q in qs:
        print(
            f"{q.domain:<12} {q.id:<45} ctx<={q.latest_context_source_date} "
            f"event={q.event_date} out<={q.latest_outcome_source_date}"
        )
    print(f"{len(qs)} questions OK")


if __name__ == "__main__":
    main()
