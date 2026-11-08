"""Knowledge-cutoff check: does a tested model already know how an event turned out?"""

from __future__ import annotations

import json
import re
from functools import partial
from pathlib import Path

from .generate import run_grid
from .llm import LLMClient
from .prompts_generation import normalize_answer
from .schemas import KnowledgeProbe, Question
from .store import append_jsonl, now_iso, read_jsonl

PARSE_ATTEMPTS = 3

PROBE_SYSTEM = """\
[[MOCK:probe]]
You are being tested on what you already know from your training data. Answer from memory \
only; do not speculate or forecast. If you do not actually remember how the event turned \
out, say so.

Reply with a single JSON object and nothing else:
{"knows_outcome": "yes" | "no" | "unsure", "stated_answer": string or null, \
"training_cutoff_guess": string}
- knows_outcome: "yes" only if you remember the actual outcome.
- stated_answer: the outcome as you remember it (one of the options, if options are given), \
or null if you do not know.
- training_cutoff_guess: your best guess of your training data cutoff, e.g. "2026-03"."""

CUTOFF_PROMPT = """\
What is the cutoff month of your training data (YYYY-MM)? And what is the most recent \
major news event you know about, with its date? Answer in two or three sentences."""


def build_probe_messages(question: Question) -> list[dict]:
    parts = [
        f"Event: {question.title}",
        f"Question: {question.question}",
        f"This was decided around {question.event_date:%B %Y}.",
    ]
    if question.options:
        parts.append("Options: " + "; ".join(question.options))
    parts.append("Do you know what actually happened?")
    return [
        {"role": "system", "content": PROBE_SYSTEM},
        {"role": "user", "content": "\n".join(parts)},
    ]


def parse_probe(text: str) -> dict:
    cleaned = re.sub(r"```(?:json)?", "", text)
    start, end = cleaned.find("{"), cleaned.rfind("}")
    if start < 0 or end <= start:
        raise ValueError("no JSON object in probe response")
    data = json.loads(cleaned[start : end + 1])
    knows = str(data.get("knows_outcome", "")).strip().lower()
    if knows not in ("yes", "no", "unsure"):
        knows = "unsure"
    stated = data.get("stated_answer")
    stated = str(stated).strip() if stated not in (None, "") else None
    if stated is not None and stated.lower() in ("null", "none"):
        stated = None
    return {
        "knows_outcome": knows,
        "stated_answer": stated,
        "training_cutoff_guess": data.get("training_cutoff_guess"),
    }


def _is_correct(question: Question, stated: str | None) -> bool | None:
    if question.question_type == "open" or stated is None:
        return None
    matched = normalize_answer(stated, question.options) or stated
    return matched.casefold() == question.resolved_answer.casefold()


def probe_one(question: Question, model: str, client: LLMClient) -> KnowledgeProbe:
    messages = build_probe_messages(question)
    last_error: Exception | None = None
    for _ in range(PARSE_ATTEMPTS):
        result = client.chat(model, messages, temperature=0.0, max_tokens=4000)
        try:
            parsed = parse_probe(result.text)
        except (ValueError, json.JSONDecodeError) as e:
            last_error = e
            continue
        return KnowledgeProbe(
            question_id=question.id,
            model=model,
            knows_outcome=parsed["knows_outcome"],
            stated_answer=parsed["stated_answer"],
            correct=_is_correct(question, parsed["stated_answer"]),
            raw_response=result.text,
            usage=result.usage,
            created_at=now_iso(),
        )
    raise ValueError(f"unparseable probe output: {last_error}")


def run_probes(
    questions: list[Question],
    models: list[str],
    client: LLMClient,
    out_path: str | Path,
    *,
    workers: int = 8,
    progress: bool = True,
) -> list[KnowledgeProbe]:
    """Probe every missing (question, model) pair; return all probes in the grid."""
    existing = read_jsonl(out_path, KnowledgeProbe)
    done = {(p.question_id, p.model) for p in existing}
    grid = {(q.id, m) for q in questions for m in models}
    jobs = [
        ((q.id, m), partial(probe_one, q, m, client))
        for q in questions
        for m in models
        if (q.id, m) not in done
    ]
    new = run_grid(
        jobs,
        client,
        on_result=lambda p: append_jsonl(out_path, p),
        workers=workers,
        progress=progress,
        description="probing",
    )
    return [p for p in existing if (p.question_id, p.model) in grid] + new


def probe_cutoff(model: str, client: LLMClient) -> str:
    result = client.chat(
        model,
        [{"role": "user", "content": CUTOFF_PROMPT}],
        temperature=0.0,
        max_tokens=4000,
    )
    return result.text
