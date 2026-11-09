from datetime import date

import pytest

from divination_bench.generate import run_generation
from divination_bench.llm import BudgetExceededError, ChatResult, LLMClient
from divination_bench.probe import parse_probe, run_probes
from divination_bench.prompts_generation import (
    build_generation_messages,
    parse_generation,
)
from divination_bench.schemas import Method, Question, Reading, Source
from divination_bench.store import read_jsonl

OUTCOME = "The Zorblax Party won 41 seats in a landslide upset"
RESOLVED = "Zorblax"


def make_question(qid="test-q", qtype="multiple_choice") -> Question:
    src = Source(
        url="https://example.com",
        title="Preview",
        publisher="Example",
        published_date=date(2026, 10, 1),
    )
    late_src = src.model_copy(update={"published_date": date(2026, 10, 20)})
    return Question(
        id=qid,
        domain="politics",
        title="Example election",
        question="Which party will win the example election?",
        question_type=qtype,
        options=["Alpha", RESOLVED, "Gamma"] if qtype != "open" else None,
        resolution_criteria="Official results.",
        context_summary="Three parties compete; polls are tight.",
        context_sources=[src, late_src],
        event_date=date(2026, 10, 29),
        outcome_summary=OUTCOME,
        resolved_answer=RESOLVED if qtype != "open" else "Zorblax won",
        outcome_sources=[src],
    )


def binary_question(qid: str) -> Question:
    q = make_question(qid)
    return q.model_copy(
        update={
            "question_type": "binary",
            "options": ["Yes", "No"],
            "resolved_answer": "Yes",
        }
    )


class CountingClient(LLMClient):
    def __init__(self, **kw):
        super().__init__(**kw)
        self.calls = 0

    def chat(self, model, messages, **kw):
        self.calls += 1
        return super().chat(model, messages, **kw)


@pytest.mark.parametrize("method", list(Method))
def test_prompt_has_no_outcome(method):
    q = make_question()
    text = "cast text" if method != Method.predict else None
    msgs = build_generation_messages(q, method, text)
    blob = "\n".join(m["content"] for m in msgs)
    assert OUTCOME not in blob
    assert "landslide" not in blob
    assert "Information is current as of 2026-10-20" in blob
    assert q.context_summary in blob
    assert (
        "Options: Alpha; Zorblax; Gamma" in blob
    )  # options are fine, the answer is not flagged
    assert "<answer>" in blob


def test_prompt_open_question_has_no_resolved_answer():
    q = make_question(qtype="open")
    for method in Method:
        msgs = build_generation_messages(q, method, "cast")
        blob = "\n".join(m["content"] for m in msgs)
        assert "Zorblax" not in blob
        assert "do not include an <answer> tag" in blob


def test_method_specific_prompts():
    q = make_question()
    tarot = build_generation_messages(q, Method.tarot, "cards")[0]["content"]
    assert "Crowley-Harris Thoth Tarot" in tarot and "Book of Thoth" in tarot
    iching = build_generation_messages(q, Method.iching, "hex")[0]["content"]
    assert "yarrow-stalk" in iching and "Wilhelm" in iching
    predict = build_generation_messages(q, Method.predict, None)
    assert "<reading>" not in predict[1]["content"]
    with pytest.raises(ValueError):
        build_generation_messages(q, Method.tarot, None)


def test_parse_generation_basic_and_case_insensitive():
    q = make_question()
    out = parse_generation(
        "<reading>r</reading>\n<prediction> p </prediction>\n<answer> zorblax. </answer>",
        q,
        Method.tarot,
    )
    assert out == {"reading": "r", "prediction": "p", "answer": "Zorblax"}


def test_parse_generation_uses_last_tag_and_unmatched_answer():
    q = make_question()
    text = (
        "Format: <reading>...</reading><prediction>...</prediction>\n"
        "<READING>real reading</READING><prediction>real</prediction><answer>Delta</answer>"
    )
    out = parse_generation(text, q, Method.iching)
    assert out["reading"] == "real reading"
    assert out["prediction"] == "real"
    assert out["answer"] is None


def test_parse_generation_answer_prefix():
    q = binary_question("b")
    out = parse_generation(
        "<prediction>p</prediction><answer>Yes, narrowly</answer>", q, Method.predict
    )
    assert out == {"reading": None, "prediction": "p", "answer": "Yes"}


@pytest.mark.parametrize(
    "text,method",
    [
        ("<prediction>p</prediction><answer>Alpha</answer>", Method.tarot),
        ("<reading>r</reading><answer>Alpha</answer>", Method.tarot),
        ("<reading>r</reading><prediction>p</prediction>", Method.tarot),
        ("<prediction></prediction><answer>Alpha</answer>", Method.predict),
        ("<prediction>p</prediction>", Method.predict),
    ],
)
def test_parse_generation_missing_tags(text, method):
    with pytest.raises(ValueError):
        parse_generation(text, make_question(), method)


def test_parse_generation_open_question_no_answer_needed():
    q = make_question(qtype="open")
    out = parse_generation("<prediction>p</prediction>", q, Method.predict)
    assert out["answer"] is None


def test_run_generation_end_to_end_and_resume(tmp_path):
    qs = [binary_question("q-a"), binary_question("q-b")]
    out = tmp_path / "readings.jsonl"
    client = CountingClient()
    models = ["mock/a", "mock/b"]
    seeds = [0, 1]
    readings = run_generation(
        qs, models, list(Method), seeds, client, out, workers=4, progress=False
    )
    expected = len(qs) * len(Method) * len(seeds) * len(models)
    assert len(readings) == expected
    assert client.calls == expected
    assert len(read_jsonl(out, Reading)) == expected

    by_key = {(r.question_id, r.method, r.seed, r.model): r for r in readings}
    for q in qs:
        for m in (Method.tarot, Method.iching):
            for s in seeds:
                a, b = by_key[(q.id, m, s, "mock/a")], by_key[(q.id, m, s, "mock/b")]
                assert a.cast == b.cast and a.cast is not None
                assert a.reading
        p = by_key[(q.id, Method.predict, 0, "mock/a")]
        assert p.cast is None and p.reading is None
    assert all(r.answer in ("Yes", "No") for r in readings)

    client2 = CountingClient()
    again = run_generation(
        qs, models, list(Method), seeds, client2, out, workers=4, progress=False
    )
    assert client2.calls == 0
    assert len(again) == expected
    assert len(read_jsonl(out, Reading)) == expected

    run_generation(qs, models, list(Method), [0, 1, 2], client2, out, progress=False)
    assert client2.calls == expected // 2


def test_run_generation_resume_grows_grid_and_redoes_edited_questions(tmp_path):
    out = tmp_path / "readings.jsonl"
    models = ["mock/a", "mock/b"]
    pilot = [binary_question("q-a")]
    client = CountingClient()
    run_generation(pilot, models, list(Method), [0], client, out, progress=False)
    assert client.calls == len(Method) * len(models)

    full = [binary_question("q-a"), binary_question("q-b")]
    client = CountingClient()
    readings = run_generation(
        full, models, list(Method), [0, 1], client, out, progress=False
    )
    assert client.calls == 3 * len(Method) * len(models)
    assert len(readings) == 4 * len(Method) * len(models)

    edited = [
        full[0].model_copy(update={"context_summary": "New polling changes things."}),
        full[1],
    ]
    client = CountingClient()
    readings = run_generation(
        edited, models, list(Method), [0, 1], client, out, progress=False
    )
    assert client.calls == 2 * len(Method) * len(models)
    assert len(readings) == 4 * len(Method) * len(models)
    assert len({(r.question_id, r.method, r.seed, r.model) for r in readings}) == len(
        readings
    )


def test_generate_one_keeps_cost_of_failed_attempts():
    from divination_bench.generate import generate_one

    class Scripted(LLMClient):
        def __init__(self):
            super().__init__()
            self.texts = ["junk", "<prediction>p</prediction><answer>Yes</answer>"]

        def chat(self, model, messages, **kw):
            return ChatResult(self.texts.pop(0), {"cost": 0.25}, model)

    r = generate_one(binary_question("q"), Method.predict, 0, "x/y", Scripted())
    assert r.usage == {"cost": 0.5, "attempts": 2}
    assert r.fingerprint


def test_ledger_records_paid_calls(tmp_path, monkeypatch):
    from divination_bench import llm

    ledger = tmp_path / "spend.jsonl"
    client = LLMClient(api_key="k", ledger_path=ledger)
    monkeypatch.setattr(
        client,
        "_chat_remote",
        lambda *a: ChatResult("junk", {"cost": 0.3}, "x/y"),
    )
    client.chat("x/y", [{"role": "user", "content": "hi"}])
    client.chat("x/y", [{"role": "user", "content": "hi"}])
    assert llm.ledger_cost(ledger) == pytest.approx(0.6)
    assert llm.ledger_cost(tmp_path / "missing.jsonl") == 0.0


class FlakyClient(CountingClient):
    def chat(self, model, messages, **kw):
        self.calls += 1
        if model == "mock/broken":
            return ChatResult(text="no tags here", usage=None, model=model)
        if model == "mock/budget":
            raise BudgetExceededError("budget")
        return LLMClient.chat(self, model, messages, **kw)


def test_run_generation_skips_persistent_parse_failures(tmp_path):
    client = FlakyClient()
    out = tmp_path / "r.jsonl"
    readings = run_generation(
        [binary_question("q")],
        ["mock/a", "mock/broken"],
        [Method.predict],
        [0],
        client,
        out,
        progress=True,
    )
    assert [r.model for r in readings] == ["mock/a"]
    assert client.calls == 1 + 3


def test_run_generation_stops_on_budget(tmp_path):
    client = FlakyClient()
    qs = [binary_question(f"q{i}") for i in range(20)]
    readings = run_generation(
        qs,
        ["mock/budget"],
        [Method.predict],
        [0],
        client,
        tmp_path / "r.jsonl",
        workers=1,
        progress=False,
    )
    assert readings == []
    assert client.calls < len(qs)


def test_parse_probe_variants():
    fenced = '```json\n{"knows_outcome": "YES", "stated_answer": "Alpha", "training_cutoff_guess": "2026-01"}\n```'
    assert parse_probe(fenced)["knows_outcome"] == "yes"
    assert parse_probe(fenced)["stated_answer"] == "Alpha"
    odd = 'Sure: {"knows_outcome": "maybe", "stated_answer": "null"}'
    assert parse_probe(odd) == {
        "knows_outcome": "unsure",
        "stated_answer": None,
        "training_cutoff_guess": None,
    }
    with pytest.raises(ValueError):
        parse_probe("no json")


def test_run_probes_and_resume(tmp_path):
    out = tmp_path / "probes.jsonl"
    qs = [make_question("p1"), make_question("p2", qtype="open")]
    client = CountingClient()
    probes = run_probes(qs, ["mock/a", "mock/b"], client, out, progress=False)
    assert len(probes) == 4 and client.calls == 4
    assert all(p.knows_outcome == "no" and p.correct is None for p in probes)
    client2 = CountingClient()
    assert len(run_probes(qs, ["mock/a", "mock/b"], client2, out, progress=False)) == 4
    assert client2.calls == 0


def test_probe_correctness():
    from divination_bench.probe import _is_correct

    q = make_question()
    assert _is_correct(q, "zorblax") is True
    assert _is_correct(q, "Alpha") is False
    assert _is_correct(q, None) is None
    assert _is_correct(make_question(qtype="open"), "Zorblax") is None
