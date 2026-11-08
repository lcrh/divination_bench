from __future__ import annotations

from pathlib import Path

import pytest
import yaml
from test_judge import JUDGES, MODELS, make_question, make_readings
from typer.testing import CliRunner

from divination_bench.analyze import (
    accuracy_table,
    agreement_table,
    build_report,
    items_from_judgments,
    kendall_tau,
    known_question_ids,
    leaderboard,
    self_preference_table,
    spearman_rho,
)
from divination_bench.judge import run_judging
from divination_bench.llm import LLMClient
from divination_bench.schemas import Judgment, KnowledgeProbe, RankedItem


def judgment(
    judge: str,
    order: list[str],
    *,
    qid: str = "q1",
    comparison: str = "models",
    mode: str = "prediction",
    seed: int = 0,
    scores: list[float] | None = None,
) -> Judgment:
    """`order` lists 'method|model' keys from best to worst."""
    scores = scores or [9.0 - 3 * i for i in range(len(order))]
    labels = "ABC"[: len(order)]
    first = order[0].split("|")
    return Judgment(
        question_id=qid,
        comparison=comparison,
        judge_model=judge,
        mode=mode,
        seed=seed,
        fixed_method=first[0] if comparison == "models" else None,
        fixed_model=first[1] if comparison == "methods" else None,
        label_map=dict(zip(labels, order, strict=True)),
        ranking=[
            RankedItem(label=lab, rank=i + 1, score=scores[i], rationale="")
            for i, lab in enumerate(labels)
        ],
        raw_response="",
        usage={"cost": 0.1, "prompt_tokens": 100, "completion_tokens": 50},
        created_at="",
    )


A, B = "tarot|mock/alpha", "tarot|mock/beta"


def test_leaderboard_win_rate_and_rank():
    js = [
        judgment("mock/alpha", [A, B]),
        judgment("mock/beta", [B, A]),
        judgment("mock/gamma", [A, B]),
        judgment("mock/gamma", [A, B], qid="q2"),
    ]
    rows = {
        r["entity"]: r
        for r in leaderboard(
            items_from_judgments(js), lambda it: it.model, ci=True, n_boot=200, seed=0
        )
    }
    assert rows["mock/alpha"]["win_rate"] == pytest.approx(0.75)
    assert rows["mock/beta"]["mean_rank"] == pytest.approx(1.75)
    assert rows["mock/alpha"]["questions"] == 2
    lo, hi = rows["mock/alpha"]["win_ci"]
    assert 0 <= lo <= 0.75 <= hi <= 1


def test_self_preference_flag():
    js = [judgment("mock/alpha", [A, B], seed=s) for s in range(4)]
    js += [judgment("mock/gamma", [B, A], seed=s) for s in range(4)]
    rows = self_preference_table(items_from_judgments(js)).rows
    alpha = next(r for r in rows if r["model"] == "mock/alpha")
    assert alpha["win_self"] == 1.0 and alpha["win_others"] == 0.0
    assert alpha["flag"] == "SELF-PREFERENCE"


def test_rank_correlations():
    assert kendall_tau([1, 2, 3], [1, 2, 3]) == 1
    assert kendall_tau([1, 2, 3], [3, 2, 1]) == -1
    assert spearman_rho([1, 2, 3], [3, 2, 1]) == -1
    js = [judgment("mock/alpha", [A, B]), judgment("mock/beta", [B, A])]
    js += [
        judgment("mock/alpha", [A, B], seed=1),
        judgment("mock/beta", [A, B], seed=1),
    ]
    (row,) = agreement_table(js).rows
    assert row["groups"] == 2 and row["kendall"] == 0 and row["top1"] == 0.5


def test_accuracy_and_chance():
    q = make_question()
    readings = make_readings(seeds=(0,))
    readings[0] = readings[0].model_copy(update={"answer": "no"})
    rows = accuracy_table({q.id: q}, readings, n_boot=0, seed=0).rows
    overall = next(r for r in rows if r["method"] == "all" and r["model"] == "all")
    assert overall["n"] == 6
    assert overall["accuracy"] == pytest.approx(5 / 6)
    assert overall["chance"] == 0.5


def probe(qid: str, model: str, knows: str, correct: bool | None) -> KnowledgeProbe:
    return KnowledgeProbe(
        question_id=qid,
        model=model,
        knows_outcome=knows,
        stated_answer="Yes",
        correct=correct,
        raw_response="",
        created_at="",
    )


def test_known_questions():
    probes = [
        probe("q1", "mock/alpha", "yes", True),
        probe("q2", "mock/alpha", "yes", False),
        probe("q3", "mock/beta", "unsure", True),
    ]
    assert known_question_ids(probes) == {"q1"}


def test_report_end_to_end(tmp_path: Path):
    qs = [
        make_question("q1"),
        make_question("q2", "sports"),
        make_question("q3", "tech"),
    ]
    readings = make_readings(qids=("q1", "q2", "q3"))
    client = LLMClient(api_key="unused")
    js = run_judging(qs, readings, JUDGES, client, tmp_path / "j.jsonl", progress=False)
    probes = [probe("q2", "mock/alpha", "yes", True)]

    rep = build_report(qs, readings, js, probes, tmp_path, n_boot=50)
    md = (tmp_path / "report.md").read_text()
    for heading in (
        "Method leaderboard: prediction only",
        "Method leaderboard: full reading",
        "Model leaderboard (prediction mode)",
        "Self-preference",
        "Objective accuracy",
        "Method scores by domain",
        "Judge agreement",
        "Knowledge probes",
        "Cost",
        "latest context source",
    ):
        assert heading in md
    assert "EXCLUDE?" in md
    csvs = {p.name for p in (tmp_path / "csv").iterdir()}
    assert {"method_leaderboard_prediction.csv", "model_leaderboard_full.csv"} <= csvs
    assert rep.excluded == []

    rep = build_report(qs, readings, js, probes, None, exclude_known=True, n_boot=0)
    assert rep.excluded == ["q2"]
    assert "Questions with data: 2" in rep.markdown


def write_question_dir(directory: Path) -> None:
    for qid, backup in (("q1", False), ("q2", True), ("q3", False)):
        q = make_question(qid).model_copy(update={"backup": backup})
        path = directory / "politics" / f"{qid}.yaml"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(yaml.safe_dump(q.model_dump(mode="json")))


def write_config(tmp_path: Path) -> Path:
    write_question_dir(tmp_path / "questions")
    cfg = {
        "questions_dir": str(tmp_path / "questions"),
        "results_dir": str(tmp_path / "results"),
        "seeds": [0],
        "generation": {"methods": ["tarot", "iching", "predict"], "models": MODELS},
        "judging": {"modes": ["full", "prediction"], "judges": JUDGES},
        "knowledge_probe": {"models": MODELS},
    }
    path = tmp_path / "config.yaml"
    path.write_text(yaml.safe_dump(cfg))
    return path


def test_cli_validate_and_estimate_calls(tmp_path: Path):
    from divination_bench.cli import (
        Assumptions,
        app,
        estimate_calls,
        load_settings,
        select_questions,
    )

    config = write_config(tmp_path)
    result = CliRunner().invoke(app, ["validate", "--config", str(config)])
    assert result.exit_code == 0, result.output
    assert "3 questions OK" in result.output

    s = load_settings(config, "x", judges="mock/j1")
    qs = select_questions(s.questions_dir)
    assert [q.id for q in qs] == ["q1", "q3"]
    assert len(select_questions(s.questions_dir, include_backups=True)) == 3
    assert [q.id for q in select_questions(s.questions_dir, "q2")] == ["q2"]
    rows = estimate_calls(s, qs, Assumptions())
    calls = {
        stage: sum(r["calls"] for r in rows if r["stage"].startswith(stage))
        for stage in ("generate", "judge")
    }
    assert calls["generate"] == 2 * 3 * 2
    # models: (pred: 3 methods + full: 2) per question; methods: 2 per (question, model)
    assert calls["judge"] == 2 * (5 + 2 * 2)


def test_cli_mock_run(tmp_path: Path):
    pytest.importorskip("divination_bench.generate")
    pytest.importorskip("divination_bench.probe")
    from divination_bench.cli import app

    config = write_config(tmp_path)
    args = ["run", "--config", str(config), "--run", "t", "--mock", "--n-boot", "20"]
    result = CliRunner().invoke(app, args)
    assert result.exit_code == 0, result.output
    run_dir = tmp_path / "results" / "t"
    assert (run_dir / "report.md").exists()
    assert (run_dir / "config.judge.yaml").exists()
    assert len((run_dir / "judgments.jsonl").read_text().splitlines()) == 2 * 9 * 3
