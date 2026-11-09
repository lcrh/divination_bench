"""Render the README's plots into docs/img/.

uv run --with matplotlib python scripts/plots.py results/pilot
"""

from __future__ import annotations

import csv
import json
import statistics as st
import sys
from collections import defaultdict
from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np
from matplotlib import font_manager

RUN = Path(sys.argv[1] if len(sys.argv) > 1 else "results/pilot")
OUT = Path("docs/img")
OUT.mkdir(parents=True, exist_ok=True)

INK = "#0b0a1a"
GOLD = "#d9b45a"
PALE = "#e9e2cf"
DIM = "#8a83a8"
METHOD_COLOURS = {
    "predict": "#9fc5e8",
    "tarot": "#c0392b",
    "iching": "#2fa37b",
    "tarot_reading": "#e67e9a",
    "iching_reading": "#7fd6b0",
    "background": "#8a83a8",
}
METHOD_NAMES = {
    "predict": "Pure Reason",
    "tarot": "Thoth Tarot",
    "iching": "I Ching",
    "tarot_reading": "Tarot reading\n(no prediction)",
    "iching_reading": "I Ching reading\n(no prediction)",
    "background": "The briefing\nitself (control)",
}
MODEL_COLOURS = {
    "anthropic/claude-opus-5.5": "#e8955a",
    "openai/gpt-6-astra": "#5ad1c8",
    "google/gemini-4-argon": "#8fa8ff",
}
MODEL_NAMES = {
    "anthropic/claude-opus-5.5": "Claude Opus 5.5",
    "openai/gpt-6-astra": "GPT-6 Astra",
    "google/gemini-4-argon": "Gemini 4 Argon",
}
SUIT_COLOURS = {
    "Wands": "#e0663a",
    "Cups": "#4f8fd6",
    "Swords": "#c9ccd6",
    "Disks": "#7fbf5a",
    None: GOLD,
}

SUPP = Path("/System/Library/Fonts/Supplemental")
for f in ("Copperplate.ttc", "Baskerville.ttc"):
    if (SUPP / f).exists():
        font_manager.fontManager.addfont(str(SUPP / f))
TITLE_FONT = "Copperplate" if (SUPP / "Copperplate.ttc").exists() else "serif"
BODY_FONT = "Baskerville" if (SUPP / "Baskerville.ttc").exists() else "serif"

mpl.rcParams.update(
    {
        "font.family": BODY_FONT,
        "font.size": 12,
        "text.color": PALE,
        "axes.labelcolor": PALE,
        "xtick.color": PALE,
        "ytick.color": PALE,
        "axes.edgecolor": GOLD,
        "figure.facecolor": INK,
        "axes.facecolor": INK,
        "savefig.facecolor": INK,
        "axes.spines.top": False,
        "axes.spines.right": False,
    }
)


def starfield(fig, n=260, seed=7):
    rng = np.random.default_rng(seed)
    ax = fig.add_axes([0, 0, 1, 1], zorder=-10)
    ax.set_axis_off()
    ax.scatter(
        rng.random(n), rng.random(n), s=rng.random(n) ** 3 * 9, c=PALE, alpha=0.35, lw=0
    )
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)


def titled(fig, title, subtitle):
    fig.text(
        0.5,
        0.955,
        title,
        ha="center",
        va="top",
        fontsize=21,
        color=GOLD,
        family=TITLE_FONT,
    )
    fig.text(
        0.5,
        0.885,
        subtitle,
        ha="center",
        va="top",
        fontsize=12,
        color=DIM,
        style="italic",
    )


def save(fig, name):
    fig.savefig(OUT / name, dpi=160)
    plt.close(fig)
    print("wrote", OUT / name)


def last_wins(path, key):
    out = {}
    for line in path.open():
        r = json.loads(line)
        out[key(r)] = r
    return out


def rows(name, sub=""):
    p = RUN / sub / "csv" / name
    return list(csv.DictReader(p.open())) if p.exists() else []


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
# Unjudged (model, seed) cells, e.g. a partially generated seed, are left out everywhere.
judged = {
    (j["seed"], m.split("|")[1])
    for j in judgments.values()
    for m in j["label_map"].values()
}
readings = {k: r for k, r in readings.items() if (k[2], k[3]) in judged}


def extras(name):
    p = RUN / "extras" / f"{name}.jsonl"
    out = [json.loads(x) for x in p.open()] if p.exists() else []
    return [
        r
        for r in out
        if len(parts := r["key"].split("|")) < 4 or (int(parts[2]), parts[3]) in judged
    ]


# 1. The leaderboard of mystic power.
def leaderboard():
    data = {
        r["entity"]: r
        for r in rows("method_leaderboard_prediction.csv")
        if r["generator"] == "pooled" and r["judges"] == "pooled"
    }
    order = ["predict", "tarot", "iching"]
    fig = plt.figure(figsize=(9, 4.8))
    starfield(fig)
    titled(
        fig,
        "The Leaderboard of Mystic Power",
        "share of head-to-head match-ups won, prediction mode, 95% CI over questions",
    )
    ax = fig.add_axes([0.2, 0.14, 0.72, 0.62])
    for i, m in enumerate(order):
        r = data[m]
        w, lo, hi = float(r["win_rate"]), float(r["win_ci_lo"]), float(r["win_ci_hi"])
        ax.barh(
            i,
            w,
            color=METHOD_COLOURS[m],
            height=0.62,
            alpha=0.9,
            edgecolor=GOLD,
            lw=0.8,
        )
        ax.errorbar(w, i, xerr=[[w - lo], [hi - w]], color=PALE, capsize=5, lw=1.4)
        ax.text(
            hi + 0.015,
            i,
            f"{w:.0%}",
            va="center",
            color=PALE,
            fontsize=14,
            family=TITLE_FONT,
        )
    ax.axvline(0.5, color=GOLD, ls=(0, (2, 3)), lw=1)
    ax.text(
        0.5, 2.55, "a coin flip", color=GOLD, ha="center", fontsize=10, style="italic"
    )
    ax.set_yticks(
        range(3), [METHOD_NAMES[m] for m in order], fontsize=14, family=TITLE_FONT
    )
    ax.set_xlim(0, 0.8)
    ax.set_ylim(2.75, -0.6)
    ax.xaxis.set_major_formatter(mpl.ticker.PercentFormatter(1, decimals=0))
    save(fig, "leaderboard.png")


# 2. Divination works exactly when reason fails.
def upsets():
    per = defaultdict(list)
    for r in extras("called"):
        qid, method, seed, model, _ = r["key"].split("|")
        per[(qid, method, seed, model)].append(r["p_right"])
    byq = defaultdict(lambda: defaultdict(list))
    for (qid, method, _, _), v in per.items():
        if len(v) == 2 and method in ("predict", "tarot", "iching"):
            byq[qid][method].append(st.mean(v) > 0.5)
    rates = {
        q: {m: st.mean(v) for m, v in d.items()} for q, d in byq.items() if len(d) == 3
    }
    buckets = {
        "when reason\nwas right": [q for q, d in rates.items() if d["predict"] >= 0.75],
        "when reason\nwas wrong": [q for q, d in rates.items() if d["predict"] <= 0.25],
    }
    fig = plt.figure(figsize=(9, 5.2))
    starfield(fig, seed=3)
    titled(
        fig,
        "The Cards Favour the Underdog",
        "how often each method called the headline outcome, by how plain reasoning fared",
    )
    ax = fig.add_axes([0.1, 0.17, 0.85, 0.6])
    width = 0.26
    for bi, (label, qs) in enumerate(buckets.items()):
        for mi, m in enumerate(("predict", "tarot", "iching")):
            v = st.mean(rates[q][m] for q in qs)
            x = bi + (mi - 1) * width
            ax.bar(
                x,
                v,
                width * 0.92,
                color=METHOD_COLOURS[m],
                edgecolor=GOLD,
                lw=0.8,
                label=METHOD_NAMES[m] if bi == 0 else None,
            )
            ax.text(
                x,
                v + 0.02,
                f"{v:.0%}",
                ha="center",
                color=PALE,
                fontsize=13,
                family=TITLE_FONT,
            )
    ax.set_xticks(
        [0, 1], [f"{k}\n({len(v)} questions)" for k, v in buckets.items()], fontsize=12
    )
    ax.set_ylim(0, 1.08)
    ax.yaxis.set_major_formatter(mpl.ticker.PercentFormatter(1, decimals=0))
    ax.legend(frameon=False, loc="upper right", fontsize=12)
    save(fig, "upsets.png")


def card_stats(mode):
    agg = defaultdict(list)
    for j in judgments.values():
        if j["comparison"] != "methods" or j["mode"] != mode:
            continue
        for it in j["ranking"]:
            method, model = j["label_map"][it["label"]].split("|")
            r = readings.get((j["question_id"], method, j["seed"], model))
            if r and r["cast"] and "cards" in r["cast"]:
                for c in r["cast"]["cards"]:
                    agg[(c["name"], c.get("suit"))].append(
                        1.0 if it["rank"] == 1 else 0.0
                    )
    return {k: (st.mean(v), len(v)) for k, v in agg.items()}


# 3. The almanac of prophetic cards.
def cards():
    stats = card_stats("prediction")
    ranked = sorted(((m, n, k) for k, (m, n) in stats.items() if n >= 10), reverse=True)
    pick = ranked[:7] + ranked[-7:]
    fig = plt.figure(figsize=(9, 7.4))
    starfield(fig, seed=11)
    titled(
        fig,
        "The Almanac of Prophetic Cards",
        "share of three-way match-ups won when the card was drawn (chance: 1 in 3)",
    )
    ax = fig.add_axes([0.36, 0.08, 0.58, 0.74])
    for i, (m, n, (name, suit)) in enumerate(pick):
        y = i + (0.8 if i >= 7 else 0)
        ax.barh(
            y,
            m,
            color=SUIT_COLOURS.get(suit, GOLD),
            height=0.7,
            edgecolor=GOLD,
            lw=0.6,
            alpha=0.92,
        )
        ax.text(
            m + 0.012, y, f"{m:.0%}  (n={n})", va="center", fontsize=10.5, color=PALE
        )
    ax.set_yticks(
        [i + (0.8 if i >= 7 else 0) for i in range(len(pick))],
        [p[2][0] for p in pick],
        fontsize=11.5,
    )
    ax.axvline(1 / 3, color=GOLD, ls=(0, (2, 3)), lw=1)
    ax.set_ylim(len(pick) + 0.5, -0.8)
    ax.set_xlim(0, 1)
    ax.xaxis.set_major_formatter(mpl.ticker.PercentFormatter(1, decimals=0))
    handles = [
        mpl.patches.Patch(color=c, label=s or "Major Arcana")
        for s, c in SUIT_COLOURS.items()
    ]
    ax.legend(handles=handles, frameon=False, loc="lower right", fontsize=10)
    save(fig, "cards.png")


# 4. Real timeline or its evil twin?
def coldread():
    per = defaultdict(list)
    for r in extras("coldread"):
        qid, method, seed, model, _ = r["key"].split("|")
        per[(qid, method, seed, model)].append(r["p_real"])
    by = defaultdict(list)
    for (_, method, _, _), v in per.items():
        if len(v) == 2:
            by[method].append(st.mean(v))
    ctrl = defaultdict(list)
    for r in extras("coldread-control"):
        ctrl[r["key"].split("|")[0]].append(r["p_real"])
    by["background"] = [st.mean(v) for v in ctrl.values()]
    order = [
        "predict",
        "tarot",
        "iching",
        "background",
        "tarot_reading",
        "iching_reading",
    ]
    fig = plt.figure(figsize=(9.5, 5.4))
    starfield(fig, seed=5)
    titled(
        fig,
        "The Real Timeline, or Its Evil Twin?",
        "Jev's probability that a text describes what really happened rather than a plausible fake",
    )
    ax = fig.add_axes([0.08, 0.2, 0.88, 0.56])
    rng = np.random.default_rng(0)
    for i, m in enumerate(order):
        v = np.array(by[m])
        ax.scatter(
            i + rng.normal(0, 0.07, len(v)),
            v,
            s=6,
            color=METHOD_COLOURS[m],
            alpha=0.25,
            lw=0,
        )
        ax.scatter(i, v.mean(), s=260, marker="*", color=GOLD, edgecolor=INK, zorder=5)
        ax.text(
            i + 0.18,
            v.mean(),
            f"{v.mean():.2f}",
            va="center",
            color=GOLD,
            fontsize=13,
            family=TITLE_FONT,
        )
    ax.axhline(0.5, color=PALE, ls=(0, (2, 3)), lw=1)
    ax.text(
        len(order) - 0.5,
        0.52,
        "coin flip",
        color=PALE,
        ha="right",
        fontsize=10,
        style="italic",
    )
    ax.set_xticks(range(len(order)), [METHOD_NAMES[m] for m in order], fontsize=11)
    ax.set_ylim(-0.03, 1.03)
    ax.set_ylabel("P(real outcome)")
    save(fig, "coldread.png")


# 5. Model horoscopes: precision vs accuracy.
def models():
    # Seeds where all three models were ranked together.
    data = [
        r
        for r in rows("model_leaderboard_prediction.csv", "seeds-0-1-2")
        if r["method"] == "all" and r["judges"] == "pooled"
    ]
    fig = plt.figure(figsize=(8.5, 6.4))
    starfield(fig, seed=9)
    titled(
        fig,
        "Horoscopes of the Oracles",
        "three-way model match-ups, prediction mode: being right vs sounding sure",
    )
    ax = fig.add_axes([0.13, 0.12, 0.8, 0.68])
    offsets = {
        "anthropic/claude-opus-5.5": ((40, 34), "left"),
        "openai/gpt-6-astra": ((40, -34), "left"),
        "google/gemini-4-argon": ((36, 0), "left"),
    }
    for r in data:
        m = r["entity"]
        x, y, w = float(r["p_accuracy"]), float(r["p_precision"]), float(r["win_rate"])
        ax.scatter(
            x,
            y,
            s=1800 * w,
            color=MODEL_COLOURS.get(m, GOLD),
            alpha=0.8,
            edgecolor=GOLD,
            lw=1.5,
        )
        (dx, dy), ha = offsets.get(m, ((0, -40), "center"))
        ax.annotate(
            f"{MODEL_NAMES.get(m, m)}\nwins {w:.0%}",
            (x, y),
            xytext=(dx, dy),
            textcoords="offset points",
            ha=ha,
            va="center",
            fontsize=12,
            family=TITLE_FONT,
            color=PALE,
            arrowprops={"arrowstyle": "-", "color": DIM, "lw": 0.8},
        )
    xs = [float(r["p_accuracy"]) for r in data] + [
        float(r["p_precision"]) for r in data
    ]
    lo, hi = min(xs) - 0.12, max(xs) + 0.12
    ax.plot([lo, hi], [lo, hi], color=DIM, ls=(0, (2, 3)), lw=1)
    ax.set_xlim(lo, hi)
    ax.set_ylim(lo, hi)
    for x, y, text, ha in (
        (lo + 0.01, hi - 0.01, "the confident prophet\n(bold, often wrong)", "left"),
        (hi - 0.01, lo + 0.01, "the timid seer\n(right, but hedges)", "right"),
    ):
        ax.text(
            x,
            y,
            text,
            ha=ha,
            va="top" if y > lo + 0.05 else "bottom",
            color=DIM,
            fontsize=11,
            style="italic",
        )
    ax.set_xlabel("P(most accurate)  ·  judged with the outcome")
    ax.set_ylabel("P(most precise)  ·  judged without it")
    save(fig, "models.png")


# 6. How often the cards changed the model's mind.
def changed():
    by = defaultdict(list)
    for r in extras("changed"):
        model = r["key"].split("|")[3]
        by[model].append(r["p_different"] > 0.5)
    ms = [m for m in MODEL_COLOURS if m in by]
    fig = plt.figure(figsize=(9, 4.4))
    starfield(fig, seed=13)
    titled(
        fig,
        "Faith in the Cards",
        "share of divined forecasts that changed the model's own plain call",
    )
    ax = fig.add_axes([0.25, 0.14, 0.68, 0.6])
    for i, m in enumerate(ms):
        v = st.mean(by[m])
        ax.barh(i, 1, color="#1c1936", height=0.55, edgecolor=GOLD, lw=0.6)
        ax.barh(i, v, color=MODEL_COLOURS[m], height=0.55)
        ax.text(
            v + 0.02,
            i,
            f"{v:.0%} heeded the cards",
            va="center",
            color=PALE,
            fontsize=12,
        )
    ax.set_yticks(
        range(len(ms)), [MODEL_NAMES[m] for m in ms], fontsize=13, family=TITLE_FONT
    )
    ax.set_xlim(0, 1)
    ax.set_ylim(len(ms) - 0.4, -0.6)
    ax.xaxis.set_major_formatter(mpl.ticker.PercentFormatter(1, decimals=0))
    save(fig, "changed.png")


for fn in (leaderboard, upsets, cards, coldread, models, changed):
    fn()
