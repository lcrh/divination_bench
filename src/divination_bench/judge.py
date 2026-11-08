"""Anonymised ranking of readings by LLM judges."""

from __future__ import annotations

import hashlib
import json
import random
import re
import threading
from collections import defaultdict
from collections.abc import Iterable, Sequence
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path

from rich.console import Console
from rich.progress import BarColumn, MofNCompleteColumn, Progress, TextColumn

from .llm import BudgetExceededError, LLMClient
from .prompts_judge import judge_messages, retry_message
from .schemas import (
    Comparison,
    JudgeMode,
    Judgment,
    Method,
    Question,
    RankedItem,
    Reading,
)
from .store import append_jsonl, now_iso, read_jsonl

LABELS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
MAX_RETRIES = 2
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
    """A set of readings ranked against each other in one judge call."""

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
    """Deterministic per-(group, judge) shuffle so position bias averages out across judges."""
    seed_str = "|".join(str(x) for x in group.key(judge))
    rng = random.Random(int(hashlib.sha256(seed_str.encode()).hexdigest(), 16))
    items = list(group.readings)
    rng.shuffle(items)
    return dict(zip(LABELS, items, strict=False))


class JudgeParseError(ValueError):
    pass


_FENCE = re.compile(r"```(?:json)?\s*(.*?)```", re.DOTALL)
_LABEL = re.compile(r"^\[?\s*(?:item\s+)?([A-Z])\s*\]?$", re.IGNORECASE)


def _extract_json(text: str) -> dict:
    candidates = [m.group(1) for m in _FENCE.finditer(text)] + [text]
    decoder = json.JSONDecoder()
    for cand in candidates:
        for start in (i for i, ch in enumerate(cand) if ch == "{"):
            try:
                obj, _ = decoder.raw_decode(cand, start)
            except json.JSONDecodeError:
                continue
            if isinstance(obj, dict) and "ranking" in obj:
                return obj
    raise JudgeParseError("no JSON object with a 'ranking' key found")


def parse_ranking(text: str, labels: Sequence[str]) -> list[RankedItem]:
    obj = _extract_json(text)
    entries = obj["ranking"]
    if not isinstance(entries, list):
        raise JudgeParseError("'ranking' is not a list")
    items: dict[str, RankedItem] = {}
    for e in entries:
        if not isinstance(e, dict):
            raise JudgeParseError("ranking entries must be objects")
        m = _LABEL.match(str(e.get("label", "")).strip())
        label = m.group(1).upper() if m else None
        if label not in labels:
            raise JudgeParseError(f"unknown label {e.get('label')!r}")
        if label in items:
            raise JudgeParseError(f"label {label} ranked twice")
        try:
            rank, score = int(e["rank"]), float(e["score"])
        except (KeyError, TypeError, ValueError) as exc:
            raise JudgeParseError(f"bad rank/score for {label}: {exc}") from exc
        if not 0 <= score <= 10:
            raise JudgeParseError(f"score {score} for {label} outside 0-10")
        items[label] = RankedItem(
            label=label, rank=rank, score=score, rationale=str(e.get("rationale", ""))
        )
    missing = [lab for lab in labels if lab not in items]
    if missing:
        raise JudgeParseError(f"missing labels {missing}")
    if sorted(i.rank for i in items.values()) != list(range(1, len(labels) + 1)):
        raise JudgeParseError(f"ranks must be 1..{len(labels)} without ties")
    return sorted(items.values(), key=lambda i: i.rank)


def _merge_usage(usages: list[dict | None]) -> dict | None:
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


def judge_group(
    question: Question,
    group: JudgeGroup,
    judge: str,
    client: LLMClient,
    *,
    temperature: float = 0.0,
    max_tokens: int = 16000,
) -> Judgment:
    items = assign_labels(group, judge)
    labels = list(items)
    messages = judge_messages(question, items, group.mode)
    usages: list[dict | None] = []
    error = ""
    for _ in range(MAX_RETRIES + 1):
        result = client.chat(
            judge, messages, temperature=temperature, max_tokens=max_tokens
        )
        usages.append(result.usage)
        try:
            ranking = parse_ranking(result.text, labels)
        except JudgeParseError as exc:
            error = str(exc)
            messages = messages + [
                {"role": "assistant", "content": result.text},
                retry_message(error, labels),
            ]
            continue
        return Judgment(
            question_id=group.question_id,
            comparison=group.comparison,
            judge_model=judge,
            mode=group.mode,
            seed=group.seed,
            fixed_method=group.fixed_method,
            fixed_model=group.fixed_model,
            label_map={lab: reading_key(r) for lab, r in items.items()},
            ranking=ranking,
            raw_response=result.text,
            usage=_merge_usage(usages),
            created_at=now_iso(),
        )
    raise JudgeParseError(
        f"{judge} gave invalid output {MAX_RETRIES + 1} times: {error}"
    )


def run_judging(
    questions: Sequence[Question],
    readings: Sequence[Reading],
    judges: Sequence[str],
    client: LLMClient,
    out_path: str | Path,
    *,
    comparisons: Sequence[Comparison] = ("models", "methods"),
    modes: Sequence[JudgeMode] = ("full", "prediction"),
    temperature: float = 0.0,
    max_tokens: int = 16000,
    workers: int = 8,
    progress: bool = True,
) -> list[Judgment]:
    """Judge every group not yet in `out_path`; returns all judgments in the file."""
    qmap = {q.id: q for q in questions}
    groups = build_groups(
        (r for r in readings if r.question_id in qmap), comparisons, modes
    )
    done = {judgment_key(j) for j in read_jsonl(out_path, Judgment)}
    todo = [(g, j) for g in groups for j in judges if g.key(j) not in done]
    if not todo:
        console.print(f"Judging: nothing to do ({len(done)} judgments on file).")
        return read_jsonl(out_path, Judgment)

    stop = threading.Event()
    failures: list[str] = []

    def work(group: JudgeGroup, judge: str) -> None:
        if stop.is_set():
            return
        j = judge_group(
            qmap[group.question_id],
            group,
            judge,
            client,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        append_jsonl(out_path, j)

    with (
        Progress(
            TextColumn("[bold]Judging"),
            BarColumn(),
            MofNCompleteColumn(),
            TextColumn("${task.fields[spent]:.2f} spent"),
            console=console,
            disable=not progress,
        ) as bar,
        ThreadPoolExecutor(max_workers=workers) as pool,
    ):
        task = bar.add_task("judge", total=len(todo), spent=client.spent_usd)
        futures = {pool.submit(work, g, j): (g, j) for g, j in todo}
        for fut in as_completed(futures):
            g, j = futures[fut]
            if fut.cancelled():
                continue
            try:
                fut.result()
            except BudgetExceededError as exc:
                if not stop.is_set():
                    console.print(f"[red]{exc}; stopping judging.")
                stop.set()
                for f in futures:
                    f.cancel()
            except Exception as exc:  # noqa: BLE001 - one bad group must not kill the run
                failures.append(f"{g.key(j)}: {exc}")
                console.print(f"[yellow]Judge failed for {g.key(j)}: {exc}")
            bar.update(task, advance=1, spent=client.spent_usd)

    if failures:
        console.print(f"[yellow]{len(failures)} judge calls failed (rerun to retry).")
    return read_jsonl(out_path, Judgment)
