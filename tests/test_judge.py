from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import pytest

from divination_bench.judge import (
    JudgeParseError,
    assign_labels,
    build_groups,
    judge_group,
    judgment_key,
    parse_ranking,
    run_judging,
)
from divination_bench.llm import BudgetExceededError, ChatResult, LLMClient
from divination_bench.prompts_judge import judge_messages
from divination_bench.schemas import Judgment, Method, Question, Reading, Source
from divination_bench.store import read_jsonl

MODELS = ["mock/alpha", "mock/beta"]
JUDGES = ["mock/alpha", "mock/beta", "mock/gamma"]


def make_question(qid: str = "q1", domain: str = "politics") -> Question:
    src = Source(
        url="https://example.com",
        title="Preview",
        publisher="Example",
        published_date=date(2026, 10, 1),
        excerpt="Polls are tight.",
    )
    out = src.model_copy(
        update={
            "title": "Result",
            "published_date": date(2026, 10, 6),
            "excerpt": "Yes won.",
        }
    )
    return Question(
        id=qid,
        domain=domain,
        title=f"Title {qid}",
        question=f"Will it happen ({qid})?",
        question_type="binary",
        options=["Yes", "No"],
        resolution_criteria="Official result.",
        context_summary="Background known before the event.",
        context_sources=[src],
        event_date=date(2026, 10, 5),
        outcome_summary="It happened, 52-48.",
        resolved_answer="Yes",
        outcome_sources=[out],
    )


def make_reading(
    qid: str, method: str, seed: int, model: str, answer: str = "Yes"
) -> Reading:
    divines = method != "predict"
    return Reading(
        question_id=qid,
        method=Method(method),
        seed=seed,
        model=model,
        reading=f"Reading by {model} via {method}" if divines else None,
        prediction=f"Prediction by {model}, seed {seed}",
        answer=answer,
        raw_response="",
        usage={"cost": 0.01},
        created_at="2026-11-01T00:00:00+00:00",
    )


def make_readings(qids=("q1",), seeds=(0, 1)) -> list[Reading]:
    return [
        make_reading(q, m, s, model)
        for q in qids
        for m in ("tarot", "iching", "predict")
        for s in seeds
        for model in MODELS
    ]


def test_build_groups_counts_and_membership():
    groups = build_groups(make_readings())
    by_kind: dict[tuple[str, str], list] = {}
    for g in groups:
        by_kind.setdefault((g.comparison, g.mode), []).append(g)
    # models: per (seed, method); full skips predict
    assert len(by_kind[("models", "prediction")]) == 2 * 3
    assert len(by_kind[("models", "full")]) == 2 * 2
    assert all(g.fixed_method != Method.predict for g in by_kind[("models", "full")])
    # methods: per (seed, model)
    assert len(by_kind[("methods", "prediction")]) == 2 * 2
    assert len(by_kind[("methods", "full")]) == 2 * 2
    for g in by_kind[("methods", "prediction")]:
        assert {r.method for r in g.readings} == set(Method)
        assert {r.model for r in g.readings} == {g.fixed_model}
    for g in by_kind[("methods", "full")]:
        assert {r.method for r in g.readings} == {Method.tarot, Method.iching}


def test_build_groups_skips_singletons_and_filters():
    readings = [make_reading("q1", "tarot", 0, "mock/alpha")]
    assert build_groups(readings) == []
    groups = build_groups(
        make_readings(), comparisons=("methods",), modes=("prediction",)
    )
    assert {(g.comparison, g.mode) for g in groups} == {("methods", "prediction")}


def test_build_groups_dedupes_latest_reading():
    rs = make_readings(seeds=(0,))
    newer = make_reading("q1", "tarot", 0, "mock/alpha").model_copy(
        update={"prediction": "newer"}
    )
    groups = build_groups(rs + [newer], comparisons=("models",), modes=("prediction",))
    tarot = next(g for g in groups if g.fixed_method == Method.tarot)
    assert len(tarot.readings) == 2
    assert "newer" in {r.prediction for r in tarot.readings}


def test_labels_deterministic_and_vary_by_judge():
    groups = build_groups(make_readings(seeds=tuple(range(10))))
    for g in groups:
        a1 = assign_labels(g, "mock/alpha")
        assert a1 == assign_labels(g, "mock/alpha")
        assert list(a1) == list("ABC"[: len(g.readings)])
        assert set(map(id, a1.values())) == set(map(id, g.readings))
    orders = {
        tuple(r.model for r in assign_labels(g, j).values())
        for g in groups
        if g.comparison == "models"
        for j in JUDGES
    }
    assert len(orders) > 1


def test_prediction_prompt_hides_method_and_reading():
    q = make_question()
    g = next(
        g
        for g in build_groups(make_readings())
        if g.comparison == "methods" and g.mode == "prediction"
    )
    items = assign_labels(g, "mock/alpha")
    msgs = judge_messages(q, items, "prediction")
    text = msgs[1]["content"]
    assert "[[MOCK:judge]]" in msgs[0]["content"]
    assert "Reading by" not in text
    assert "Chosen answer: Yes" in text
    assert "It happened, 52-48." in text and "2026-10-06" in text
    for lab in items:
        assert f"[Item {lab}]" in text
    for msg in msgs:
        assert "tarot" not in msg["content"].lower()
        assert "ching" not in msg["content"].lower()

    full = next(g for g in build_groups(make_readings()) if g.mode == "full")
    text = judge_messages(q, assign_labels(full, "mock/alpha"), "full")[1]["content"]
    assert "Reading by" in text


def test_parse_ranking_variants():
    text = (
        "Sure!\n```json\n"
        + json.dumps(
            {
                "ranking": [
                    {"label": "Item B", "rank": 1, "score": 8, "rationale": "right"},
                    {"label": "[A]", "rank": 2, "score": 3.5, "rationale": "wrong"},
                ]
            }
        )
        + "\n```"
    )
    ranking = parse_ranking(text, ["A", "B"])
    assert [(r.label, r.rank, r.score) for r in ranking] == [
        ("B", 1, 8.0),
        ("A", 2, 3.5),
    ]
    bare = 'prefix {"note": 1} {"ranking": [{"label": "a", "rank": 2, "score": 1}, {"label": "B", "rank": 1, "score": 9}]}'
    assert [r.label for r in parse_ranking(bare, ["A", "B"])] == ["B", "A"]


@pytest.mark.parametrize(
    "payload",
    [
        "no json here",
        '{"ranking": [{"label": "A", "rank": 1, "score": 5}]}',
        '{"ranking": [{"label": "A", "rank": 1, "score": 5}, {"label": "B", "rank": 1, "score": 4}]}',
        '{"ranking": [{"label": "A", "rank": 1, "score": 5}, {"label": "C", "rank": 2, "score": 4}]}',
        '{"ranking": [{"label": "A", "rank": 1, "score": 15}, {"label": "B", "rank": 2, "score": 4}]}',
    ],
)
def test_parse_ranking_rejects_invalid(payload):
    with pytest.raises(JudgeParseError):
        parse_ranking(payload, ["A", "B"])


class ScriptedClient:
    """Returns queued responses; records calls."""

    def __init__(self, responses: list[str], cost: float = 0.5):
        self.responses = list(responses)
        self.calls: list[list[dict]] = []
        self.spent_usd = 0.0
        self.cost = cost

    def chat(self, model, messages, **kwargs) -> ChatResult:
        self.calls.append(messages)
        self.spent_usd += self.cost
        return ChatResult(
            self.responses.pop(0), {"cost": self.cost, "prompt_tokens": 10}, model
        )


def test_judge_group_retries_then_succeeds():
    q = make_question()
    g = next(g for g in build_groups(make_readings()) if g.comparison == "models")
    good = '{"ranking": [{"label": "A", "rank": 1, "score": 7, "rationale": "x"}, {"label": "B", "rank": 2, "score": 2, "rationale": "y"}]}'
    client = ScriptedClient(["garbage", good])
    j = judge_group(q, g, "mock/alpha", client)  # type: ignore[arg-type]
    assert len(client.calls) == 2
    assert (
        client.calls[1][-1]["role"] == "user"
        and "could not be used" in client.calls[1][-1]["content"]
    )
    assert j.usage == {"cost": 1.0, "prompt_tokens": 20, "attempts": 2}
    assert set(j.label_map.values()) == {f"{g.fixed_method}|{m}" for m in MODELS}

    client = ScriptedClient(["bad"] * 3)
    with pytest.raises(JudgeParseError):
        judge_group(q, g, "mock/alpha", client)  # type: ignore[arg-type]
    assert len(client.calls) == 3


def test_run_judging_mock_end_to_end_and_resume(tmp_path: Path):
    qs = [make_question("q1"), make_question("q2", "sports")]
    readings = make_readings(qids=("q1", "q2"))
    out = tmp_path / "judgments.jsonl"
    client = LLMClient(api_key="unused")
    js = run_judging(qs, readings, JUDGES, client, out, progress=False)
    n_groups = len(build_groups(readings))
    assert len(js) == n_groups * len(JUDGES)
    assert len({judgment_key(j) for j in js}) == len(js)
    for j in js:
        assert sorted(r.rank for r in j.ranking) == list(range(1, len(j.ranking) + 1))
        assert set(j.label_map) == {r.label for r in j.ranking}

    again = run_judging(qs, readings, JUDGES, client, out, progress=False)
    assert len(again) == len(js)
    assert len(read_jsonl(out, Judgment)) == len(js)


class BudgetClient:
    spent_usd = 0.0

    def chat(self, *a, **k):
        raise BudgetExceededError("budget")


def test_run_judging_stops_on_budget(tmp_path: Path):
    out = tmp_path / "j.jsonl"
    js = run_judging(
        [make_question()],
        make_readings(),
        JUDGES,
        BudgetClient(),
        out,
        progress=False,  # type: ignore[arg-type]
    )
    assert js == []


def test_run_judging_with_generated_readings(tmp_path: Path):
    generate = pytest.importorskip("divination_bench.generate")
    qs = [make_question("q1")]
    client = LLMClient(api_key="unused")
    readings = generate.run_generation(
        qs, MODELS, list(Method), [0], client, tmp_path / "r.jsonl", progress=False
    )
    assert len(readings) == len(MODELS) * len(Method)
    js = run_judging(qs, readings, JUDGES, client, tmp_path / "j.jsonl", progress=False)
    assert len(js) == len(build_groups(readings)) * len(JUDGES)
