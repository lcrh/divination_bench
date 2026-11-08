"""Run the generation grid: questions x methods x seeds x models."""

from __future__ import annotations

import logging
import threading
from collections.abc import Callable, Iterable
from concurrent.futures import Future, ThreadPoolExecutor, as_completed
from contextlib import nullcontext
from functools import partial
from pathlib import Path

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
from .store import append_jsonl, now_iso, read_jsonl

log = logging.getLogger(__name__)

PARSE_ATTEMPTS = 3

ReadingKey = tuple[str, str, int, str]


def reading_key(r: Reading) -> ReadingKey:
    return (r.question_id, str(r.method), r.seed, r.model)


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
    for _ in range(PARSE_ATTEMPTS):
        result = client.chat(
            model, messages, temperature=temperature, max_tokens=max_tokens
        )
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
            usage=result.usage,
            created_at=now_iso(),
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
    results: list[T] = []

    def guarded(fn: Callable[[], T]) -> T | None:
        if stop.is_set():
            return None
        return fn()

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
                if not stop.is_set():
                    log.warning("%s; stopping after in-flight requests finish", e)
                    stop.set()
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
    """Generate every missing reading and return all readings in the grid (old and new)."""
    questions = list(questions)
    methods = [Method(m) for m in methods]
    existing = read_jsonl(out_path, Reading)
    done = {reading_key(r) for r in existing}
    grid: set[ReadingKey] = set()
    jobs: list[tuple[ReadingKey, Callable[[], Reading]]] = []
    for q in questions:
        for method in methods:
            for seed in seeds:
                for model in models:
                    key = (q.id, str(method), seed, model)
                    grid.add(key)
                    if key in done:
                        continue
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
    new = run_grid(
        jobs,
        client,
        on_result=lambda r: append_jsonl(out_path, r),
        workers=workers,
        progress=progress,
        description="generating",
    )
    return [r for r in existing if reading_key(r) in grid] + new
