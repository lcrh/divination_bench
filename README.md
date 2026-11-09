# divination-bench

A just-for-fun benchmark: can LLMs predict the future better by casting a
**Thoth tarot** spread or an **I Ching** hexagram than by simply forecasting?

Each model is asked about real events that resolved *after* its training cutoff.
For every question it produces readings with three methods:

| method    | what the model sees                                      | output                              |
|-----------|----------------------------------------------------------|-------------------------------------|
| `tarot`   | a deterministic 3-card Thoth draw (no reversals)         | full reading + standalone prediction |
| `iching`  | a deterministic yarrow-stalk hexagram (with moving lines) | full reading + standalone prediction |
| `predict` | nothing extra                                            | prediction only                     |
| `tarot_reading` / `iching_reading` | the same draw as `tarot` / `iching`, with the instruction to analyse the situation deeply and make no specific predictions | reading only |

Reading-only methods are judged in their own `reading` mode: Jev is asked which
reading best describes what actually happened, and which is most specific and
concrete about the situation (without seeing the outcome).

A decision model ([TypeSafe Jev](https://openrouter.ai/typesafe/jev-1.13), via
OpenRouter's Decisions API) then ranks the readings against what actually happened.

## Design

**Questions** (`data/questions/<domain>/<id>.yaml`, template in
`data/questions/_example.yaml.txt`). Questions are open-ended ("what will
happen?") across uncorrelated events and domains, including "what is X" questions
about things unknown before the cutoff. Each has a neutral question, type
(`open`, or `binary` / `multiple_choice` with options), resolution criteria, a
context summary that does not leak the outcome, dated context sources, the
event date, an outcome summary, the resolved answer and dated outcome sources.
`validate` prints, per question, the latest context source date, event date
and latest outcome source date, and checks every event is after the documented
`model_cutoffs` (max of training cutoff and release date) of every tested
model. Reserve questions (`backup: true`) are skipped unless `--include-backups`.

**Casting** is deterministic in `sha256(question_id|method|seed)`, so every
question gets its own draw, both models get the same draw for a given seed, and
`cast` can reproduce any draw. Models see the draw, not the randomness.

**Reading → standalone prediction.** Divination readings end with a
`prediction` that must not mention cards, hexagrams or divination, plus an
`answer` (one of the options) for binary / multiple-choice questions. This is
what makes tarot, I Ching and plain prediction directly comparable.

**Judging.** Each group of 2-3 anonymised forecasts (`forecast A`, `forecast B`,
... with labels shuffled deterministically per (group, judge)) is ranked by
*successive choice*: Jev picks the best of the remaining forecasts, that one is
removed, and it picks again (a Plackett-Luce ranking). Each pick combines two
Decisions-API `choice` questions, asked in separate calls:

- **accuracy**: which forecast's claims best match what actually happened. Jev
  sees the question, resolution criteria, outcome summary, resolved answer and
  dated outcome excerpts.
- **precision**: which forecast is most precise and committal. Jev sees only the
  question and pre-event background, so knowing the outcome cannot colour it.

The two probability vectors are combined with a log-linear (geometric) opinion
pool, `P(i) ∝ sqrt(P_acc(i) · P_prec(i))`: being right about a vague forecast,
or precise about a wrong one, both score low. Every round is asked in all cyclic
rotations of the remaining forecasts and averaged, so each forecast appears in
every position. A 3-way ranking takes 10 calls (about $0.0005).

| comparison | fixed                    | mode `prediction`                   | mode `full`                             |
|------------|--------------------------|-------------------------------------|-----------------------------------------|
| `methods`  | question, seed, model    | tarot vs iching vs predict (headline) | tarot vs iching, reading + prediction |
| `models`   | question, seed, method   | generator models, prediction only   | generator models, reading + prediction (not `predict`) |

In `prediction` mode the judge is not told how items were produced.

The rubric: the central outcome matters most; specific details count only if
they came true and count against a forecast if false; restating known
background, vague or unfalsifiable claims earn nothing; style, length and
symbolism are ignored. In `full` mode, concrete claims in the reading count as
part of the forecast. Malformed answers are retried up to twice.

The report ranks by mean rank and pairwise win rate, and also shows mean pooled
P(best) and its two components, P(acc) and P(prec), from the first round.

**Caveats.**
- *Judge strength*: Jev is a small, cheap decision model, not a frontier LLM.
  Its choice probabilities are often near one-hot, so the rank order carries
  most of the signal.
- *Self-preference*: Jev is not a tested model, so there is none. The report's
  `independent` rows and self-preference table only matter if tested models are
  added as judges with `--judges`.
- *Leakage*: besides the documented cutoffs, a knowledge probe asks each tested
  model whether it already knows each outcome. `report --exclude-known` drops
  questions a model claimed to know (and did not get wrong).
- Small n: CIs are 95% bootstrap intervals resampling questions.

## Running

```bash
uv sync
export OPENROUTER_API_KEY=...            # not needed for --mock

uv run divination-bench validate          # check questions + date metadata
uv run divination-bench cast brazil-presidential-runoff-2026 --method tarot --seed 0
uv run divination-bench run --mock --run dry --limit 3   # offline end-to-end dry run
uv run divination-bench estimate          # rough cost from OpenRouter pricing
```

A real run, step by step. Every stage is resumable: rerunning skips what is
already in the run directory, so you can pilot one question to check costs
(`--limit 1 --seeds 0`) and later widen the same run with more questions, seeds,
models or methods. Each record carries a fingerprint of its exact request; if a
question or prompt is edited, only the affected readings and rankings are redone
(and a ranking is redone when a new reading joins its group).

```bash
uv run divination-bench probe    --run main --budget 120
uv run divination-bench generate --run main --budget 120
uv run divination-bench judge    --run main --budget 120
uv run divination-bench report   --run main [--exclude-known]
# or all at once:
uv run divination-bench run --run main --budget 120
```

`--budget` caps the total spend of the run directory: every paid call is also
logged to `spend.jsonl`, so calls whose output was discarded (parse failures,
superseded records) still count. Narrow a run with `--questions id1,id2`,
`--limit N`, `--models`, `--judges`, `--methods`, `--seeds`, `--modes`,
`--comparisons`; tune with `--reasoning-effort low|medium|high` and
`--workers`. `estimate` token assumptions can be overridden with
`--assume gen_output_divination=8000` (or an `estimate:` section in the config).
Generation dominates the cost; ranking with Jev costs well under a dollar.

## Results layout

```
results/<run>/
  readings.jsonl     one Reading per (question, method, seed, model)
  judgments.jsonl    one Judgment (ranking) per (group, judge), with label -> 'method|model' map
  probes.jsonl       knowledge probes
  spend.jsonl        ledger of every paid API call
  probe_cutoffs.json models' self-reported training cutoffs
  config.<command>.yaml  resolved settings snapshot per command
  report.md          leaderboards, accuracy, per-domain, agreement, probes, cost
  csv/*.csv          every report table (full detail, incl. per-judge rows)
```

The report covers: method leaderboards (per generator and pooled; mean rank,
mean P(best), P(acc), P(prec), pairwise win rate, CIs) and head-to-head matrices; objective
accuracy on binary / multiple-choice questions vs a chance baseline; model
leaderboards per method; self-preference; per-domain method scores; judge
agreement (Kendall / Spearman); knowledge probes; cost per stage and model;
question metadata.

## Adding questions

1. Copy `data/questions/_example.yaml.txt` to
   `data/questions/<domain>/<id>.yaml`.
2. Pick an event that resolved after every tested model's cutoff and release.
   Context sources must predate the event; the context summary must not hint
   at the outcome.
3. Prefer `open` questions phrased as "what will happen?"; `resolved_answer` is
   then a one-line headline. For binary / multiple-choice questions it must be
   one of `options` verbatim. Give outcome excerpts with the specific facts
   (numbers, names, margins) a judge needs.
4. Run `uv run divination-bench validate`.

## Development

```bash
uv run ruff check src tests && uv run ruff format src tests && uv run pytest -q
```
