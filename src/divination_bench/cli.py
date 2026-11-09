"""Command-line entry point: `divination-bench <command>`."""

from __future__ import annotations

import json
import sys
from dataclasses import asdict, dataclass, field, fields
from pathlib import Path
from typing import Annotated, Any

import httpx
import typer
import yaml
from rich.console import Console
from rich.table import Table as RichTable

from .analyze import build_report, question_metadata_rows, recorded_cost
from .cutoffs import cutoff_violations, parse_cutoffs
from .judge import build_groups
from .llm import MOCK_PREFIX, LLMClient, ledger_cost
from .questions import load_questions
from .schemas import Judgment, KnowledgeProbe, Method, Question, Reading
from .store import now_iso, read_jsonl

app = typer.Typer(
    no_args_is_help=True,
    add_completion=False,
    help="Benchmark LLMs predicting the future from Thoth tarot and I Ching readings.",
)
console = Console(width=None if sys.stdout.isatty() else 160)

OPENROUTER_MODELS_URL = "https://openrouter.ai/api/v1/models"
# Decision models are missing from /models; USD per token (input, output).
DECISION_MODEL_PRICING = {"typesafe/jev-1.13": (0.042e-6, 0.0)}

ConfigOpt = Annotated[Path, typer.Option("--config", help="YAML config file.")]
RunOpt = Annotated[str, typer.Option("--run", help="Run name: results/<run>/.")]
QuestionsOpt = Annotated[
    str | None, typer.Option("--questions", help="Comma-separated question ids.")
]
LimitOpt = Annotated[
    int | None, typer.Option("--limit", help="Use the first N questions.")
]
ModelsOpt = Annotated[
    str | None, typer.Option("--models", help="Generator models (csv).")
]
JudgesOpt = Annotated[str | None, typer.Option("--judges", help="Judge models (csv).")]
MethodsOpt = Annotated[
    str | None,
    typer.Option(
        "--methods", help="tarot,iching,predict,tarot_reading,iching_reading (csv)."
    ),
]
SeedsOpt = Annotated[
    str | None, typer.Option("--seeds", help="Seeds (csv), e.g. 0,1,2.")
]
ModesOpt = Annotated[
    str | None, typer.Option("--modes", help="full,prediction,reading (csv).")
]
ComparisonsOpt = Annotated[
    str | None, typer.Option("--comparisons", help="models,methods (csv).")
]
BudgetOpt = Annotated[
    float | None,
    typer.Option(
        "--budget",
        help="Stop when total spend for this run (incl. costs already recorded "
        "in the run directory) reaches this many USD.",
    ),
]
EffortOpt = Annotated[
    str | None,
    typer.Option("--reasoning-effort", help="low|medium|high (OpenRouter reasoning)."),
]
WorkersOpt = Annotated[int | None, typer.Option("--workers", help="Parallel requests.")]
MockOpt = Annotated[
    bool, typer.Option("--mock", help="Replace every model with mock/<name> (offline).")
]
BackupsOpt = Annotated[
    bool,
    typer.Option("--include-backups", help="Include reserve questions (backup: true)."),
]
ExcludeKnownOpt = Annotated[
    bool,
    typer.Option(
        "--exclude-known",
        help="Drop questions any tested model claimed to know from the report.",
    ),
]
BootOpt = Annotated[int, typer.Option("--n-boot", help="Bootstrap resamples for CIs.")]
IgnoreCutoffsOpt = Annotated[
    bool,
    typer.Option(
        "--ignore-cutoffs",
        help="Generate even if a question is not after a model's documented cutoff.",
    ),
]


def _csv(value: str | None) -> list[str] | None:
    if value is None:
        return None
    return [v.strip() for v in value.split(",") if v.strip()]


def _mockify(model: str) -> str:
    return (
        model if model.startswith(MOCK_PREFIX) else MOCK_PREFIX + model.split("/")[-1]
    )


@dataclass
class Settings:
    run: str
    run_dir: Path
    questions_dir: Path
    models: list[str]
    probe_models: list[str]
    judges: list[str]
    methods: list[str]
    seeds: list[int]
    modes: list[str]
    comparisons: list[str]
    gen_temperature: float
    gen_max_tokens: int
    workers: int
    budget: float | None
    reasoning_effort: str | None
    mock: bool
    raw_config: dict = field(repr=False)

    @property
    def readings_path(self) -> Path:
        return self.run_dir / "readings.jsonl"

    @property
    def judgments_path(self) -> Path:
        return self.run_dir / "judgments.jsonl"

    @property
    def probes_path(self) -> Path:
        return self.run_dir / "probes.jsonl"

    @property
    def spend_path(self) -> Path:
        return self.run_dir / "spend.jsonl"

    def snapshot(self, command: str) -> None:
        self.run_dir.mkdir(parents=True, exist_ok=True)
        data = {
            k: (str(v) if isinstance(v, Path) else v)
            for k, v in asdict(self).items()
            if k != "raw_config"
        }
        data["command"] = command
        data["written_at"] = now_iso()
        (self.run_dir / f"config.{command}.yaml").write_text(
            yaml.safe_dump(data, sort_keys=False)
        )


def load_settings(
    config: Path,
    run: str,
    *,
    models: str | None = None,
    judges: str | None = None,
    methods: str | None = None,
    seeds: str | None = None,
    modes: str | None = None,
    comparisons: str | None = None,
    budget: float | None = None,
    reasoning_effort: str | None = None,
    workers: int | None = None,
    mock: bool = False,
) -> Settings:
    cfg: dict[str, Any] = yaml.safe_load(config.read_text()) or {}
    gen = cfg.get("generation", {})
    jud = cfg.get("judging", {})
    gen_models = _csv(models) or gen.get("models", [])
    probe_models = _csv(models) or cfg.get("knowledge_probe", {}).get(
        "models", gen_models
    )
    judge_models = _csv(judges) or jud.get("judges", [])
    if mock:
        gen_models = [_mockify(m) for m in gen_models]
        probe_models = [_mockify(m) for m in probe_models]
        judge_models = [_mockify(m) for m in judge_models]
    method_list = _csv(methods) or gen.get("methods", [m.value for m in Method])
    for m in method_list:
        Method(m)
    mode_list = _csv(modes) or jud.get("modes", ["full", "prediction", "reading"])
    comparison_list = _csv(comparisons) or jud.get("comparisons", ["models", "methods"])
    if bad := set(mode_list) - {"full", "prediction", "reading"}:
        raise typer.BadParameter(f"unknown modes {sorted(bad)}")
    if bad := set(comparison_list) - {"models", "methods"}:
        raise typer.BadParameter(f"unknown comparisons {sorted(bad)}")
    if reasoning_effort not in (None, "low", "medium", "high"):
        raise typer.BadParameter("--reasoning-effort must be low, medium or high")
    results_dir = Path(cfg.get("results_dir", "results"))
    return Settings(
        run=run,
        run_dir=results_dir / run,
        questions_dir=Path(cfg.get("questions_dir", "data/questions")),
        models=gen_models,
        probe_models=probe_models,
        judges=judge_models,
        methods=method_list,
        seeds=[int(s) for s in (_csv(seeds) or cfg.get("seeds", [0]))],
        modes=mode_list,
        comparisons=comparison_list,
        gen_temperature=float(gen.get("temperature", 1.0)),
        gen_max_tokens=int(gen.get("max_tokens", 16000)),
        workers=workers or int(cfg.get("workers", 8)),
        budget=budget if budget is not None else cfg.get("budget_usd"),
        reasoning_effort=reasoning_effort or cfg.get("reasoning_effort"),
        mock=mock,
        raw_config=cfg,
    )


def is_backup(q: Question) -> bool:
    return q.backup or (q.notes or "").strip().lower() == "backup"


def select_questions(
    questions_dir: Path,
    ids: str | None = None,
    limit: int | None = None,
    include_backups: bool = False,
) -> list[Question]:
    wanted = _csv(ids)
    qs = load_questions(questions_dir, wanted)
    if wanted:
        missing = set(wanted) - {q.id for q in qs}
        if missing:
            raise typer.BadParameter(f"unknown question ids: {sorted(missing)}")
    elif not include_backups:
        qs = [q for q in qs if not is_backup(q)]
    return qs[:limit] if limit else qs


def check_cutoffs(s: Settings, qs: list[Question], ignore: bool) -> None:
    cutoffs = parse_cutoffs(s.raw_config.get("model_cutoffs"))
    problems = cutoff_violations(qs, s.models, cutoffs)
    if not problems:
        return
    for p in problems:
        console.print(f"[red]{p}")
    if not ignore:
        raise typer.BadParameter(
            f"{len(problems)} cutoff violations (use --ignore-cutoffs to proceed)"
        )


def run_spend(s: Settings) -> float:
    """Everything this run directory has spent so far, across all earlier invocations."""
    records = recorded_cost(
        read_jsonl(s.readings_path, Reading),
        read_jsonl(s.judgments_path, Judgment),
        read_jsonl(s.probes_path, KnowledgeProbe),
    )
    return max(records, ledger_cost(s.spend_path))


def make_client(s: Settings) -> LLMClient:
    client = LLMClient(
        budget_usd=s.budget,
        reasoning_effort=s.reasoning_effort,
        ledger_path=s.spend_path,
    )
    client.spent_usd = run_spend(s)
    if s.budget is not None:
        console.print(
            f"Budget ${s.budget:.2f}; already recorded in {s.run_dir}: "
            f"${client.spent_usd:.2f}"
        )
    return client


def _print_rows(title: str, rows: list[dict]) -> None:
    if not rows:
        console.print(f"{title}: no rows")
        return
    t = RichTable(title=title)
    for col in rows[0]:
        t.add_column(col)
    for row in rows:
        t.add_row(*(str(v) for v in row.values()))
    console.print(t)


@app.command()
def validate(
    config: ConfigOpt = Path("config/default.yaml"),
    questions_dir: Annotated[
        Path | None, typer.Option("--questions-dir", help="Override config.")
    ] = None,
) -> None:
    """Validate every question file and print the date metadata table."""
    cfg = yaml.safe_load(config.read_text()) or {}
    qs = load_questions(
        questions_dir or Path(cfg.get("questions_dir", "data/questions"))
    )
    rows = question_metadata_rows(qs)
    for row in rows:
        notes = str(row["notes"])
        row["notes"] = notes if len(notes) <= 40 else notes[:37] + "..."
    _print_rows("Questions", rows)
    backups = sum(1 for q in qs if is_backup(q))
    models = cfg.get("generation", {}).get("models", [])
    problems = cutoff_violations(qs, models, parse_cutoffs(cfg.get("model_cutoffs")))
    for p in problems:
        console.print(f"[red]{p}")
    console.print(f"[green]{len(qs)} questions OK[/] ({backups} backups)")
    if problems:
        console.print(f"[red]{len(problems)} cutoff violations")
        raise typer.Exit(1)


@app.command("cast")
def cast_cmd(
    question_id: str,
    method: Annotated[Method, typer.Option("--method", help="tarot or iching.")],
    seed: Annotated[int, typer.Option("--seed")] = 0,
) -> None:
    """Print the deterministic draw for a question, method and seed."""
    from .divination import cast

    if method == Method.predict:
        raise typer.BadParameter("predict has no cast; use tarot or iching")
    _, text = cast(question_id, method, seed)
    console.print(text, markup=False, highlight=False)


@app.command()
def probe(
    config: ConfigOpt = Path("config/default.yaml"),
    run: RunOpt = "default",
    questions: QuestionsOpt = None,
    limit: LimitOpt = None,
    models: ModelsOpt = None,
    budget: BudgetOpt = None,
    reasoning_effort: EffortOpt = None,
    workers: WorkersOpt = None,
    mock: MockOpt = False,
    include_backups: BackupsOpt = False,
    cutoff: Annotated[
        bool, typer.Option(help="Also ask each model for its training cutoff.")
    ] = True,
) -> None:
    """Ask tested models whether they already know each outcome."""
    s = load_settings(
        config,
        run,
        models=models,
        budget=budget,
        reasoning_effort=reasoning_effort,
        workers=workers,
        mock=mock,
    )
    qs = select_questions(s.questions_dir, questions, limit, include_backups)
    _probe(s, qs, make_client(s), cutoff=cutoff)


def _probe(s: Settings, qs: list[Question], client: LLMClient, *, cutoff: bool) -> None:
    from .probe import probe_cutoff, run_probes

    s.snapshot("probe")
    probes = run_probes(qs, s.probe_models, client, s.probes_path, workers=s.workers)
    knew = [p for p in probes if p.knows_outcome == "yes"]
    _print_rows(
        "Models claiming to know the outcome",
        [
            {
                "question": p.question_id,
                "model": p.model,
                "stated": p.stated_answer,
                "correct": p.correct,
            }
            for p in knew
        ],
    )
    if cutoff:
        path = s.run_dir / "probe_cutoffs.json"
        cutoffs = json.loads(path.read_text()) if path.exists() else {}
        for m in s.probe_models:
            if m not in cutoffs:
                cutoffs[m] = probe_cutoff(m, client)
                path.write_text(json.dumps(cutoffs, indent=2))
        for m in s.probe_models:
            console.print(f"[bold]{m}[/] cutoff: {cutoffs[m].strip()[:300]}")


@app.command()
def generate(
    config: ConfigOpt = Path("config/default.yaml"),
    run: RunOpt = "default",
    questions: QuestionsOpt = None,
    limit: LimitOpt = None,
    models: ModelsOpt = None,
    methods: MethodsOpt = None,
    seeds: SeedsOpt = None,
    budget: BudgetOpt = None,
    reasoning_effort: EffortOpt = None,
    workers: WorkersOpt = None,
    mock: MockOpt = False,
    include_backups: BackupsOpt = False,
    ignore_cutoffs: IgnoreCutoffsOpt = False,
) -> None:
    """Generate readings and predictions (resumable)."""
    s = load_settings(
        config,
        run,
        models=models,
        methods=methods,
        seeds=seeds,
        budget=budget,
        reasoning_effort=reasoning_effort,
        workers=workers,
        mock=mock,
    )
    qs = select_questions(s.questions_dir, questions, limit, include_backups)
    check_cutoffs(s, qs, ignore_cutoffs)
    _generate(s, qs, make_client(s))


def _generate(s: Settings, qs: list[Question], client: LLMClient) -> list[Reading]:
    from .generate import run_generation

    s.snapshot("generate")
    readings = run_generation(
        qs,
        s.models,
        [Method(m) for m in s.methods],
        s.seeds,
        client,
        s.readings_path,
        temperature=s.gen_temperature,
        max_tokens=s.gen_max_tokens,
        workers=s.workers,
    )
    console.print(f"{len(readings)} readings; spent ${client.spent_usd:.2f}")
    return readings


@app.command()
def judge(
    config: ConfigOpt = Path("config/default.yaml"),
    run: RunOpt = "default",
    questions: QuestionsOpt = None,
    limit: LimitOpt = None,
    models: ModelsOpt = None,
    judges: JudgesOpt = None,
    methods: MethodsOpt = None,
    seeds: SeedsOpt = None,
    modes: ModesOpt = None,
    comparisons: ComparisonsOpt = None,
    budget: BudgetOpt = None,
    reasoning_effort: EffortOpt = None,
    workers: WorkersOpt = None,
    mock: MockOpt = False,
    include_backups: BackupsOpt = False,
) -> None:
    """Judge the readings in the run directory (resumable)."""
    s = load_settings(
        config,
        run,
        models=models,
        judges=judges,
        methods=methods,
        seeds=seeds,
        modes=modes,
        comparisons=comparisons,
        budget=budget,
        reasoning_effort=reasoning_effort,
        workers=workers,
        mock=mock,
    )
    qs = select_questions(s.questions_dir, questions, limit, include_backups)
    _judge(s, qs, make_client(s))


def _judge(s: Settings, qs: list[Question], client: LLMClient) -> list[Judgment]:
    from .judge import run_judging

    s.snapshot("judge")
    readings = [
        r
        for r in read_jsonl(s.readings_path, Reading)
        if r.model in s.models and r.method in s.methods and r.seed in s.seeds
    ]
    if not readings:
        console.print(f"[yellow]No matching readings in {s.readings_path}.")
    judgments = run_judging(
        qs,
        readings,
        s.judges,
        client,
        s.judgments_path,
        comparisons=s.comparisons,
        modes=s.modes,
        workers=s.workers,
    )
    console.print(f"{len(judgments)} judgments; spent ${client.spent_usd:.2f}")
    return judgments


@app.command()
def report(
    config: ConfigOpt = Path("config/default.yaml"),
    run: RunOpt = "default",
    questions: QuestionsOpt = None,
    limit: LimitOpt = None,
    include_backups: BackupsOpt = False,
    exclude_known: ExcludeKnownOpt = False,
    n_boot: BootOpt = 1000,
) -> None:
    """Write results/<run>/report.md and CSVs from the stored records."""
    s = load_settings(config, run)
    qs = select_questions(s.questions_dir, questions, limit, include_backups)
    _report(s, qs, exclude_known=exclude_known, n_boot=n_boot)


def _report(
    s: Settings, qs: list[Question], *, exclude_known: bool, n_boot: int
) -> None:
    rep = build_report(
        qs,
        read_jsonl(s.readings_path, Reading),
        read_jsonl(s.judgments_path, Judgment),
        read_jsonl(s.probes_path, KnowledgeProbe),
        s.run_dir,
        exclude_known=exclude_known,
        n_boot=n_boot,
        title=f"divination-bench report: {s.run}",
        total_spend=run_spend(s),
    )
    if rep.excluded:
        console.print(f"Excluded known questions: {', '.join(rep.excluded)}")
    console.print(f"[green]Wrote {s.run_dir / 'report.md'}")


@app.command("run")
def run_all(
    config: ConfigOpt = Path("config/default.yaml"),
    run: RunOpt = "default",
    questions: QuestionsOpt = None,
    limit: LimitOpt = None,
    models: ModelsOpt = None,
    judges: JudgesOpt = None,
    methods: MethodsOpt = None,
    seeds: SeedsOpt = None,
    modes: ModesOpt = None,
    comparisons: ComparisonsOpt = None,
    budget: BudgetOpt = None,
    reasoning_effort: EffortOpt = None,
    workers: WorkersOpt = None,
    mock: MockOpt = False,
    include_backups: BackupsOpt = False,
    exclude_known: ExcludeKnownOpt = False,
    n_boot: BootOpt = 1000,
    ignore_cutoffs: IgnoreCutoffsOpt = False,
    skip_probe: Annotated[bool, typer.Option("--skip-probe")] = False,
) -> None:
    """probe -> generate -> judge -> report, sharing one budget."""
    s = load_settings(
        config,
        run,
        models=models,
        judges=judges,
        methods=methods,
        seeds=seeds,
        modes=modes,
        comparisons=comparisons,
        budget=budget,
        reasoning_effort=reasoning_effort,
        workers=workers,
        mock=mock,
    )
    qs = select_questions(s.questions_dir, questions, limit, include_backups)
    check_cutoffs(s, qs, ignore_cutoffs)
    client = make_client(s)
    if not skip_probe:
        _probe(s, qs, client, cutoff=True)
    _generate(s, qs, client)
    _judge(s, qs, client)
    _report(s, qs, exclude_known=exclude_known, n_boot=n_boot)


@dataclass
class Assumptions:
    """Rough per-call token counts (reasoning tokens count as output)."""

    gen_input: int = 1500
    gen_output_divination: int = 5000
    gen_output_predict: int = 2500
    judge_input_base: int = 1500
    judge_input_per_item_full: int = 1800
    judge_input_per_item_prediction: int = 300
    judge_output: int = 70
    probe_input: int = 600
    probe_output: int = 1500


def fetch_pricing() -> dict[str, tuple[float, float]]:
    """OpenRouter USD per token: model id -> (prompt, completion)."""
    resp = httpx.get(OPENROUTER_MODELS_URL, timeout=30)
    resp.raise_for_status()
    out = {}
    for m in resp.json().get("data", []):
        p = m.get("pricing") or {}
        try:
            out[m["id"]] = (float(p.get("prompt", 0)), float(p.get("completion", 0)))
        except (TypeError, ValueError):
            continue
    return out


def estimate_calls(
    s: Settings, qs: list[Question], a: Assumptions
) -> list[dict[str, Any]]:
    """Calls and token totals per (stage, model), mirroring the real grids."""
    rows: dict[tuple[str, str], dict[str, Any]] = {}

    def add(stage: str, model: str, tin: int, tout: int) -> None:
        r = rows.setdefault(
            (stage, model),
            {"stage": stage, "model": model, "calls": 0, "input": 0, "output": 0},
        )
        r["calls"] += 1
        r["input"] += tin
        r["output"] += tout

    for _ in qs:
        for m in s.probe_models:
            add("probe", m, a.probe_input, a.probe_output)
    fake = []
    for q in qs:
        for method in s.methods:
            for seed in s.seeds:
                for model in s.models:
                    divines = method != Method.predict
                    out = a.gen_output_divination if divines else a.gen_output_predict
                    add("generate", model, a.gen_input, out)
                    fake.append(
                        Reading(
                            question_id=q.id,
                            method=Method(method),
                            seed=seed,
                            model=model,
                            reading="x" if divines else None,
                            prediction="x",
                            raw_response="",
                            created_at="",
                        )
                    )
    for g in build_groups(fake, s.comparisons, s.modes):  # type: ignore[arg-type]
        per_item = (
            a.judge_input_per_item_full
            if g.mode != "prediction"
            else a.judge_input_per_item_prediction
        )
        # successive choice: rounds over n, n-1, ..., 2 forecasts, each in every
        # rotation, each rotation asking accuracy and precision separately
        for k in range(len(g.readings), 1, -1):
            for j in s.judges:
                for _ in range(2 * k):
                    add(
                        f"judge:{g.comparison}/{g.mode}",
                        j,
                        a.judge_input_base + per_item * k,
                        a.judge_output,
                    )
    return list(rows.values())


@app.command()
def estimate(
    config: ConfigOpt = Path("config/default.yaml"),
    questions: QuestionsOpt = None,
    limit: LimitOpt = None,
    models: ModelsOpt = None,
    judges: JudgesOpt = None,
    methods: MethodsOpt = None,
    seeds: SeedsOpt = None,
    modes: ModesOpt = None,
    comparisons: ComparisonsOpt = None,
    include_backups: BackupsOpt = False,
    assume: Annotated[
        list[str] | None,
        typer.Option(
            "--assume",
            help="Override a token assumption, e.g. --assume judge_output=5000. "
            "Keys: " + ", ".join(f.name for f in fields(Assumptions)),
        ),
    ] = None,
) -> None:
    """Rough cost estimate for probe + generate + judge using OpenRouter pricing."""
    s = load_settings(
        config,
        "estimate",
        models=models,
        judges=judges,
        methods=methods,
        seeds=seeds,
        modes=modes,
        comparisons=comparisons,
    )
    overrides: dict[str, int] = dict(s.raw_config.get("estimate", {}) or {})
    for kv in assume or []:
        key, _, value = kv.partition("=")
        overrides[key.strip()] = int(value)
    try:
        a = Assumptions(**overrides)
    except TypeError as exc:
        raise typer.BadParameter(str(exc)) from exc
    qs = select_questions(s.questions_dir, questions, limit, include_backups)
    rows = estimate_calls(s, qs, a)
    try:
        pricing = fetch_pricing()
    except httpx.HTTPError as exc:
        console.print(f"[yellow]Could not fetch pricing ({exc}); showing tokens only.")
        pricing = {}
    pricing = {**DECISION_MODEL_PRICING, **pricing}

    t = RichTable(title=f"Estimate for {len(qs)} questions")
    for col in ("stage", "model", "calls", "in tok", "out tok", "$/M in/out", "cost $"):
        t.add_column(col, justify="left" if col in ("stage", "model") else "right")
    by_stage: dict[str, float] = {}
    unpriced = set()
    for r in rows:
        price = pricing.get(r["model"])
        if price is None and not r["model"].startswith(MOCK_PREFIX):
            unpriced.add(r["model"])
        pin, pout = price or (0.0, 0.0)
        cost = r["input"] * pin + r["output"] * pout
        stage = r["stage"].split(":")[0]
        by_stage[stage] = by_stage.get(stage, 0.0) + cost
        t.add_row(
            r["stage"],
            r["model"],
            str(r["calls"]),
            _ktok(r["input"]),
            _ktok(r["output"]),
            f"{pin * 1e6:.2f}/{pout * 1e6:.2f}",
            f"{cost:.2f}",
        )
    console.print(t)
    console.print(f"Assumptions: {asdict(a)}")
    if unpriced and pricing:
        console.print(
            f"[yellow]No OpenRouter pricing for: {', '.join(sorted(unpriced))}"
        )
    console.print(
        "By stage: " + ", ".join(f"{k} ${v:.2f}" for k, v in by_stage.items())
    )
    console.print(f"[bold]Estimated total: ${sum(by_stage.values()):.2f}[/]")
    if s.budget is not None:
        console.print(f"Configured budget: ${s.budget:.2f}")


def _ktok(n: int) -> str:
    return f"{n / 1e6:.2f}M" if n >= 1e6 else f"{n / 1e3:.0f}k"
