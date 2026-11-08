"""Guarantee every question resolves after the tested models could have seen it."""

from __future__ import annotations

from datetime import date

from pydantic import BaseModel

from .schemas import Question


class ModelCutoff(BaseModel):
    model: str
    training_cutoff: date
    release_date: date
    source: str

    @property
    def safe_after(self) -> date:
        """Nothing after release can be in the weights, and we never enable web search."""
        return max(self.training_cutoff, self.release_date)


def parse_cutoffs(raw: dict) -> dict[str, ModelCutoff]:
    return {
        model: ModelCutoff(model=model, **info) for model, info in (raw or {}).items()
    }


def cutoff_violations(
    questions: list[Question], models: list[str], cutoffs: dict[str, ModelCutoff]
) -> list[str]:
    problems = []
    for model in models:
        if model.startswith("mock/"):
            continue
        if model not in cutoffs:
            problems.append(f"{model}: no documented cutoff in config `model_cutoffs`")
            continue
        safe_after = cutoffs[model].safe_after
        for q in questions:
            if q.event_date <= safe_after:
                problems.append(
                    f"{q.id}: event {q.event_date} is not after {model} cutoff/release {safe_after}"
                )
    return problems
