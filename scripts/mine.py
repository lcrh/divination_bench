"""Mine a run directory for qualitative tidbits: prophetic cards, oracle hits, divergence.

uv run python scripts/mine.py results/pilot [section ...]
"""

from __future__ import annotations

import json
import re
import statistics as st
import sys
from collections import defaultdict
from pathlib import Path

import yaml

RUN = Path(sys.argv[1] if len(sys.argv) > 1 else "results/pilot")
SECTIONS = set(sys.argv[2:])
QDIR = Path("data/questions")


def want(name: str) -> bool:
    return not SECTIONS or name in SECTIONS


def last_wins(path: Path, key) -> dict:
    out = {}
    for line in path.open():
        r = json.loads(line)
        out[key(r)] = r
    return out


readings = last_wins(
    RUN / "readings.jsonl",
    lambda r: (r["question_id"], r["method"], r["seed"], r["model"]),
)
judgments = last_wins(
    RUN / "judgments.jsonl",
    lambda j: (
        j["question_id"],
        j["comparison"],
        j["mode"],
        j["seed"],
        j["fixed_method"],
        j["fixed_model"],
    ),
)
judged = {
    (j["seed"], m.split("|")[1])
    for j in judgments.values()
    for m in j["label_map"].values()
}
readings = {k: r for k, r in readings.items() if (k[2], k[3]) in judged}
questions = {}
for p in QDIR.rglob("*.yaml"):
    q = yaml.safe_load(p.read_text())
    questions[q["id"]] = q

short = {
    "anthropic/claude-opus-5.5": "claude",
    "openai/gpt-6-astra": "gpt",
    "google/gemini-4-argon": "argon",
}


def words(s: str) -> set[str]:
    return set(re.findall(r"[a-z0-9]+", (s or "").lower()))


def jaccard(a: str, b: str) -> float:
    A, B = words(a), words(b)
    return len(A & B) / max(1, len(A | B))


# Per-reading score within its methods group, by mode.
scored = defaultdict(list)  # (mode) -> list of dicts
for j in judgments.values():
    if j["comparison"] != "methods":
        continue
    n = len(j["ranking"])
    for it in j["ranking"]:
        method, model = j["label_map"][it["label"]].split("|")
        r = readings.get((j["question_id"], method, j["seed"], model))
        if r is None:
            continue
        scored[j["mode"]].append(
            {
                "r": r,
                "rank": it["rank"],
                "n": n,
                "score": it["score"],
                "acc": it["p_accuracy"],
                "prec": it["p_precision"],
            }
        )

print(f"# {RUN}: {len(readings)} readings, {len(judgments)} judgments")
print({m: len(v) for m, v in scored.items()})


def table(rows, title, min_n=6, top=8):
    print(f"\n## {title}")
    agg = defaultdict(list)
    for name, x in rows:
        agg[name].append(x)
    stats = [(st.mean(v), len(v), k) for k, v in agg.items() if len(v) >= min_n]
    stats.sort(reverse=True)
    for m, n, k in stats[:top]:
        print(f"  {m:.2f}  n={n:3d}  {k}")
    print("  ...")
    for m, n, k in stats[-top:]:
        print(f"  {m:.2f}  n={n:3d}  {k}")


if want("cards"):
    for mode in ("prediction", "reading"):
        rows = scored.get(mode, [])
        tar = [x for x in rows if x["r"]["cast"] and "cards" in x["r"]["cast"]]
        ich = [x for x in rows if x["r"]["cast"] and "primary" in x["r"]["cast"]]
        win = lambda x: 1.0 if x["rank"] == 1 else 0.0
        table(
            [(c["name"], win(x)) for x in tar for c in x["r"]["cast"]["cards"]],
            f"{mode}: card win rate",
        )
        table(
            [
                (c.get("suit") or "Major Arcana", win(x))
                for x in tar
                for c in x["r"]["cast"]["cards"]
            ],
            f"{mode}: suit win rate",
            top=5,
        )
        table(
            [
                (
                    f"{x['r']['cast']['primary']['number']} {x['r']['cast']['primary']['english']}",
                    win(x),
                )
                for x in ich
            ],
            f"{mode}: primary hexagram win rate",
            min_n=4,
        )
        table(
            [
                (f"{len(x['r']['cast']['changing_lines'])} changing lines", win(x))
                for x in ich
            ],
            f"{mode}: changing lines",
            min_n=4,
            top=4,
        )

if want("hits"):
    print(
        "\n## Oracle hits: divined forecast ranked 1st, the same model's plain forecast last (prediction mode)"
    )
    groups = defaultdict(dict)
    for x in scored.get("prediction", []):
        r = x["r"]
        groups[(r["question_id"], r["seed"], r["model"])][r["method"]] = x
    hits = []
    for (qid, seed, model), g in groups.items():
        if "predict" not in g:
            continue
        for m in ("tarot", "iching"):
            if (
                m in g
                and g[m]["rank"] == 1
                and g["predict"]["rank"] == g["predict"]["n"]
                and g[m]["acc"] > 0.6
            ):
                hits.append((g[m]["acc"] - g["predict"]["acc"], qid, seed, model, m, g))
    hits.sort(reverse=True)
    print(f"{len(hits)} hits")
    for _, qid, seed, model, m, g in hits[: int((SECTIONS and 40) or 12)]:
        q = questions[qid]
        print(
            f"\n### {qid} seed={seed} {short[model]} {m}  acc {g[m]['acc']:.2f} vs predict {g['predict']['acc']:.2f}"
        )
        print("OUTCOME:", q["resolved_answer"][:300])
        print(
            "CAST:",
            g[m]["r"]["cast_text"].split("\n\nLines")[0].replace("\n", " / ")[:300],
        )
        print("DIVINED:", g[m]["r"]["prediction"][:500])
        print("PLAIN:", g["predict"]["r"]["prediction"][:400])

if want("diverge"):
    print(
        "\n## How much do the cards move the forecast? Jaccard(divined prediction, own plain prediction)"
    )
    sims = defaultdict(list)
    for (qid, method, seed, model), r in readings.items():
        if method not in ("tarot", "iching"):
            continue
        p = readings.get((qid, "predict", seed, model))
        if p:
            sims[(short[model], method)].append(
                jaccard(r["prediction"], p["prediction"])
            )
    for k, v in sorted(sims.items()):
        print(f"  {k}: mean {st.mean(v):.3f}  n={len(v)}")
    # Across seeds, same model and method: how stable is the plain prediction?
    seeds = defaultdict(list)
    for (qid, method, seed, model), r in readings.items():
        if method in ("tarot", "iching", "predict"):
            seeds[(qid, method, model)].append(r["prediction"])
    stab = defaultdict(list)
    for (qid, method, model), ps in seeds.items():
        for i in range(len(ps)):
            for k in range(i + 1, len(ps)):
                stab[(short[model], method)].append(jaccard(ps[i], ps[k]))
    print("  cross-seed self-similarity (same model+method, different seeds):")
    for k, v in sorted(stab.items()):
        print(f"  {k}: mean {st.mean(v):.3f}  n={len(v)}")


def extras(name: str) -> dict:
    p = RUN / "extras" / f"{name}.jsonl"
    out = {json.loads(x)["key"]: json.loads(x) for x in p.open()} if p.exists() else {}
    return {
        k: r
        for k, r in out.items()
        if len(parts := k.split("|")) < 4 or (int(parts[2]), parts[3]) in judged
    }


if want("coldread"):
    print(
        "\n## Cold-reading test: P(Jev matches the text to the real outcome rather than a plausible fake)"
    )
    cr = extras("coldread")
    per = defaultdict(list)  # (qid, method, seed, model) -> p_real over both orders
    for k, r in cr.items():
        qid, method, seed, model, _ = k.split("|")
        per[(qid, method, int(seed), model)].append(r["p_real"])
    by = defaultdict(list)
    byq = defaultdict(list)
    for (qid, method, seed, model), v in per.items():
        if len(v) == 2:
            by[(method, short[model])].append(st.mean(v))
            by[(method, "both")].append(st.mean(v))
            byq[(qid, method.replace("_reading", "_r"))].append(st.mean(v))
    for k, v in sorted(by.items()):
        print(
            f"  {k}: mean P(real) {st.mean(v):.3f}  real preferred {st.mean([x > 0.5 for x in v]):.2f}  n={len(v)}"
        )
    for meth in ("predict", "tarot_r", "iching_r"):
        rows = sorted(
            ((st.mean(v), q) for (q, m), v in byq.items() if m == meth), reverse=True
        )
        print(f"  {meth} best: " + ", ".join(f"{q[:28]} {s:.2f}" for s, q in rows[:6]))
        print(
            f"  {meth} worst: " + ", ".join(f"{q[:28]} {s:.2f}" for s, q in rows[-6:])
        )
    pos = [r["p_real"] for k, r in cr.items() if k.endswith("|1")]
    neg = [r["p_real"] for k, r in cr.items() if k.endswith("|0")]
    print(
        f"  position check: P(real) when real is A {st.mean(pos):.3f}, when B {st.mean(neg):.3f}"
    )

if want("called"):
    print(
        "\n## Called it: P(Jev says the text gets the main point right), averaged over both orders"
    )
    cl = extras("called")
    per = defaultdict(list)
    for k, r in cl.items():
        qid, method, seed, model, _ = k.split("|")
        per[(qid, method, int(seed), model)].append(r["p_right"])
    per = {k: st.mean(v) for k, v in per.items() if len(v) == 2}
    by = defaultdict(list)
    byq = defaultdict(lambda: defaultdict(list))
    for (qid, method, seed, model), p in per.items():
        by[(method, short[model])].append(p > 0.5)
        by[(method, "both")].append(p > 0.5)
        byq[qid][method].append(p > 0.5)
    for k, v in sorted(by.items()):
        print(f"  {k}: called it {st.mean(v):.3f}  n={len(v)}")
    print(
        "  per question (called-it rate over 12 forecasts: predict / tarot / iching):"
    )
    rows = []
    for qid, d in byq.items():
        if all(m in d for m in ("predict", "tarot", "iching")):
            rows.append(
                (st.mean(d["predict"]), st.mean(d["tarot"]), st.mean(d["iching"]), qid)
            )
    rows.sort()
    for p, t, i, qid in rows:
        flag = (
            "  <-- oracle"
            if max(t, i) - p >= 0.25
            else ("  <-- reason" if p - max(t, i) >= 0.25 else "")
        )
        print(f"    {p:.2f} / {t:.2f} / {i:.2f}  {qid}{flag}")
    upsets = [r for r in rows if r[0] <= 0.25]
    if upsets:
        print(
            f"  on {len(upsets)} questions plain prediction mostly missed (<=25%):"
            f" predict {st.mean(r[0] for r in upsets):.2f}, tarot {st.mean(r[1] for r in upsets):.2f},"
            f" iching {st.mean(r[2] for r in upsets):.2f}"
        )
        easy = [r for r in rows if r[0] >= 0.75]
        print(
            f"  on {len(easy)} questions plain prediction mostly hit (>=75%):"
            f" predict {st.mean(r[0] for r in easy):.2f}, tarot {st.mean(r[1] for r in easy):.2f},"
            f" iching {st.mean(r[2] for r in easy):.2f}"
        )

if want("changed"):
    print(
        "\n## Did the cards change the forecast? (Jev: plain vs divined forecast, same model and seed)"
    )
    ch = extras("changed")
    groups = defaultdict(dict)
    for x in scored.get("prediction", []):
        r = x["r"]
        groups[(r["question_id"], r["seed"], r["model"])][r["method"]] = x
    by = defaultdict(list)
    effect = defaultdict(list)
    for k, r in ch.items():
        qid, method, seed, model = k.split("|")
        d = r["p_different"] > 0.5
        by[(short[model], method)].append(d)
        g = groups.get((qid, int(seed), model), {})
        if method in g and "predict" in g:
            effect[(method, "changed" if d else "same")].append(
                g[method]["acc"] - g["predict"]["acc"]
            )
    for k, v in sorted(by.items()):
        print(f"  {k}: changed the call {st.mean(v):.2f}  n={len(v)}")
    for k, v in sorted(effect.items()):
        print(f"  {k}: mean P(acc) divined minus plain {st.mean(v):+.3f}  n={len(v)}")
    byq = defaultdict(list)
    for k, r in ch.items():
        byq[k.split("|")[0]].append(r["p_different"] > 0.5)
    rows = sorted(((st.mean(v), q) for q, v in byq.items()), reverse=True)
    print("  most swayed: " + ", ".join(f"{q[:30]} {s:.2f}" for s, q in rows[:8]))
    print("  least swayed: " + ", ".join(f"{q[:30]} {s:.2f}" for s, q in rows[-8:]))

if want("length"):
    print("\n## Length vs win (models comparisons)")
    for mode in ("full", "prediction", "reading"):
        wins = defaultdict(list)
        longer_wins = []
        for j in judgments.values():
            if j["comparison"] != "models" or j["mode"] != mode:
                continue
            items = []
            for it in j["ranking"]:
                method, model = j["label_map"][it["label"]].split("|")
                r = readings.get((j["question_id"], method, j["seed"], model))
                text = (
                    r["reading"]
                    if mode == "reading"
                    else (
                        r["prediction"]
                        if mode == "prediction"
                        else (r["reading"] or "") + r["prediction"]
                    )
                )
                items.append((it["score"], len(text.split()), short[model]))
                wins[short[model]].append(1.0 if it["rank"] == 1 else 0.0)
            if len(items) == 2 and items[0][1] != items[1][1]:
                longer = max(items, key=lambda t: t[1])
                longer_wins.append(
                    1.0 if longer[0] == max(i[0] for i in items) else 0.0
                )
        if longer_wins:
            print(
                f"  {mode}: win rate { {k: round(st.mean(v), 2) for k, v in wins.items()} }"
                f"  longer text wins {st.mean(longer_wins):.2f} (n={len(longer_wins)})"
            )
    for mode in ("prediction", "reading"):
        lens = defaultdict(list)
        for (qid, method, seed, model), r in readings.items():
            text = r["reading"] if mode == "reading" else r["prediction"]
            if (mode == "reading") == method.endswith("_reading") and text:
                lens[(short[model], method)].append(len(text.split()))
        for k, v in sorted(lens.items()):
            print(f"  words {mode} {k}: {st.mean(v):.0f}")
