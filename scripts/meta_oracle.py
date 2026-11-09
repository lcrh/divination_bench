"""Ask the oracles about the benchmark itself. Writes <run>/extras/meta_oracle.jsonl.

uv run python scripts/meta_oracle.py results/pilot
"""

import sys
from datetime import date
from pathlib import Path

from divination_bench.generate import generate_one
from divination_bench.llm import LLMClient
from divination_bench.schemas import Method, Question
from divination_bench.store import append_line

RUN = Path(sys.argv[1])
OUT = RUN / "extras"
OUT.mkdir(exist_ok=True)

src = {
    "url": "https://github.com/lcrh/divination_bench",
    "title": "divination_bench",
    "publisher": "GitHub",
    "published_date": date(2026, 11, 8),
}
q = Question(
    id="divination-bench-itself-2026",
    domain="science",
    title="Does divination beat plain forecasting on divination_bench?",
    question=(
        "divination_bench asks Claude Opus 5.5 and GPT-6 Astra to forecast 40 real events from "
        "autumn 2026 three ways: from a Thoth tarot spread, from an I Ching cast, and by plain "
        "reasoning. A judge model ranks the forecasts against what really happened. Which method "
        "will come out on top, which model will divine better, and what will the results reveal?"
    ),
    question_type="open",
    resolution_criteria="The benchmark's final results.",
    context_summary=(
        "The 40 questions span elections, courts, sport, science, business, culture and internet "
        "mysteries, all resolved after the models' training cutoffs. Each model gives the reading "
        "and a concrete forecast. The judge, TypeSafe Jev, ranks forecasts by accuracy against the "
        "outcome and by precision, over six seeds with distinct casts."
    ),
    context_sources=[src],
    event_date=date(2026, 11, 9),
    outcome_summary="(see README)",
    resolved_answer="(see README)",
    outcome_sources=[src],
)

client = LLMClient(budget_usd=3, ledger_path=OUT / "spend.jsonl")
for model in ("anthropic/claude-opus-5.5", "openai/gpt-6-astra"):
    for method in (Method.tarot, Method.iching):
        r = generate_one(q, method, 0, model, client)
        append_line(OUT / "meta_oracle.jsonl", r.model_dump_json())
        print(
            f"\n===== {model} {method}\n{r.cast_text.split(chr(10) * 2)[0]}\n\n{r.reading}\n\nPREDICTION: {r.prediction}"
        )
print(f"spent ${client.spent_usd:.2f}")
