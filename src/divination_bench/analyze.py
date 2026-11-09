"""Aggregate judgments, readings and probes into a markdown report plus CSVs."""

from __future__ import annotations

import csv
import random
import re
from collections import defaultdict
from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass, field
from itertools import combinations
from pathlib import Path
from typing import Self

from .generate import current_readings
from .judge import current_judgments, judgment_key, split_key
from .schemas import Judgment, KnowledgeProbe, Method, Question, Reading

SELF_PREFERENCE_THRESHOLD = 0.10
METHOD_ORDER = {"tarot": 0, "iching": 1, "predict": 2}
POOLED = "pooled"
INDEPENDENT = "independent"

Cell = float | int | str | tuple[float, float] | None


@dataclass
class Table:
    """`name` is the CSV stem (None: markdown only); `show=False`: CSV only."""

    name: str | None
    title: str
    columns: list[tuple[str, str]]
    rows: list[dict[str, Cell]]
    note: str = ""
    show: bool = True

    def view(
        self,
        title: str,
        keep: Callable[[dict[str, Cell]], bool],
        drop: Sequence[str] = (),
        note: str = "",
    ) -> Table:
        return Table(
            None,
            title,
            [c for c in self.columns if c[0] not in drop],
            [r for r in self.rows if keep(r)],
            note,
        )

    def markdown(self) -> str:
        out = [f"### {self.title}", ""]
        if self.note:
            out += [self.note, ""]
        if not self.rows:
            return "\n".join(out + ["_No data._", ""])
        out.append("| " + " | ".join(h for _, h in self.columns) + " |")
        out.append("|" + "---|" * len(self.columns))
        for row in self.rows:
            cells = (_fmt(row.get(k)).replace("|", "\\|") for k, _ in self.columns)
            out.append("| " + " | ".join(cells) + " |")
        return "\n".join(out + [""])

    def write_csv(self, directory: Path) -> Path | None:
        if self.name is None:
            return None
        path = directory / f"{self.name}.csv"
        header: list[str] = []
        for k, _ in self.columns:
            is_ci = any(isinstance(r.get(k), tuple) for r in self.rows)
            header += [f"{k}_lo", f"{k}_hi"] if is_ci else [k]
        with path.open("w", newline="") as f:
            w = csv.writer(f)
            w.writerow(header)
            for row in self.rows:
                vals: list[Cell] = []
                for k, _ in self.columns:
                    v = row.get(k)
                    if f"{k}_lo" in header:
                        vals += list(v) if isinstance(v, tuple) else ["", ""]
                    else:
                        vals.append(round(v, 4) if isinstance(v, float) else v)
                w.writerow(["" if v is None else v for v in vals])
        return path


def _fmt(v: Cell) -> str:
    if v is None:
        return ""
    if isinstance(v, tuple):
        return f"[{v[0]:.2f}, {v[1]:.2f}]"
    if isinstance(v, float):
        return f"{v:.2f}"
    return str(v)


@dataclass
class Acc:
    n: int = 0
    rank_sum: float = 0.0
    score_sum: float = 0.0
    wins: float = 0.0
    pairs: float = 0.0
    p_acc_sum: float = 0.0
    p_prec_sum: float = 0.0

    def __add__(self, other: Acc) -> Acc:
        out = Acc(
            self.n,
            self.rank_sum,
            self.score_sum,
            self.wins,
            self.pairs,
            self.p_acc_sum,
            self.p_prec_sum,
        )
        out += other
        return out

    def __iadd__(self, other: Acc) -> Self:
        self.n += other.n
        self.rank_sum += other.rank_sum
        self.score_sum += other.score_sum
        self.wins += other.wins
        self.pairs += other.pairs
        self.p_acc_sum += other.p_acc_sum
        self.p_prec_sum += other.p_prec_sum
        return self

    @property
    def mean_p_accuracy(self) -> float | None:
        return self.p_acc_sum / self.n if self.n else None

    @property
    def mean_p_precision(self) -> float | None:
        return self.p_prec_sum / self.n if self.n else None

    @property
    def mean_rank(self) -> float | None:
        return self.rank_sum / self.n if self.n else None

    @property
    def mean_score(self) -> float | None:
        return self.score_sum / self.n if self.n else None

    @property
    def win_rate(self) -> float | None:
        return self.wins / self.pairs if self.pairs else None


@dataclass(frozen=True)
class Item:
    """One ranked reading within one judgment."""

    question_id: str
    comparison: str
    mode: str
    seed: int
    judge: str
    fixed_method: str | None
    fixed_model: str | None
    method: str
    model: str
    rank: int
    score: float
    n_items: int
    judge_in_group: bool
    p_accuracy: float = 0.0
    p_precision: float = 0.0

    def acc(self) -> Acc:
        return Acc(
            1,
            self.rank,
            self.score,
            self.n_items - self.rank,
            self.n_items - 1,
            self.p_accuracy,
            self.p_precision,
        )


def items_from_judgments(judgments: Iterable[Judgment]) -> list[Item]:
    items = []
    for j in judgments:
        models = {split_key(k)[1] for k in j.label_map.values()}
        for ri in j.ranking:
            method, model = split_key(j.label_map[ri.label])
            items.append(
                Item(
                    question_id=j.question_id,
                    comparison=j.comparison,
                    mode=j.mode,
                    seed=j.seed,
                    judge=j.judge_model,
                    fixed_method=str(j.fixed_method) if j.fixed_method else None,
                    fixed_model=j.fixed_model,
                    method=method,
                    model=model,
                    rank=ri.rank,
                    score=ri.score,
                    n_items=len(j.ranking),
                    judge_in_group=j.judge_model in models,
                    p_accuracy=ri.p_accuracy,
                    p_precision=ri.p_precision,
                )
            )
    return items


PerQuestion = dict[str, dict[str, Acc]]


def per_question(items: Iterable[Item], entity: Callable[[Item], str]) -> PerQuestion:
    out: PerQuestion = defaultdict(lambda: defaultdict(Acc))
    for it in items:
        out[it.question_id][entity(it)] += it.acc()
    return out


def total(per_q: PerQuestion, qids: Iterable[str] | None = None) -> dict[str, Acc]:
    out: dict[str, Acc] = defaultdict(Acc)
    for qid in per_q if qids is None else qids:
        for ent, acc in per_q[qid].items():
            out[ent] += acc
    return out


def bootstrap(
    per_q: PerQuestion,
    stat: Callable[[Acc], float | None],
    n_boot: int = 1000,
    seed: int = 0,
) -> dict[str, tuple[float, float]]:
    """95% percentile CI per entity, resampling questions with replacement."""
    qids = sorted(per_q)
    if len(qids) < 2 or n_boot <= 0:
        return {}
    rng = random.Random(seed)
    samples: dict[str, list[float]] = defaultdict(list)
    for _ in range(n_boot):
        for ent, acc in total(per_q, rng.choices(qids, k=len(qids))).items():
            v = stat(acc)
            if v is not None:
                samples[ent].append(v)
    return {ent: _percentile_ci(vs) for ent, vs in samples.items()}


def _percentile_ci(values: list[float]) -> tuple[float, float]:
    vs = sorted(values)
    lo = vs[round(0.025 * (len(vs) - 1))]
    hi = vs[round(0.975 * (len(vs) - 1))]
    return (lo, hi)


def _entity_order(ent: str) -> tuple[int, str]:
    return (METHOD_ORDER.get(ent, 99), ent)


def leaderboard(
    items: Sequence[Item],
    entity: Callable[[Item], str],
    *,
    ci: bool,
    n_boot: int,
    seed: int,
) -> list[dict[str, Cell]]:
    per_q = per_question(items, entity)
    tot = total(per_q)
    score_ci = bootstrap(per_q, lambda a: a.mean_score, n_boot, seed) if ci else {}
    win_ci = bootstrap(per_q, lambda a: a.win_rate, n_boot, seed) if ci else {}
    rows: list[dict[str, Cell]] = [
        {
            "entity": ent,
            "n": acc.n,
            "questions": sum(1 for q in per_q.values() if ent in q),
            "mean_rank": acc.mean_rank,
            "mean_score": acc.mean_score,
            "score_ci": score_ci.get(ent),
            "p_accuracy": acc.mean_p_accuracy,
            "p_precision": acc.mean_p_precision,
            "win_rate": acc.win_rate,
            "win_ci": win_ci.get(ent),
        }
        for ent, acc in tot.items()
    ]
    return sorted(rows, key=lambda r: _entity_order(str(r["entity"])))


def judge_sets(items: Sequence[Item]) -> list[tuple[str, list[Item]]]:
    """Pooled, independent (judge's own model not among the items), then each judge."""
    sets = [(POOLED, list(items))]
    if any(it.judge_in_group for it in items):
        sets.append((INDEPENDENT, [it for it in items if not it.judge_in_group]))
    for judge in sorted({it.judge for it in items}):
        sets.append((judge, [it for it in items if it.judge == judge]))
    return [(name, its) for name, its in sets if its]


LB_COLUMNS = [
    ("n", "n"),
    ("questions", "questions"),
    ("mean_rank", "mean rank"),
    ("mean_score", "mean P(best)"),
    ("score_ci", "P(best) 95% CI"),
    ("p_accuracy", "P(acc)"),
    ("p_precision", "P(prec)"),
    ("win_rate", "win rate"),
    ("win_ci", "win 95% CI"),
]


def _modes(items: Sequence[Item]) -> list[str]:
    return [m for m in ("prediction", "full") if any(it.mode == m for it in items)]


def method_tables(items: Sequence[Item], n_boot: int, seed: int) -> list[Table]:
    method_items = [it for it in items if it.comparison == "methods"]
    tables = []
    for mode in _modes(method_items):
        mode_items = [it for it in method_items if it.mode == mode]
        rows: list[dict[str, Cell]] = []
        generators = [POOLED] + sorted({it.model for it in mode_items})
        for gen in generators:
            gen_items = [it for it in mode_items if gen in (POOLED, it.model)]
            for jset, its in judge_sets(gen_items):
                ci = jset in (POOLED, INDEPENDENT)
                for row in leaderboard(
                    its, lambda it: it.method, ci=ci, n_boot=n_boot, seed=seed
                ):
                    rows.append({"generator": gen, "judges": jset, **row})
        label = (
            "prediction only, all methods"
            if mode == "prediction"
            else "full reading, tarot vs I Ching"
        )
        full = Table(
            f"method_leaderboard_{mode}",
            f"Method leaderboard: {label}",
            [("generator", "generator"), ("judges", "judges"), ("entity", "method")]
            + LB_COLUMNS,
            rows,
            show=False,
        )
        tables += [
            full,
            full.view(
                full.title,
                lambda r: r["judges"] in (POOLED, INDEPENDENT),
                note=(
                    "Each judge call ranks one generator's readings for one (question, "
                    "seed) across methods. `independent` excludes judgments where the "
                    "judge is the generator. CIs bootstrap over questions."
                ),
            ),
            full.view(
                f"Method leaderboard by judge ({mode} mode, all generators)",
                lambda r: (
                    r["generator"] == POOLED
                    and r["judges"] not in (POOLED, INDEPENDENT)
                ),
                drop=("generator", "score_ci", "win_ci"),
            ),
            head_to_head(mode_items, mode),
        ]
    return tables


def head_to_head(items: Sequence[Item], mode: str) -> Table:
    by_judgment: dict[tuple, list[Item]] = defaultdict(list)
    for it in items:
        key = (it.question_id, it.seed, it.fixed_model, it.judge)
        by_judgment[key].append(it)
    wins: dict[tuple[str, str], int] = defaultdict(int)
    games: dict[tuple[str, str], int] = defaultdict(int)
    for its in by_judgment.values():
        for a, b in combinations(its, 2):
            for x, y in ((a, b), (b, a)):
                games[(x.method, y.method)] += 1
                wins[(x.method, y.method)] += x.rank < y.rank
    methods = sorted({it.method for it in items}, key=_entity_order)
    rows: list[dict[str, Cell]] = []
    for m in methods:
        row: dict[str, Cell] = {"method": m}
        for o in methods:
            g = games.get((m, o))
            row[o] = wins[(m, o)] / g if g else None
        rows.append(row)
    return Table(
        f"method_head_to_head_{mode}",
        f"Method head-to-head ({mode} mode, pooled): P(row ranked above column)",
        [("method", "method")] + [(m, m) for m in methods],
        rows,
    )


def model_tables(items: Sequence[Item], n_boot: int, seed: int) -> list[Table]:
    model_items = [it for it in items if it.comparison == "models"]
    tables = []
    for mode in _modes(model_items):
        mode_items = [it for it in model_items if it.mode == mode]
        rows: list[dict[str, Cell]] = []
        methods = ["all"] + sorted({it.method for it in mode_items}, key=_entity_order)
        for method in methods:
            m_items = [it for it in mode_items if method in ("all", it.method)]
            for jset, its in judge_sets(m_items):
                ci = jset in (POOLED, INDEPENDENT)
                for row in leaderboard(
                    its, lambda it: it.model, ci=ci, n_boot=n_boot, seed=seed
                ):
                    rows.append({"method": method, "judges": jset, **row})
        full = Table(
            f"model_leaderboard_{mode}",
            f"Model leaderboard ({mode} mode)",
            [("method", "method"), ("judges", "judges"), ("entity", "model")]
            + LB_COLUMNS,
            rows,
            show=False,
        )
        tables += [
            full,
            full.view(
                full.title,
                lambda r: r["judges"] in (POOLED, INDEPENDENT),
                note=(
                    "Each judge call ranks the generator models' readings for one "
                    "(question, seed, method). `independent` keeps only judgments "
                    "whose judge is not one of the ranked models (dropping single "
                    "self-judged rows would bias the comparison)."
                ),
            ),
            full.view(
                f"Model leaderboard by judge ({mode} mode, all methods)",
                lambda r: (
                    r["method"] == "all" and r["judges"] not in (POOLED, INDEPENDENT)
                ),
                drop=("method", "score_ci", "win_ci"),
            ),
        ]
    return tables


def self_preference_table(items: Sequence[Item]) -> Table:
    model_items = [it for it in items if it.comparison == "models"]
    rows: list[dict[str, Cell]] = []
    for mode in _modes(model_items):
        mode_items = [it for it in model_items if it.mode == mode]
        generators = {it.model for it in mode_items}
        for judge in sorted({it.judge for it in mode_items} & generators):
            own = [it for it in mode_items if it.model == judge]
            by_self = sum((it.acc() for it in own if it.judge == judge), Acc())
            baseline = [it for it in own if not it.judge_in_group] or [
                it for it in own if it.judge != judge
            ]
            by_others = sum((it.acc() for it in baseline), Acc())
            delta = (
                by_self.win_rate - by_others.win_rate
                if by_self.win_rate is not None and by_others.win_rate is not None
                else None
            )
            rows.append(
                {
                    "mode": mode,
                    "model": judge,
                    "n_self": by_self.n,
                    "win_self": by_self.win_rate,
                    "score_self": by_self.mean_score,
                    "n_others": by_others.n,
                    "win_others": by_others.win_rate,
                    "score_others": by_others.mean_score,
                    "delta": delta,
                    "flag": "SELF-PREFERENCE"
                    if delta is not None and delta >= SELF_PREFERENCE_THRESHOLD
                    else "",
                }
            )
    return Table(
        "self_preference",
        "Self-preference (model comparison)",
        [
            ("mode", "mode"),
            ("model", "model (as judge and generator)"),
            ("n_self", "n (self-judged)"),
            ("win_self", "win rate by itself"),
            ("score_self", "score by itself"),
            ("n_others", "n (baseline judges)"),
            ("win_others", "win rate by baseline judges"),
            ("score_others", "score by baseline judges"),
            ("delta", "win-rate delta"),
            ("flag", "flag"),
        ],
        rows,
        note=(
            "Baseline judges are those whose own model is not being ranked (or all "
            "other judges if there are none). Flagged when a judge rates its own "
            f"model's win rate at least {SELF_PREFERENCE_THRESHOLD:.2f} higher than "
            "the baseline does."
        ),
    )


def normalize_answer(s: str | None) -> str:
    return (s or "").strip().strip(".!\"'*").casefold()


def accuracy_table(
    questions: dict[str, Question],
    readings: Sequence[Reading],
    n_boot: int,
    seed: int,
) -> Table:
    scored = [
        r
        for r in readings
        if r.question_id in questions
        and questions[r.question_id].question_type in ("binary", "multiple_choice")
    ]
    cells: list[tuple[str, str, Callable[[Reading], bool]]] = [
        ("all", "all", lambda r: True)
    ]
    for method in sorted({str(r.method) for r in scored}, key=_entity_order):
        cells.append((method, "all", lambda r, m=method: r.method == m))
    for model in sorted({r.model for r in scored}):
        cells.append(("all", model, lambda r, m=model: r.model == m))
    for method in sorted({str(r.method) for r in scored}, key=_entity_order):
        for model in sorted({r.model for r in scored}):
            cells.append(
                (
                    method,
                    model,
                    lambda r, a=method, b=model: r.method == a and r.model == b,
                )
            )
    rows: list[dict[str, Cell]] = []
    for method, model, pred in cells:
        rs = [r for r in scored if pred(r)]
        if not rs:
            continue
        per_q: PerQuestion = defaultdict(lambda: defaultdict(Acc))
        for r in rs:
            ok = normalize_answer(r.answer) == normalize_answer(
                questions[r.question_id].resolved_answer
            )
            per_q[r.question_id]["x"] += Acc(1, 0, 0, float(ok), 1)
        acc = total(per_q)["x"]
        chance = [1 / len(questions[r.question_id].options or [1, 1]) for r in rs]
        rows.append(
            {
                "method": method,
                "model": model,
                "n": acc.n,
                "questions": len(per_q),
                "missing": sum(1 for r in rs if not r.answer),
                "accuracy": acc.win_rate,
                "ci": bootstrap(per_q, lambda a: a.win_rate, n_boot, seed).get("x"),
                "chance": sum(chance) / len(chance),
            }
        )
    return Table(
        "accuracy",
        "Objective accuracy (binary / multiple-choice questions)",
        [
            ("method", "method"),
            ("model", "model"),
            ("n", "readings"),
            ("questions", "questions"),
            ("missing", "no answer"),
            ("accuracy", "accuracy"),
            ("ci", "95% CI"),
            ("chance", "chance baseline"),
        ],
        rows,
        note="`answer` vs `resolved_answer` (case-insensitive). Chance = mean 1/#options.",
    )


def domain_tables(items: Sequence[Item], questions: dict[str, Question]) -> list[Table]:
    method_items = [
        it for it in items if it.comparison == "methods" and it.question_id in questions
    ]
    tables = []
    for mode in _modes(method_items):
        mode_items = [it for it in method_items if it.mode == mode]
        methods = sorted({it.method for it in mode_items}, key=_entity_order)
        by_domain: dict[str, list[Item]] = defaultdict(list)
        for it in mode_items:
            by_domain[str(questions[it.question_id].domain)].append(it)
        rows: list[dict[str, Cell]] = []
        for domain, its in sorted(by_domain.items()):
            tot = total(per_question(its, lambda it: it.method))
            row: dict[str, Cell] = {
                "domain": domain,
                "questions": len({it.question_id for it in its}),
            }
            for m in methods:
                row[f"{m}_score"] = tot[m].mean_score if m in tot else None
                row[f"{m}_win"] = tot[m].win_rate if m in tot else None
            rows.append(row)
        cols = [("domain", "domain"), ("questions", "questions")]
        for m in methods:
            cols += [(f"{m}_score", f"{m} score"), (f"{m}_win", f"{m} win rate")]
        tables.append(
            Table(
                f"domain_{mode}",
                f"Method scores by domain ({mode} mode, pooled)",
                cols,
                rows,
            )
        )
    return tables


def kendall_tau(a: Sequence[float], b: Sequence[float]) -> float:
    pairs = list(combinations(range(len(a)), 2))
    s = sum(
        (1 if (a[i] - a[j]) * (b[i] - b[j]) > 0 else -1)
        for i, j in pairs
        if (a[i] - a[j]) * (b[i] - b[j]) != 0
    )
    return s / len(pairs) if pairs else 0.0


def spearman_rho(a: Sequence[float], b: Sequence[float]) -> float:
    n = len(a)
    if n < 2:
        return 0.0
    d2 = sum((x - y) ** 2 for x, y in zip(a, b, strict=True))
    return 1 - 6 * d2 / (n * (n * n - 1))


def agreement_table(judgments: Sequence[Judgment]) -> Table:
    groups: dict[tuple, dict[str, dict[str, int]]] = defaultdict(dict)
    for j in judgments:
        ranks = {j.label_map[ri.label]: ri.rank for ri in j.ranking}
        groups[judgment_key(j)[:-1]][j.judge_model] = ranks
    stats: dict[tuple[str, str, str, str], list[tuple[float, float, bool]]] = (
        defaultdict(list)
    )
    for key, by_judge in groups.items():
        comparison, mode = key[1], key[2]
        for ja, jb in combinations(sorted(by_judge), 2):
            ra, rb = by_judge[ja], by_judge[jb]
            common = sorted(set(ra) & set(rb))
            if len(common) < 2:
                continue
            a = [ra[k] for k in common]
            b = [rb[k] for k in common]
            top_same = min(common, key=ra.__getitem__) == min(
                common, key=rb.__getitem__
            )
            stats[(comparison, mode, ja, jb)].append(
                (kendall_tau(a, b), spearman_rho(a, b), top_same)
            )
    rows: list[dict[str, Cell]] = []
    for (comparison, mode, ja, jb), vals in sorted(stats.items()):
        rows.append(
            {
                "comparison": comparison,
                "mode": mode,
                "judge_a": ja,
                "judge_b": jb,
                "groups": len(vals),
                "kendall": sum(v[0] for v in vals) / len(vals),
                "spearman": sum(v[1] for v in vals) / len(vals),
                "top1": sum(v[2] for v in vals) / len(vals),
            }
        )
    return Table(
        "judge_agreement",
        "Judge agreement",
        [
            ("comparison", "comparison"),
            ("mode", "mode"),
            ("judge_a", "judge A"),
            ("judge_b", "judge B"),
            ("groups", "shared groups"),
            ("kendall", "mean Kendall tau"),
            ("spearman", "mean Spearman rho"),
            ("top1", "same top item"),
        ],
        rows,
        note="Rank correlation between two judges on the same group of readings.",
    )


def latest_probes(
    probes: Iterable[KnowledgeProbe],
) -> dict[tuple[str, str], KnowledgeProbe]:
    return {(p.question_id, p.model): p for p in probes}


def probe_knew(p: KnowledgeProbe) -> bool:
    return p.knows_outcome == "yes" and p.correct is not False


def known_question_ids(probes: Iterable[KnowledgeProbe]) -> set[str]:
    return {qid for (qid, _), p in latest_probes(probes).items() if probe_knew(p)}


def probe_table(probes: Sequence[KnowledgeProbe], qids: Iterable[str]) -> Table:
    latest = latest_probes(probes)
    models = sorted({m for _, m in latest})
    rows: list[dict[str, Cell]] = []
    for qid in sorted(qids):
        row: dict[str, Cell] = {"question": qid}
        flags = []
        for m in models:
            p = latest.get((qid, m))
            if p is None:
                continue
            correct = {True: "correct", False: "wrong", None: "?"}[p.correct]
            answer = (p.stated_answer or "").replace("\n", " ")[:60]
            row[m] = f"{p.knows_outcome} / {correct}" + (
                f": {answer}" if answer else ""
            )
            if probe_knew(p):
                flags.append("knew")
            elif p.correct:
                flags.append("guessed right")
        row["flag"] = "EXCLUDE?" if "knew" in flags else ", ".join(sorted(set(flags)))
        if len(row) > 2 or row["flag"]:
            rows.append(row)
    return Table(
        "knowledge_probes",
        "Knowledge probes",
        [("question", "question")] + [(m, m) for m in models] + [("flag", "flag")],
        rows,
        note=(
            "Cells: knows_outcome / correctness of stated answer. `EXCLUDE?` marks "
            "questions where a tested model claimed to know the outcome and was not "
            "wrong; `--exclude-known` drops them from the report."
        ),
    )


DIVINATION_TERMS = re.compile(
    r"\b(cards?|tarot|atu|arcana|hexagrams?|trigrams?|i ching|yarrow|changing lines?|"
    r"the reading|divination|oracle|spread)\b",
    re.IGNORECASE,
)


def leakage_table(readings: Sequence[Reading]) -> Table:
    """Predictions mentioning divination would reveal the method to a prediction-mode judge."""
    agg: dict[tuple[str, str], list[int]] = defaultdict(lambda: [0, 0])
    examples: dict[tuple[str, str], str] = {}
    for r in readings:
        if r.method == Method.predict:
            continue
        key = (str(r.method), r.model)
        agg[key][0] += 1
        m = DIVINATION_TERMS.search(r.prediction)
        if m:
            agg[key][1] += 1
            examples.setdefault(key, f"{r.question_id} s{r.seed}: '{m.group(0)}'")
    rows: list[dict[str, Cell]] = [
        {
            "method": method,
            "model": model,
            "predictions": n,
            "mentions_divination": hits,
            "example": examples.get((method, model), ""),
        }
        for (method, model), (n, hits) in sorted(agg.items())
    ]
    return Table(
        "prediction_leakage",
        "Predictions that mention divination",
        [
            ("method", "method"),
            ("model", "model"),
            ("predictions", "predictions"),
            ("mentions_divination", "mentioning divination"),
            ("example", "first example"),
        ],
        rows,
        note="Simple keyword match; check examples by hand before trusting prediction-mode blinding.",
    )


def _usage_num(usage: dict | None, key: str) -> float:
    v = (usage or {}).get(key)
    return float(v) if isinstance(v, int | float) and not isinstance(v, bool) else 0.0


def cost_table(
    readings: Sequence[Reading],
    judgments: Sequence[Judgment],
    probes: Sequence[KnowledgeProbe] = (),
) -> Table:
    agg: dict[tuple[str, str], list[float]] = defaultdict(lambda: [0, 0.0, 0.0, 0.0])
    records = (
        [("probe", p.model, p.usage) for p in probes]
        + [("generation", r.model, r.usage) for r in readings]
        + [("judging", j.judge_model, j.usage) for j in judgments]
    )
    for stage, model, usage in records:
        a = agg[(stage, model)]
        a[0] += 1
        a[1] += _usage_num(usage, "cost")
        a[2] += _usage_num(usage, "prompt_tokens") + _usage_num(usage, "input_tokens")
        a[3] += _usage_num(usage, "completion_tokens") + _usage_num(
            usage, "output_tokens"
        )
    rows: list[dict[str, Cell]] = [
        {
            "stage": stage,
            "model": model,
            "calls": int(a[0]),
            "cost": a[1],
            "prompt_tokens": int(a[2]),
            "completion_tokens": int(a[3]),
        }
        for (stage, model), a in sorted(agg.items())
    ]
    if rows:
        rows.append(
            {
                "stage": "total",
                "model": "",
                "calls": sum(int(a[0]) for a in agg.values()),
                "cost": sum(a[1] for a in agg.values()),
                "prompt_tokens": sum(int(a[2]) for a in agg.values()),
                "completion_tokens": sum(int(a[3]) for a in agg.values()),
            }
        )
    return Table(
        "costs",
        "Cost (OpenRouter usage.cost, USD)",
        [
            ("stage", "stage"),
            ("model", "model"),
            ("calls", "calls"),
            ("cost", "cost $"),
            ("prompt_tokens", "prompt tokens"),
            ("completion_tokens", "completion tokens"),
        ],
        rows,
    )


def recorded_cost(
    readings: Iterable[Reading],
    judgments: Iterable[Judgment],
    probes: Iterable[KnowledgeProbe] = (),
) -> float:
    return (
        sum(_usage_num(r.usage, "cost") for r in readings)
        + sum(_usage_num(j.usage, "cost") for j in judgments)
        + sum(_usage_num(p.usage, "cost") for p in probes)
    )


def question_metadata_rows(questions: Iterable[Question]) -> list[dict[str, Cell]]:
    return [
        {
            "id": q.id,
            "domain": str(q.domain),
            "type": q.question_type,
            "context_date": str(q.latest_context_source_date),
            "event_date": str(q.event_date),
            "outcome_date": str(q.latest_outcome_source_date),
            "notes": q.notes or "",
        }
        for q in sorted(questions, key=lambda q: (str(q.domain), q.id))
    ]


def question_table(questions: Iterable[Question]) -> Table:
    return Table(
        "questions",
        "Questions",
        [
            ("id", "id"),
            ("domain", "domain"),
            ("type", "type"),
            ("context_date", "latest context source"),
            ("event_date", "event date"),
            ("outcome_date", "latest outcome source"),
            ("notes", "notes"),
        ],
        question_metadata_rows(questions),
    )


def coverage_table(readings: Sequence[Reading], judgments: Sequence[Judgment]) -> Table:
    counts: dict[tuple[str, str, str], int] = defaultdict(int)
    for r in readings:
        counts[("reading", str(r.method), r.model)] += 1
    for j in judgments:
        counts[(f"judgment ({j.comparison}, {j.mode})", "", j.judge_model)] += 1
    return Table(
        "coverage",
        "Coverage",
        [
            ("kind", "record"),
            ("method", "method"),
            ("model", "model / judge"),
            ("n", "n"),
        ],
        [
            {"kind": k, "method": m, "model": model, "n": n}
            for (k, m, model), n in sorted(counts.items())
        ],
    )


@dataclass
class Report:
    markdown: str
    tables: list[Table] = field(default_factory=list)
    excluded: list[str] = field(default_factory=list)


def build_report(
    questions: Sequence[Question],
    readings: Sequence[Reading],
    judgments: Sequence[Judgment],
    probes: Sequence[KnowledgeProbe] = (),
    out_dir: str | Path | None = None,
    *,
    exclude_known: bool = False,
    n_boot: int = 1000,
    seed: int = 0,
    title: str = "divination-bench report",
    total_spend: float | None = None,
) -> Report:
    """Build the report; if `out_dir` is given, write report.md and one CSV per table.

    Analyses use only the current record per key (superseded readings and judgments
    are dropped); the cost table counts every record, since all of them were paid for.
    """
    qmap = {q.id: q for q in questions}
    known = known_question_ids(p for p in probes if p.question_id in qmap)
    excluded = sorted(known) if exclude_known else []
    keep = set(qmap) - set(excluded)
    paid_readings = [r for r in readings if r.question_id in keep]
    paid_judgments = [j for j in judgments if j.question_id in keep]
    readings = current_readings(paid_readings)
    judgments = current_judgments(paid_judgments)
    used_qids = {r.question_id for r in readings} | {j.question_id for j in judgments}
    items = items_from_judgments(judgments)

    sections: list[tuple[str, list[Table]]] = [
        ("Method comparison", method_tables(items, n_boot, seed)),
        ("Objective accuracy", [accuracy_table(qmap, readings, n_boot, seed)]),
        (
            "Model comparison",
            model_tables(items, n_boot, seed) + [self_preference_table(items)],
        ),
        ("Per-domain breakdown", domain_tables(items, qmap)),
        ("Judge agreement", [agreement_table(judgments)]),
        ("Knowledge probes", [probe_table(probes, qmap)]),
        ("Prediction blinding", [leakage_table(readings)]),
        (
            "Cost and coverage",
            [
                cost_table(paid_readings, paid_judgments, probes),
                coverage_table(readings, judgments),
            ],
        ),
        ("Questions", [question_table(qmap[q] for q in sorted(used_qids or keep))]),
    ]
    lines = [
        f"# {title}",
        "",
        f"- Questions with data: {len(used_qids)} (of {len(qmap)} loaded)",
        f"- Readings: {len(readings)}; judgments: {len(judgments)}",
        f"- Recorded cost: ${recorded_cost(paid_readings, paid_judgments, probes):.2f}"
        + (
            f" (total run spend incl. discarded calls: ${total_spend:.2f})"
            if total_spend is not None
            else ""
        ),
        f"- Questions a tested model claimed to know: {len(known)}"
        + (f" (excluded: {', '.join(excluded)})" if excluded else " (not excluded)"),
        (
            "- Rankings come from successive choices (best of the remaining forecasts, "
            "repeated); win rate is the share of pairwise comparisons within a ranking "
            "that the entry won. P(best) pools the judge's accuracy and precision "
            "choice probabilities as sqrt(P_acc * P_prec), renormalised; P(acc) and "
            "P(prec) are the two components (precision is judged without the outcome)."
        ),
        "",
    ]
    tables: list[Table] = []
    for heading, ts in sections:
        lines += [f"## {heading}", ""]
        for t in ts:
            if t.show:
                lines.append(t.markdown())
            tables.append(t)
    md = "\n".join(lines).rstrip() + "\n"

    if out_dir is not None:
        out = Path(out_dir)
        out.mkdir(parents=True, exist_ok=True)
        (out / "report.md").write_text(md)
        csv_dir = out / "csv"
        csv_dir.mkdir(exist_ok=True)
        for t in tables:
            t.write_csv(csv_dir)
    return Report(md, tables, excluded)
