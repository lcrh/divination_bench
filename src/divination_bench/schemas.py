"""Shared data models. Every other module reads and writes these shapes."""

from __future__ import annotations

from datetime import date
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, Field


class Domain(StrEnum):
    politics = "politics"
    geopolitics = "geopolitics"
    law = "law"
    economics = "economics"
    business = "business"
    tech = "tech"
    science = "science"
    sports = "sports"
    culture = "culture"
    other = "other"


class Source(BaseModel):
    url: str
    title: str
    publisher: str
    published_date: date
    excerpt: str | None = Field(
        default=None,
        description="Short quote or close paraphrase of the relevant facts from this source.",
    )


class Question(BaseModel):
    id: str = Field(description="Stable slug, e.g. 'japan-snap-election-2026'.")
    domain: Domain
    title: str
    question: str = Field(
        description="The question put to the oracle, phrased neutrally."
    )
    question_type: Literal["binary", "multiple_choice", "open"]
    options: list[str] | None = Field(
        default=None,
        description="Possible answers for binary / multiple_choice questions.",
    )
    resolution_criteria: str = Field(
        description="Judge-only (accuracy round): may name the actual outcome, so it "
        "must never be shown to forecasters or in the precision round."
    )
    context_summary: str = Field(
        description="What was known before the decisive event. Must not leak the outcome."
    )
    context_sources: list[Source]
    event_date: date = Field(
        description="Date the decisive outcome happened / became known."
    )
    outcome_summary: str
    resolved_answer: str = Field(
        description="For binary / multiple_choice: one of `options`. For open: a short statement."
    )
    outcome_sources: list[Source]
    market: dict | None = Field(
        default=None,
        description="Optional prediction-market info: {platform, url, pre_event_probability, as_of}.",
    )
    backup: bool = Field(
        default=False, description="Reserve question, skipped by default."
    )
    notes: str | None = None

    @property
    def latest_context_source_date(self) -> date:
        return max(s.published_date for s in self.context_sources)

    @property
    def latest_outcome_source_date(self) -> date:
        return max(s.published_date for s in self.outcome_sources)

    @property
    def context_as_of(self) -> date:
        return self.latest_context_source_date


class Method(StrEnum):
    tarot = "tarot"
    iching = "iching"
    predict = "predict"
    # Reading only: the same draw as tarot / iching, interpreted without a prediction.
    tarot_reading = "tarot_reading"
    iching_reading = "iching_reading"


READING_ONLY_BASE = {
    Method.tarot_reading: Method.tarot,
    Method.iching_reading: Method.iching,
}


def base_method(method: Method | str) -> Method:
    """The divination system a method draws from (itself, for non reading-only)."""
    m = Method(method)
    return READING_ONLY_BASE.get(m, m)


class Reading(BaseModel):
    """One generated reading: (question, method, seed, model)."""

    question_id: str
    method: Method
    seed: int
    model: str
    cast: dict | None = Field(
        default=None,
        description="Structured draw (cards or hexagram). None for `predict`.",
    )
    cast_text: str | None = None
    reading: str | None = Field(
        default=None, description="Full interpretation. None for `predict`."
    )
    prediction: str = Field(description="Empty for reading-only methods.")
    answer: str | None = Field(
        default=None,
        description="Chosen option for binary / multiple_choice questions.",
    )
    raw_response: str
    usage: dict | None = None
    created_at: str
    fingerprint: str | None = Field(
        default=None,
        description="Hash of (model, prompt); a mismatch means the reading is stale.",
    )


JudgeMode = Literal["full", "prediction", "reading"]
Comparison = Literal["models", "methods"]


class RankedItem(BaseModel):
    label: str
    rank: int = Field(description="1 = best, by the pooled probability `score`.")
    score: float = Field(
        description="Pooled probability of being the best forecast in its group: "
        "normalised sqrt(p_accuracy * p_precision)."
    )
    p_accuracy: float = Field(
        description="Probability of being the forecast that best matches what "
        "happened, averaged over presentation orders."
    )
    p_precision: float = Field(
        description="Probability of being the most specific forecast (judged without "
        "the outcome), averaged over presentation orders."
    )


class Judgment(BaseModel):
    """One judge's forced ranking of a group of anonymised readings."""

    question_id: str
    comparison: Comparison
    judge_model: str
    mode: JudgeMode
    seed: int
    fixed_method: Method | None = None
    fixed_model: str | None = None
    label_map: dict[str, str] = Field(
        description="Anonymous label -> reading key ('method|model')."
    )
    ranking: list[RankedItem]
    raw_response: str
    usage: dict | None = None
    created_at: str
    fingerprint: str | None = Field(
        default=None,
        description="Hash of (judge, requests incl. items); a mismatch means it is stale.",
    )


class KnowledgeProbe(BaseModel):
    """Did a tested model already know the outcome without being told?"""

    question_id: str
    model: str
    knows_outcome: Literal["yes", "no", "unsure"]
    stated_answer: str | None
    correct: bool | None
    raw_response: str
    usage: dict | None = None
    created_at: str
    fingerprint: str | None = None
