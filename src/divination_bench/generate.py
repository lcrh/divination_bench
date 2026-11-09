"""Run the generation grid: questions x methods x seeds x models."""

from __future__ import annotations

import logging
import threading
from collections.abc import Callable, Iterable
from concurrent.futures import Future, ThreadPoolExecutor, as_completed
from contextlib import nullcontext
from functools import partial
from pathlib import Path

from rich.console import Console
from rich.progress import (
    BarColumn,
    MofNCompleteColumn,
    Progress,
    TextColumn,
    TimeElapsedColumn,
)

from .divination import cast
from .llm import BudgetExceededError, LLMClient
from .prompts_generation import build_generation_messages, parse_generation
from .schemas import Method, Question, Reading
from .store import (
    append_jsonl,
    fingerprint,
    is_current,
    merge_usage,
    now_iso,
    read_jsonl,
)

log = logging.getLogger(__name__)
console = Console(stderr=True)

PARSE_ATTEMPTS = 3

ReadingKey = tuple[str, str, int, str]


def reading_key(r: Reading) -> ReadingKey:
    return (r.question_id, str(r.method), r.seed, r.model)


def current_readings(readings: Iterable[Reading]) -> list[Reading]:
    """The latest reading per (question, method, seed, model)."""
    return list({reading_key(r): r for r in readings}.values())


def _messages(question: Question, method: Method, seed: int) -> list[dict]:
    _, cast_text = cast(question.id, method, seed)
    return build_generation_messages(question, method, cast_text)


def reading_fingerprint(
    question: Question, method: Method, seed: int, model: str
) -> str:
    return fingerprint(model, _messages(question, method, seed))


def generate_one(
    question: Question,
    method: Method,
    seed: int,
    model: str,
    client: LLMClient,
    *,
    temperature: float = 1.0,
    max_tokens: int = 16000,
) -> Reading:
    """One reading; retries the call on unparseable output, then re-raises ValueError."""
    cast_data, cast_text = cast(question.id, method, seed)
    messages = build_generation_messages(question, method, cast_text)
    last_error: ValueError | None = None
    usages: list[dict | None] = []
    for _ in range(PARSE_ATTEMPTS):
        result = client.chat(
            model, messages, temperature=temperature, max_tokens=max_tokens
        )
        usages.append(result.usage)
        try:
            parsed = parse_generation(result.text, question, method)
        except ValueError as e:
            last_error = e
            continue
        return Reading(
            question_id=question.id,
            method=method,
            seed=seed,
            model=model,
            cast=cast_data,
            cast_text=cast_text,
            raw_response=result.text,
            usage=result.usage if len(usages) == 1 else merge_usage(usages),
            created_at=now_iso(),
            fingerprint=fingerprint(model, messages),
            **parsed,
        )
    raise ValueError(
        f"unparseable output after {PARSE_ATTEMPTS} attempts: {last_error}"
    )


def run_grid[K, T](
    jobs: list[tuple[K, Callable[[], T]]],
    client: LLMClient,
    *,
    on_result: Callable[[T], None],
    workers: int,
    progress: bool,
    description: str,
) -> list[T]:
    """Run jobs concurrently; log and skip failures, stop scheduling on budget exhaustion."""
    stop = threading.Event()
    budget_logged = False
    results: list[T] = []

    def guarded(fn: Callable[[], T]) -> T | None:
        if stop.is_set():
            return None
        try:
            return fn()
        except BudgetExceededError:
            stop.set()
            raise

    bar = (
        Progress(
            TextColumn("[bold]{task.description}"),
            BarColumn(),
            MofNCompleteColumn(),
            TimeElapsedColumn(),
            TextColumn("spent ${task.fields[cost]:.2f}"),
        )
        if progress
        else None
    )
    with bar or nullcontext(), ThreadPoolExecutor(max_workers=workers) as pool:
        task = bar.add_task(description, total=len(jobs), cost=0.0) if bar else None
        futures: dict[Future, K] = {pool.submit(guarded, fn): key for key, fn in jobs}
        for fut in as_completed(futures):
            key = futures[fut]
            try:
                value = fut.result()
            except BudgetExceededError as e:
                if not budget_logged:
                    budget_logged = True
                    log.warning("%s; stopping after in-flight requests finish", e)
                    for f in futures:
                        f.cancel()
                value = None
            except Exception as e:  # noqa: BLE001 - one bad call must not end the run
                log.error("skipping %s: %s: %s", key, type(e).__name__, e)
                value = None
            if value is not None:
                on_result(value)
                results.append(value)
            if bar is not None:
                bar.update(task, advance=1, cost=client.spent_usd)
    return results


def run_generation(
    questions: Iterable[Question],
    models: list[str],
    methods: list[Method],
    seeds: list[int],
    client: LLMClient,
    out_path: str | Path,
    *,
    temperature: float = 1.0,
    max_tokens: int = 16000,
    workers: int = 8,
    progress: bool = True,
) -> list[Reading]:
    """Generate every missing or stale reading and return the current readings in the
    grid (old and new). A reading is stale when its prompt changed, e.g. the question
    was edited after it was generated."""
    questions = list(questions)
    methods = [Method(m) for m in methods]
    latest = {reading_key(r): r for r in read_jsonl(out_path, Reading)}
    grid: list[ReadingKey] = []
    jobs: list[tuple[ReadingKey, Callable[[], Reading]]] = []
    stale = 0
    for q in questions:
        for method in methods:
            for seed in seeds:
                for model in models:
                    key = (q.id, str(method), seed, model)
                    grid.append(key)
                    prev = latest.get(key)
                    if prev is not None:
                        fp = reading_fingerprint(q, method, seed, model)
                        if is_current(prev.fingerprint, fp):
                            continue
                        stale += 1
                    fn = partial(
                        generate_one,
                        q,
                        method,
                        seed,
                        model,
                        client,
                        temperature=temperature,
                        max_tokens=max_tokens,
                    )
                    jobs.append((key, fn))
    if stale:
        console.print(f"[yellow]Regenerating {stale} readings whose prompt changed.")
    new = run_grid(
        jobs,
        client,
        on_result=lambda r: append_jsonl(out_path, r),
        workers=workers,
        progress=progress,
        description="generating",
    )
    latest.update((reading_key(r), r) for r in new)
    return [latest[k] for k in grid if k in latest]
