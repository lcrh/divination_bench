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

LLM judges then rank the readings against what actually happened.

## Design

**Questions** (`data/questions/<domain>/<id>.yaml`, template in
`data/questions/_example.yaml.txt`). Each has a neutral question, type
(`binary` / `multiple_choice` / `open`) with options, resolution criteria, a
context summary that does not leak the outcome, dated context sources, the
event date, an outcome summary, the resolved answer and dated outcome sources.
`validate` prints, per question, the latest context source date, event date
and latest outcome source date, and checks every event is after the documented
`model_cutoffs` (max of training cutoff and release date) of every tested
model. Reserve questions (`backup: true`) are skipped unless `--include-backups`.

**Casting** is deterministic in `(question_id, method, seed)`, so `cast` can
reproduce any draw. Models see the draw, not the randomness.

**Reading → standalone prediction.** Divination readings end with a
`prediction` that must not mention cards, hexagrams or divination, plus an
`answer` (one of the options) for binary / multiple-choice questions. This is
what makes tarot, I Ching and plain prediction directly comparable.

**Judging.** Each judge call ranks an anonymised group of 2-3 items, shown as
`[Item A]`, `[Item B]`, ... in an order shuffled deterministically per
(group, judge). The judge sees the question, options, resolution criteria, the
pre-event context, the outcome summary, the resolved answer and dated outcome
excerpts.

| comparison | fixed                    | mode `prediction`                   | mode `full`                             |
|------------|--------------------------|-------------------------------------|-----------------------------------------|
| `methods`  | question, seed, model    | tarot vs iching vs predict (headline) | tarot vs iching, reading + prediction |
| `models`   | question, seed, method   | generator models, prediction only   | generator models, reading + prediction (not `predict`) |

In `prediction` mode the judge is not told how items were produced.

**Primary criterion: did what was predicted actually happen?** The core outcome
dominates; specific checkable details earn credit only when they are right and
are penalised when wrong; vague, hedged or unfalsifiable claims earn little;
contradicted claims are penalised; eloquence, length and spiritual insight earn
nothing. In `full` mode the reading can earn credit where it clearly
anticipated aspects of the outcome. Judges return a 0-10 score and a strict
1..n ranking per item (invalid output is retried up to twice).

**Caveats.**
- *Self-preference*: two of the three judges are also the tested models. The
  report shows pooled results, results from `independent` judges only (judge
  not among the ranked models / not the generator), per-judge results, and a
  self-preference table that flags judges favouring their own model.
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

A real run, step by step (every stage is resumable; rerunning skips what is
already in the run directory):

```bash
uv run divination-bench probe    --run main --budget 120
uv run divination-bench generate --run main --budget 120
uv run divination-bench judge    --run main --budget 120
uv run divination-bench report   --run main [--exclude-known]
# or all at once:
uv run divination-bench run --run main --budget 120
```

`--budget` caps the total recorded spend of the run directory, including
costs already recorded there. Narrow a run with `--questions id1,id2`,
`--limit N`, `--models`, `--judges`, `--methods`, `--seeds`, `--modes`,
`--comparisons`; tune with `--reasoning-effort low|medium|high` and
`--workers`. `estimate` token assumptions can be overridden with
`--assume judge_output=5000` (or an `estimate:` section in the config); judging
dominates the cost, so trimming judges, modes or comparisons is the main lever.

## Results layout

```
results/<run>/
  readings.jsonl     one Reading per (question, method, seed, model)
  judgments.jsonl    one Judgment per (group, judge), with label -> 'method|model' map
  probes.jsonl       knowledge probes
  probe_cutoffs.json models' self-reported training cutoffs
  config.<command>.yaml  resolved settings snapshot per command
  report.md          leaderboards, accuracy, per-domain, agreement, probes, cost
  csv/*.csv          every report table (full detail, incl. per-judge rows)
```

The report covers: method leaderboards (per generator and pooled; mean rank,
mean score, pairwise win rate, CIs) and head-to-head matrices; objective
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
3. For binary / multiple-choice questions, `resolved_answer` must be one of
   `options` verbatim. Give outcome excerpts with the specific facts (numbers,
   names, margins) a judge needs.
4. Run `uv run divination-bench validate`.

## Development

```bash
uv run ruff check src tests && uv run ruff format src tests && uv run pytest -q
```
