"""Anonymised forced ranking of readings by a decision model (TypeSafe Jev).

A group (2-3 readings of one question and seed that differ only in model, or only in
method) is ranked by successive choice: the judge picks the best of the remaining
forecasts, that one is removed, and it picks again, which is a Plackett-Luce ranking.
Each pick pools two Choice answers, accuracy (judged with the outcome) and precision
(judged without it), as a log-linear opinion pool: P(i) ∝ sqrt(P_acc(i) * P_prec(i)).
Every round is shown in all cyclic rotations of the remaining forecasts and the
probabilities are averaged, so each forecast appears once in every position.
"""

from __future__ import annotations

import hashlib
import json
import math
import random
from collections import defaultdict
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from functools import partial
from pathlib import Path

from rich.console import Console

from .generate import run_grid
from .llm import DecisionError, LLMClient
from .prompts_judge import accuracy_request, precision_request
from .schemas import (
    Comparison,
    JudgeMode,
    Judgment,
    Method,
    Question,
    RankedItem,
    Reading,
)
from .store import (
    append_jsonl,
    fingerprint,
    is_current,
    merge_usage,
    now_iso,
    read_jsonl,
)

LABELS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
DECISION_ATTEMPTS = 3
FULL_MODE_METHODS = (Method.tarot, Method.iching)

console = Console(stderr=True)

JudgmentKey = tuple[str, str, str, int, str | None, str | None, str]


def reading_key(r: Reading) -> str:
    return f"{r.method}|{r.model}"


def split_key(key: str) -> tuple[str, str]:
    method, model = key.split("|", 1)
    return method, model


@dataclass(frozen=True)
class JudgeGroup:
    """A set of readings ranked against each other."""

    question_id: str
    comparison: Comparison
    mode: JudgeMode
    seed: int
    fixed_method: Method | None
    fixed_model: str | None
    readings: tuple[Reading, ...]

    def key(self, judge: str) -> JudgmentKey:
        return (
            self.question_id,
            self.comparison,
            self.mode,
            self.seed,
            str(self.fixed_method) if self.fixed_method else None,
            self.fixed_model,
            judge,
        )


def judgment_key(j: Judgment) -> JudgmentKey:
    return (
        j.question_id,
        j.comparison,
        j.mode,
        j.seed,
        str(j.fixed_method) if j.fixed_method else None,
        j.fixed_model,
        j.judge_model,
    )


def _eligible(r: Reading, mode: JudgeMode) -> bool:
    if mode == "full":
        return r.method in FULL_MODE_METHODS and bool(r.reading)
    return bool(r.prediction.strip())


def build_groups(
    readings: Iterable[Reading],
    comparisons: Sequence[Comparison] = ("models", "methods"),
    modes: Sequence[JudgeMode] = ("full", "prediction"),
) -> list[JudgeGroup]:
    latest: dict[tuple[str, str, int, str], Reading] = {}
    for r in readings:
        latest[(r.question_id, r.method, r.seed, r.model)] = r

    by_method: dict[tuple[str, int, Method], list[Reading]] = defaultdict(list)
    by_model: dict[tuple[str, int, str], list[Reading]] = defaultdict(list)
    for r in latest.values():
        by_method[(r.question_id, r.seed, r.method)].append(r)
        by_model[(r.question_id, r.seed, r.model)].append(r)

    groups: list[JudgeGroup] = []
    for comparison in comparisons:
        for mode in modes:
            if comparison == "models":
                buckets = {
                    (q, s, m, None): rs
                    for (q, s, m), rs in by_method.items()
                    if mode == "prediction" or m in FULL_MODE_METHODS
                }
            else:
                buckets = {(q, s, None, m): rs for (q, s, m), rs in by_model.items()}
            for (qid, seed, fmethod, fmodel), rs in buckets.items():
                items = sorted((r for r in rs if _eligible(r, mode)), key=reading_key)
                if len(items) >= 2:
                    groups.append(
                        JudgeGroup(
                            qid, comparison, mode, seed, fmethod, fmodel, tuple(items)
                        )
                    )
    groups.sort(key=lambda g: g.key(""))
    return groups


def assign_labels(group: JudgeGroup, judge: str) -> dict[str, Reading]:
    """Deterministic per-(group, judge) anonymous labels."""
    seed_str = "|".join(str(x) for x in group.key(judge))
    rng = random.Random(int(hashlib.sha256(seed_str.encode()).hexdigest(), 16))
    items = list(group.readings)
    rng.shuffle(items)
    return dict(zip(LABELS, items, strict=False))


def rotations(labels: Sequence[str]) -> list[list[str]]:
    return [list(labels[i:]) + list(labels[:i]) for i in range(len(labels))]


def first_round_requests(
    q: Question, group: JudgeGroup, judge: str
) -> list[tuple[dict, dict]]:
    items = assign_labels(group, judge)
    reqs = []
    for order in rotations(list(items)):
        shown = {lab: items[lab] for lab in order}
        reqs += [
            accuracy_request(q, shown, group.mode),
            precision_request(q, shown, group.mode),
        ]
    return reqs


def group_fingerprint(q: Question, group: JudgeGroup, judge: str) -> str:
    """Changes whenever the judge would see something different: other items, edited
    readings, an edited question or outcome, or changed rubric text. Later rounds
    depend on earlier answers, so the first round stands for the whole ranking."""
    reqs = [
        {"state": s, "questions": qs} for s, qs in first_round_requests(q, group, judge)
    ]
    return fingerprint(judge, reqs)


def parse_choice(answer: dict, labels: Sequence[str]) -> dict[str, float]:
    if answer.get("type") != "choice":
        raise DecisionError(f"not a choice answer: {answer!r}")
    probs = answer.get("probabilities")
    if probs:
        if set(probs) != set(labels):
            raise DecisionError(f"probabilities for {sorted(probs)}, expected {labels}")
        out = {lab: max(0.0, float(probs[lab])) for lab in labels}
    elif answer.get("choice") in labels:
        out = {lab: float(lab == answer["choice"]) for lab in labels}
    else:
        raise DecisionError(f"unknown choice {answer.get('choice')!r}")
    total = sum(out.values())
    if total <= 0:
        raise DecisionError("all choice probabilities are zero")
    return {lab: p / total for lab, p in out.items()}


def _ask(
    client: LLMClient,
    judge: str,
    request: tuple[dict, dict],
    usages: list,
    raws: list,
) -> dict[str, float]:
    state, questions = request
    ((key, q),) = questions.items()
    labels = list(q["criteria"])
    error: Exception | None = None
    for _ in range(DECISION_ATTEMPTS):
        try:
            result = client.decide(judge, state, questions)
            usages.append(result.usage)
            raws.append({"question": key, "order": labels, "response": result.raw})
            return parse_choice(result.answers[key], labels)
        except DecisionError as e:
            error = e
    raise DecisionError(f"{judge} gave no usable {key} answer: {error}")


def pool(p_acc: dict[str, float], p_prec: dict[str, float]) -> dict[str, float]:
    """Log-linear (geometric) opinion pool of two distributions over the same labels."""
    raw = {lab: math.sqrt(p_acc[lab] * p_prec[lab]) for lab in p_acc}
    total = sum(raw.values())
    if total <= 0:
        raw = {lab: (p_acc[lab] + p_prec[lab]) / 2 for lab in p_acc}
        total = sum(raw.values())
    return {lab: v / total for lab, v in raw.items()}


def _round(
    q: Question,
    items: dict[str, Reading],
    remaining: list[str],
    mode: JudgeMode,
    judge: str,
    client: LLMClient,
    usages: list,
    raws: list,
) -> tuple[dict[str, float], dict[str, float]]:
    """Accuracy and precision choice probabilities over `remaining`, averaged over
    all cyclic presentation orders."""
    acc: dict[str, float] = defaultdict(float)
    prec: dict[str, float] = defaultdict(float)
    orders = rotations(remaining)
    for order in orders:
        shown = {lab: items[lab] for lab in order}
        for lab, p in _ask(
            client, judge, accuracy_request(q, shown, mode), usages, raws
        ).items():
            acc[lab] += p / len(orders)
        for lab, p in _ask(
            client, judge, precision_request(q, shown, mode), usages, raws
        ).items():
            prec[lab] += p / len(orders)
    return dict(acc), dict(prec)


def judge_group(
    question: Question, group: JudgeGroup, judge: str, client: LLMClient
) -> Judgment:
    items = assign_labels(group, judge)
    remaining = list(items)
    usages: list[dict | None] = []
    raws: list[dict] = []
    order: list[str] = []
    first: tuple[dict[str, float], dict[str, float], dict[str, float]] | None = None
    while len(remaining) > 1:
        acc, prec = _round(
            question, items, remaining, group.mode, judge, client, usages, raws
        )
        pooled = pool(acc, prec)
        if first is None:
            first = (acc, prec, pooled)
        best = max(remaining, key=lambda lab: (pooled[lab], acc[lab], -ord(lab)))
        order.append(best)
        remaining.remove(best)
    order += remaining
    assert first is not None
    acc0, prec0, pooled0 = first
    return Judgment(
        question_id=group.question_id,
        comparison=group.comparison,
        judge_model=judge,
        mode=group.mode,
        seed=group.seed,
        fixed_method=group.fixed_method,
        fixed_model=group.fixed_model,
        label_map={lab: reading_key(r) for lab, r in items.items()},
        ranking=[
            RankedItem(
                label=lab,
                rank=i + 1,
                score=pooled0[lab],
                p_accuracy=acc0[lab],
                p_precision=prec0[lab],
            )
            for i, lab in enumerate(order)
        ],
        raw_response=json.dumps(raws),
        usage=merge_usage(usages),
        created_at=now_iso(),
        fingerprint=group_fingerprint(question, group, judge),
    )


def current_judgments(judgments: Iterable[Judgment]) -> list[Judgment]:
    """One judgment per (group, judge): the one covering the most items, newest first
    among equals, so a later narrowed rerun cannot displace a fuller judgment."""
    best: dict[JudgmentKey, tuple[int, int, Judgment]] = {}
    for i, j in enumerate(judgments):
        key = judgment_key(j)
        rank = (len(j.ranking), i)
        if key not in best or rank > best[key][:2]:
            best[key] = (*rank, j)
    return [j for *_, j in sorted(best.values(), key=lambda t: t[1])]


def run_judging(
    questions: Sequence[Question],
    readings: Sequence[Reading],
    judges: Sequence[str],
    client: LLMClient,
    out_path: str | Path,
    *,
    comparisons: Sequence[Comparison] = ("models", "methods"),
    modes: Sequence[JudgeMode] = ("full", "prediction"),
    workers: int = 8,
    progress: bool = True,
) -> list[Judgment]:
    """Judge every group without a current judgment in `out_path`; returns the current
    judgments in the file. A group is re-judged when its items or prompt changed."""
    qmap = {q.id: q for q in questions}
    groups = build_groups(
        (r for r in readings if r.question_id in qmap), comparisons, modes
    )
    existing = read_jsonl(out_path, Judgment)
    on_file: dict[JudgmentKey, list[str | None]] = defaultdict(list)
    for j in existing:
        on_file[judgment_key(j)].append(j.fingerprint)
    jobs = []
    stale = 0
    for g in groups:
        q = qmap[g.question_id]
        for judge in judges:
            fps = on_file.get(g.key(judge))
            if fps and any(is_current(f, group_fingerprint(q, g, judge)) for f in fps):
                continue
            stale += bool(fps)
            jobs.append((g.key(judge), partial(judge_group, q, g, judge, client)))
    if stale:
        console.print(
            f"[yellow]Re-judging {stale} groups whose items or prompt changed."
        )
    if not jobs:
        console.print(f"Judging: nothing to do ({len(existing)} judgments on file).")
    run_grid(
        jobs,
        client,
        on_result=lambda j: append_jsonl(out_path, j),
        workers=workers,
        progress=progress,
        description="judging",
    )
    return current_judgments(read_jsonl(out_path, Judgment))
