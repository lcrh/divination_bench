from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import pytest

from divination_bench.judge import (
    assign_labels,
    build_groups,
    judge_group,
    judgment_key,
    parse_choice,
    pool,
    rotations,
    run_judging,
)
from divination_bench.llm import (
    BudgetExceededError,
    DecisionError,
    DecisionResult,
    LLMClient,
)
from divination_bench.prompts_judge import accuracy_request, precision_request
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


def test_requests_hide_method_and_keep_outcome_out_of_precision():
    q = make_question()
    g = next(
        g
        for g in build_groups(make_readings())
        if g.comparison == "methods" and g.mode == "prediction"
    )
    items = assign_labels(g, "mock/alpha")
    acc_state, acc_q = accuracy_request(q, items, "prediction")
    prec_state, prec_q = precision_request(q, items, "prediction")

    assert acc_q["accuracy"]["type"] == "choice"
    assert list(acc_q["accuracy"]["criteria"]) == list(items)
    assert list(prec_q["precision"]["criteria"]) == list(items)
    acc_text = json.dumps(acc_state)
    assert "It happened, 52-48." in acc_text and "2026-10-06" in acc_text
    prec_text = json.dumps(prec_state)
    assert "52-48" not in prec_text and "Yes won" not in prec_text
    assert "Background known before the event." in prec_text
    for state in (acc_state, prec_state):
        assert [k for k in state if k.startswith("forecast ")] == [
            f"forecast {lab}" for lab in items
        ]
        assert state["forecast A"]["chosen_answer"] == "Yes"
        text = json.dumps(state).lower()
        assert "reading by" not in text
        assert "tarot" not in text and "ching" not in text

    full = next(g for g in build_groups(make_readings()) if g.mode == "full")
    state, _ = accuracy_request(q, assign_labels(full, "mock/alpha"), "full")
    assert "Reading by" in json.dumps(state)


def test_parse_choice_and_pool():
    ans = {"type": "choice", "choice": "B", "probabilities": {"A": 0.2, "B": 0.6}}
    assert parse_choice(ans, ["A", "B"]) == pytest.approx({"A": 0.25, "B": 0.75})
    assert parse_choice({"type": "choice", "choice": "A"}, ["A", "B"]) == {
        "A": 1.0,
        "B": 0.0,
    }
    for bad in (
        {"type": "score", "score": 0.5},
        {"type": "choice", "choice": "C"},
        {"type": "choice", "probabilities": {"A": 1.0}},
        {"type": "choice", "probabilities": {"A": 0, "B": 0}},
    ):
        with pytest.raises(DecisionError):
            parse_choice(bad, ["A", "B"])

    pooled = pool({"A": 0.9, "B": 0.1}, {"A": 0.1, "B": 0.9})
    assert pooled == pytest.approx({"A": 0.5, "B": 0.5})
    pooled = pool({"A": 0.8, "B": 0.2}, {"A": 0.5, "B": 0.5})
    assert pooled["A"] == pytest.approx(2 / 3)
    assert rotations(["A", "B", "C"]) == [
        ["A", "B", "C"],
        ["B", "C", "A"],
        ["C", "A", "B"],
    ]


class ScriptedJudge:
    """Prefers forecasts in a fixed model order, whatever position they are shown in;
    can fail the first few calls."""

    def __init__(self, preference: list[str], fail_first: int = 0, cost: float = 0.01):
        self.preference = preference
        self.fail_first = fail_first
        self.cost = cost
        self.calls: list[tuple[dict, dict]] = []
        self.spent_usd = 0.0

    def decide(self, model, state, questions) -> DecisionResult:
        self.calls.append((state, questions))
        self.spent_usd += self.cost
        usage = {"cost": self.cost, "input_tokens": 100}
        ((key, q),) = questions.items()
        if len(self.calls) <= self.fail_first:
            return DecisionResult({key: {"type": "score"}}, usage, model, {})
        labels = list(q["criteria"])
        model_of = {
            lab: state[f"forecast {lab}"]["prediction"].split()[2].rstrip(",")
            for lab in labels
        }
        weights = {lab: 2.0 ** -self.preference.index(model_of[lab]) for lab in labels}
        total = sum(weights.values())
        probs = {lab: w / total for lab, w in weights.items()}
        best = max(probs, key=probs.__getitem__)
        answer = {"type": "choice", "choice": best, "probabilities": probs}
        return DecisionResult({key: answer}, usage, model, {"answers": {key: answer}})


def three_way_group():
    readings = [
        make_reading("q1", "tarot", 0, m)
        for m in ("mock/alpha", "mock/beta", "mock/delta")
    ]
    (g,) = build_groups(readings, comparisons=("models",), modes=("prediction",))
    return g


def test_judge_group_ranks_by_successive_choice():
    q = make_question()
    g = three_way_group()
    client = ScriptedJudge(["mock/delta", "mock/alpha", "mock/beta"])
    j = judge_group(q, g, "mock/jev", client)  # type: ignore[arg-type]

    # round 1: 3 rotations x (accuracy, precision); round 2: 2 x 2
    assert len(client.calls) == 3 * 2 + 2 * 2
    ranked = [j.label_map[r.label].split("|")[1] for r in j.ranking]
    assert ranked == ["mock/delta", "mock/alpha", "mock/beta"]
    assert [r.rank for r in j.ranking] == [1, 2, 3]
    assert [r.score for r in j.ranking] == pytest.approx([4 / 7, 2 / 7, 1 / 7])
    assert sum(r.p_accuracy for r in j.ranking) == pytest.approx(1)
    assert j.usage == {"cost": pytest.approx(0.1), "input_tokens": 1000, "attempts": 10}
    assert len(json.loads(j.raw_response)) == 10
    # every forecast was shown in every position in the first round
    first = [next(iter(qs.values()))["criteria"] for _, qs in client.calls[:6:2]]
    assert {tuple(c) for c in first} == {tuple(o) for o in rotations(list(first[0]))}


def test_judge_group_retries_bad_answers():
    q = make_question()
    g = three_way_group()
    client = ScriptedJudge(["mock/alpha", "mock/beta", "mock/delta"], fail_first=2)
    j = judge_group(q, g, "mock/jev", client)  # type: ignore[arg-type]
    assert len(client.calls) == 10 + 2
    assert j.usage["attempts"] == 12  # type: ignore[index]

    client = ScriptedJudge(["mock/alpha"], fail_first=99)
    with pytest.raises(DecisionError):
        judge_group(q, g, "mock/jev", client)  # type: ignore[arg-type]
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
        assert sum(r.score for r in j.ranking) == pytest.approx(1)
    assert len({r.score for j in js for r in j.ranking}) > 2

    again = run_judging(qs, readings, JUDGES, client, out, progress=False)
    assert len(again) == len(js)
    assert len(read_jsonl(out, Judgment)) == len(js)


def test_run_judging_redoes_groups_that_changed(tmp_path: Path):
    from divination_bench.judge import current_judgments

    qs = [make_question("q1")]
    out = tmp_path / "judgments.jsonl"
    client = LLMClient(api_key="unused")
    partial = [r for r in make_readings(seeds=(0,)) if r.method != Method.iching]
    first = run_judging(
        qs, partial, ["mock/gamma"], client, out, modes=("prediction",), progress=False
    )
    complete = make_readings(seeds=(0,))
    second = run_judging(
        qs, complete, ["mock/gamma"], client, out, modes=("prediction",), progress=False
    )
    n_on_file = len(read_jsonl(out, Judgment))
    # iching joins both methods groups and adds a new models group
    assert n_on_file == len(first) + 3
    assert len(second) == len(build_groups(complete, modes=("prediction",)))
    methods = [j for j in second if j.comparison == "methods"]
    assert all(len(j.ranking) == 3 for j in methods)

    edited = [qs[0].model_copy(update={"outcome_summary": "Corrected outcome."})]
    run_judging(
        edited,
        complete,
        ["mock/gamma"],
        client,
        out,
        modes=("prediction",),
        progress=False,
    )
    assert len(read_jsonl(out, Judgment)) == n_on_file + len(second)

    narrowed = run_judging(
        edited,
        partial,
        ["mock/gamma"],
        client,
        out,
        comparisons=("methods",),
        modes=("prediction",),
        progress=False,
    )
    assert all(
        len(j.ranking) == 3
        for j in current_judgments(read_jsonl(out, Judgment))
        if j.comparison == "methods"
    )
    assert narrowed


class BudgetClient:
    spent_usd = 0.0

    def decide(self, *a, **k):
        raise BudgetExceededError("budget")


def test_run_judging_stops_on_budget(tmp_path: Path):
    out = tmp_path / "j.jsonl"
    js = run_judging(
        [make_question()],
        make_readings(),
        JUDGES,
        BudgetClient(),  # type: ignore[arg-type]
        out,
        progress=False,
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
