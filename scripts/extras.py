"""Side experiments on a finished run, written to <run>/extras/. Resumable.

uv run python scripts/extras.py results/pilot counterfactuals   # Claude writes a fake outcome per question
uv run python scripts/extras.py results/pilot coldread          # Jev: real vs fake outcome, per text
uv run python scripts/extras.py results/pilot changed           # Jev: did the cards change the forecast?
"""

from __future__ import annotations

import json
import sys
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from divination_bench.llm import LLMClient
from divination_bench.questions import load_questions
from divination_bench.store import append_line

RUN = Path(sys.argv[1])
TASK = sys.argv[2]
BUDGET = float(sys.argv[3]) if len(sys.argv) > 3 else 6.0
OUT = RUN / "extras"
OUT.mkdir(exist_ok=True)
JEV = "typesafe/jev-1.13"
WRITER = "anthropic/claude-opus-5.5"

questions = {q.id: q for q in load_questions("data/questions")}
client = LLMClient(budget_usd=BUDGET, ledger_path=OUT / "spend.jsonl")
client.spent_usd = (
    sum(json.loads(x)["cost"] for x in (OUT / "spend.jsonl").open())
    if (OUT / "spend.jsonl").exists()
    else 0.0
)
lock = threading.Lock()


def load(path: Path) -> dict:
    out = {}
    if path.exists():
        for line in path.open():
            r = json.loads(line)
            out[r["key"]] = r
    return out


def readings() -> dict:
    out = {}
    for line in (RUN / "readings.jsonl").open():
        r = json.loads(line)
        out[(r["question_id"], r["method"], r["seed"], r["model"])] = r
    return out


def run_all(jobs, fn, path: Path):
    done = load(path)
    todo = [j for j in jobs if j[0] not in done]
    print(f"{len(done)} done, {len(todo)} to do; spent so far ${client.spent_usd:.2f}")

    def work(job):
        try:
            rec = fn(*job[1:])
        except Exception as e:  # noqa: BLE001
            print("FAILED", job[0], repr(e)[:200])
            return
        rec["key"] = job[0]
        with lock:
            append_line(path, json.dumps(rec))

    with ThreadPoolExecutor(32) as ex:
        list(ex.map(work, todo))
    print(f"spent ${client.spent_usd:.2f}")


CF_PROMPT = """You are helping build a control condition for a forecasting evaluation.

Question (asked before the event): {question}

Background known beforehand:
{context}

What actually happened:
{outcome}

Write a counterfactual account of what happened: an outcome that was genuinely plausible beforehand but differs clearly from reality on the main point the question asks about (a different winner, result, product, finding, number, or turn of events, as appropriate). Match the real account's length, level of detail, tone and style, and make it neither more nor less dramatic or surprising than the real one. Use only names and facts that were known beforehand, plus invented details of the same kind the real account contains. Write it as a plain factual account, with no hint that it is counterfactual. Output only the account."""


def counterfactual(qid):
    q = questions[qid]
    res = client.chat(
        WRITER,
        [
            {
                "role": "user",
                "content": CF_PROMPT.format(
                    question=q.question.strip(),
                    context=q.context_summary.strip(),
                    outcome=q.outcome_summary.strip(),
                ),
            }
        ],
        max_tokens=4000,
    )
    return {"question_id": qid, "counterfactual": res.text.strip()}


COLD_INSTRUCTIONS = (
    "The text below was written about this situation before the event. Exactly one of the two "
    "accounts is what really happened; the other is a plausible alternative that did not happen. "
    "Which account does the text describe better?"
)


def coldread(qid, text, real_first):
    q = questions[qid]
    cf = cfs[qid]["counterfactual"]
    accounts = (
        {"A": q.outcome_summary.strip(), "B": cf}
        if real_first
        else {"A": cf, "B": q.outcome_summary.strip()}
    )
    state = {
        "question": q.question.strip(),
        "text_written_beforehand": text,
        "account A": accounts["A"],
        "account B": accounts["B"],
    }
    qs = {
        "match": {
            "type": "choice",
            "instructions": COLD_INSTRUCTIONS,
            "criteria": {
                lab: f"The text describes account {lab} better than the other account."
                for lab in "AB"
            },
        }
    }
    a = client.decide(JEV, state, qs).answers["match"]
    real = "A" if real_first else "B"
    return {"p_real": a["probabilities"][real], "choice_real": a["choice"] == real}


CHANGED_INSTRUCTIONS = (
    "Two forecasts were made for the same question. Do they predict substantially the same "
    "outcome on the main point the question asks about, or materially different outcomes?"
)


def changed(qid, plain, divined):
    q = questions[qid]
    state = {"question": q.question.strip(), "forecast 1": plain, "forecast 2": divined}
    qs = {
        "changed": {
            "type": "choice",
            "instructions": CHANGED_INSTRUCTIONS,
            "criteria": {
                "same": "The two forecasts predict substantially the same outcome.",
                "different": "The two forecasts predict materially different outcomes.",
            },
        }
    }
    a = client.decide(JEV, state, qs).answers["changed"]
    return {"p_different": a["probabilities"]["different"]}


CALLED_INSTRUCTIONS = (
    "A text was written about this question before the event. Judge only the headline: did the "
    "text call the main thing that happened (who or what won, what was decided or revealed, which "
    "way it went), as stated in the resolved answer? Exact numbers, margins, dates and secondary "
    "details do not matter. A text that makes no clear call on the headline did not call it."
)


def called(qid, text, yes_first):
    q = questions[qid]
    state = {
        "question": q.question.strip(),
        "resolved_answer": q.resolved_answer,
        "what_actually_happened": q.outcome_summary.strip(),
        "text_written_beforehand": text,
    }
    crit = {
        "right": "The text called the headline outcome.",
        "wrong": "The text called a different headline outcome, or made no clear call.",
    }
    if not yes_first:
        crit = dict(reversed(list(crit.items())))
    qs = {
        "called": {
            "type": "choice",
            "instructions": CALLED_INSTRUCTIONS,
            "criteria": crit,
        }
    }
    a = client.decide(JEV, state, qs).answers["called"]
    return {"p_right": a["probabilities"]["right"]}


if TASK == "called":
    jobs = []
    for (qid, method, seed, model), r in readings().items():
        text = r["reading"] if method.endswith("_reading") else r["prediction"]
        if text:
            for yes_first in (True, False):
                jobs.append(
                    (
                        f"{qid}|{method}|{seed}|{model}|{int(yes_first)}",
                        qid,
                        text,
                        yes_first,
                    )
                )
    run_all(jobs, called, OUT / "called.jsonl")

if TASK == "counterfactuals":
    run_all(
        [(qid, qid) for qid in questions], counterfactual, OUT / "counterfactuals.jsonl"
    )

elif TASK == "coldread":
    cfs = load(OUT / "counterfactuals.jsonl")
    jobs = []
    for (qid, method, seed, model), r in readings().items():
        if qid not in cfs:
            continue
        text = r["reading"] if method.endswith("_reading") else r["prediction"]
        if not text:
            continue
        for real_first in (True, False):
            key = f"{qid}|{method}|{seed}|{model}|{int(real_first)}"
            jobs.append((key, qid, text, real_first))
    run_all(jobs, coldread, OUT / "coldread.jsonl")

elif TASK == "coldread-control":
    # The background every forecast was given: what "knowing only the prior" scores.
    cfs = load(OUT / "counterfactuals.jsonl")
    jobs = [
        (
            f"{qid}|{int(real_first)}",
            qid,
            questions[qid].context_summary.strip(),
            real_first,
        )
        for qid in cfs
        for real_first in (True, False)
    ]
    run_all(jobs, coldread, OUT / "coldread-control.jsonl")

elif TASK == "changed":
    rs = readings()
    jobs = []
    for (qid, method, seed, model), r in rs.items():
        p = rs.get((qid, "predict", seed, model))
        if method in ("tarot", "iching") and p:
            jobs.append(
                (
                    f"{qid}|{method}|{seed}|{model}",
                    qid,
                    p["prediction"],
                    r["prediction"],
                )
            )
    run_all(jobs, changed, OUT / "changed.jsonl")
