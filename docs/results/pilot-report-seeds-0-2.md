# divination-bench report: pilot (seeds 0, 1, 2)

- Questions with data: 40 (of 40 loaded)
- Readings: 1800; judgments: 1920
- Recorded cost: $54.89 (total run spend incl. discarded calls: $102.88)
- Questions a tested model claimed to know: 0 (not excluded)
- Rankings come from successive choices (best of the remaining forecasts, repeated); win rate is the share of pairwise comparisons within a ranking that the entry won. P(best) pools the judge's accuracy and precision choice probabilities as sqrt(P_acc * P_prec), renormalised; P(acc) and P(prec) are the two components (precision is judged without the outcome).

## Method comparison

### Method leaderboard: prediction only, all methods

Each judge call ranks one generator's readings for one (question, seed) across methods. `independent` excludes judgments where the judge is the generator. CIs bootstrap over questions.

| generator | judges | method | n | questions | mean rank | mean P(best) | P(best) 95% CI | P(acc) | P(prec) | win rate | win 95% CI |
|---|---|---|---|---|---|---|---|---|---|---|---|
| pooled | pooled | tarot | 360 | 40 | 2.10 | 0.29 | [0.25, 0.33] | 0.31 | 0.30 | 0.45 | [0.40, 0.49] |
| pooled | pooled | iching | 360 | 40 | 2.24 | 0.23 | [0.19, 0.27] | 0.30 | 0.18 | 0.38 | [0.33, 0.43] |
| pooled | pooled | predict | 360 | 40 | 1.66 | 0.48 | [0.42, 0.53] | 0.39 | 0.51 | 0.67 | [0.62, 0.72] |
| anthropic/claude-opus-5.5 | pooled | tarot | 120 | 40 | 1.96 | 0.34 | [0.28, 0.39] | 0.27 | 0.40 | 0.52 | [0.44, 0.60] |
| anthropic/claude-opus-5.5 | pooled | iching | 120 | 40 | 2.29 | 0.23 | [0.19, 0.29] | 0.29 | 0.22 | 0.35 | [0.28, 0.43] |
| anthropic/claude-opus-5.5 | pooled | predict | 120 | 40 | 1.75 | 0.43 | [0.36, 0.50] | 0.44 | 0.38 | 0.62 | [0.55, 0.70] |
| google/gemini-4-argon | pooled | tarot | 120 | 40 | 2.41 | 0.20 | [0.16, 0.24] | 0.33 | 0.13 | 0.30 | [0.24, 0.35] |
| google/gemini-4-argon | pooled | iching | 120 | 40 | 2.17 | 0.21 | [0.15, 0.28] | 0.30 | 0.15 | 0.41 | [0.34, 0.49] |
| google/gemini-4-argon | pooled | predict | 120 | 40 | 1.42 | 0.59 | [0.50, 0.66] | 0.37 | 0.72 | 0.79 | [0.71, 0.87] |
| openai/gpt-6-astra | pooled | tarot | 120 | 40 | 1.93 | 0.34 | [0.27, 0.41] | 0.33 | 0.38 | 0.53 | [0.45, 0.61] |
| openai/gpt-6-astra | pooled | iching | 120 | 40 | 2.26 | 0.24 | [0.19, 0.30] | 0.32 | 0.18 | 0.37 | [0.30, 0.44] |
| openai/gpt-6-astra | pooled | predict | 120 | 40 | 1.81 | 0.42 | [0.34, 0.51] | 0.34 | 0.44 | 0.60 | [0.50, 0.70] |

### Method leaderboard by judge (prediction mode, all generators)

| judges | method | n | questions | mean rank | mean P(best) | P(acc) | P(prec) | win rate |
|---|---|---|---|---|---|---|---|---|
| typesafe/jev-1.13 | tarot | 360 | 40 | 2.10 | 0.29 | 0.31 | 0.30 | 0.45 |
| typesafe/jev-1.13 | iching | 360 | 40 | 2.24 | 0.23 | 0.30 | 0.18 | 0.38 |
| typesafe/jev-1.13 | predict | 360 | 40 | 1.66 | 0.48 | 0.39 | 0.51 | 0.67 |

### Method head-to-head (prediction mode, pooled): P(row ranked above column)

| method | tarot | iching | predict |
|---|---|---|---|
| tarot |  | 0.54 | 0.36 |
| iching | 0.46 |  | 0.30 |
| predict | 0.64 | 0.70 |  |

### Method leaderboard: full reading, tarot vs I Ching

Each judge call ranks one generator's readings for one (question, seed) across methods. `independent` excludes judgments where the judge is the generator. CIs bootstrap over questions.

| generator | judges | method | n | questions | mean rank | mean P(best) | P(best) 95% CI | P(acc) | P(prec) | win rate | win 95% CI |
|---|---|---|---|---|---|---|---|---|---|---|---|
| pooled | pooled | tarot | 360 | 40 | 1.46 | 0.52 | [0.48, 0.57] | 0.49 | 0.56 | 0.54 | [0.49, 0.60] |
| pooled | pooled | iching | 360 | 40 | 1.54 | 0.48 | [0.43, 0.52] | 0.51 | 0.44 | 0.46 | [0.40, 0.51] |
| anthropic/claude-opus-5.5 | pooled | tarot | 120 | 40 | 1.41 | 0.55 | [0.49, 0.61] | 0.48 | 0.61 | 0.59 | [0.51, 0.68] |
| anthropic/claude-opus-5.5 | pooled | iching | 120 | 40 | 1.59 | 0.45 | [0.39, 0.51] | 0.52 | 0.39 | 0.41 | [0.32, 0.49] |
| google/gemini-4-argon | pooled | tarot | 120 | 40 | 1.57 | 0.47 | [0.41, 0.53] | 0.49 | 0.45 | 0.43 | [0.34, 0.52] |
| google/gemini-4-argon | pooled | iching | 120 | 40 | 1.43 | 0.53 | [0.47, 0.59] | 0.51 | 0.55 | 0.57 | [0.48, 0.66] |
| openai/gpt-6-astra | pooled | tarot | 120 | 40 | 1.39 | 0.55 | [0.50, 0.61] | 0.49 | 0.63 | 0.61 | [0.53, 0.68] |
| openai/gpt-6-astra | pooled | iching | 120 | 40 | 1.61 | 0.45 | [0.39, 0.50] | 0.51 | 0.37 | 0.39 | [0.32, 0.47] |

### Method leaderboard by judge (full mode, all generators)

| judges | method | n | questions | mean rank | mean P(best) | P(acc) | P(prec) | win rate |
|---|---|---|---|---|---|---|---|---|
| typesafe/jev-1.13 | tarot | 360 | 40 | 1.46 | 0.52 | 0.49 | 0.56 | 0.54 |
| typesafe/jev-1.13 | iching | 360 | 40 | 1.54 | 0.48 | 0.51 | 0.44 | 0.46 |

### Method head-to-head (full mode, pooled): P(row ranked above column)

| method | tarot | iching |
|---|---|---|
| tarot |  | 0.54 |
| iching | 0.46 |  |

### Method leaderboard: reading only (no prediction asked), tarot vs I Ching

Each judge call ranks one generator's readings for one (question, seed) across methods. `independent` excludes judgments where the judge is the generator. CIs bootstrap over questions.

| generator | judges | method | n | questions | mean rank | mean P(best) | P(best) 95% CI | P(acc) | P(prec) | win rate | win 95% CI |
|---|---|---|---|---|---|---|---|---|---|---|---|
| pooled | pooled | tarot_reading | 360 | 40 | 1.56 | 0.47 | [0.44, 0.52] | 0.47 | 0.44 | 0.44 | [0.37, 0.51] |
| pooled | pooled | iching_reading | 360 | 40 | 1.44 | 0.53 | [0.48, 0.56] | 0.53 | 0.56 | 0.56 | [0.49, 0.63] |
| anthropic/claude-opus-5.5 | pooled | tarot_reading | 120 | 40 | 1.54 | 0.48 | [0.43, 0.53] | 0.48 | 0.46 | 0.46 | [0.38, 0.55] |
| anthropic/claude-opus-5.5 | pooled | iching_reading | 120 | 40 | 1.46 | 0.52 | [0.47, 0.57] | 0.52 | 0.54 | 0.54 | [0.45, 0.62] |
| google/gemini-4-argon | pooled | tarot_reading | 120 | 40 | 1.60 | 0.44 | [0.39, 0.50] | 0.44 | 0.37 | 0.40 | [0.30, 0.50] |
| google/gemini-4-argon | pooled | iching_reading | 120 | 40 | 1.40 | 0.56 | [0.50, 0.61] | 0.56 | 0.63 | 0.60 | [0.50, 0.70] |
| openai/gpt-6-astra | pooled | tarot_reading | 120 | 40 | 1.53 | 0.50 | [0.46, 0.55] | 0.50 | 0.49 | 0.47 | [0.37, 0.57] |
| openai/gpt-6-astra | pooled | iching_reading | 120 | 40 | 1.47 | 0.50 | [0.45, 0.54] | 0.50 | 0.51 | 0.53 | [0.43, 0.63] |

### Method leaderboard by judge (reading mode, all generators)

| judges | method | n | questions | mean rank | mean P(best) | P(acc) | P(prec) | win rate |
|---|---|---|---|---|---|---|---|---|
| typesafe/jev-1.13 | tarot_reading | 360 | 40 | 1.56 | 0.47 | 0.47 | 0.44 | 0.44 |
| typesafe/jev-1.13 | iching_reading | 360 | 40 | 1.44 | 0.53 | 0.53 | 0.56 | 0.56 |

### Method head-to-head (reading mode, pooled): P(row ranked above column)

| method | tarot_reading | iching_reading |
|---|---|---|
| tarot_reading |  | 0.44 |
| iching_reading | 0.56 |  |

## Objective accuracy

### Objective accuracy (binary / multiple-choice questions)

`answer` vs `resolved_answer` (case-insensitive). Chance = mean 1/#options.

_No data._

## Model comparison

### Model leaderboard (prediction mode)

Each judge call ranks the generator models' readings for one (question, seed, method). `independent` keeps only judgments whose judge is not one of the ranked models (dropping single self-judged rows would bias the comparison).

| method | judges | model | n | questions | mean rank | mean P(best) | P(best) 95% CI | P(acc) | P(prec) | win rate | win 95% CI |
|---|---|---|---|---|---|---|---|---|---|---|---|
| all | pooled | anthropic/claude-opus-5.5 | 360 | 40 | 1.98 | 0.30 | [0.25, 0.36] | 0.38 | 0.23 | 0.51 | [0.44, 0.58] |
| all | pooled | google/gemini-4-argon | 360 | 40 | 1.78 | 0.41 | [0.37, 0.45] | 0.24 | 0.56 | 0.61 | [0.56, 0.66] |
| all | pooled | openai/gpt-6-astra | 360 | 40 | 2.24 | 0.28 | [0.23, 0.34] | 0.38 | 0.21 | 0.38 | [0.30, 0.45] |
| tarot | pooled | anthropic/claude-opus-5.5 | 120 | 40 | 1.79 | 0.39 | [0.32, 0.46] | 0.36 | 0.34 | 0.60 | [0.52, 0.69] |
| tarot | pooled | google/gemini-4-argon | 120 | 40 | 2.15 | 0.28 | [0.23, 0.33] | 0.24 | 0.35 | 0.42 | [0.35, 0.50] |
| tarot | pooled | openai/gpt-6-astra | 120 | 40 | 2.06 | 0.34 | [0.26, 0.41] | 0.40 | 0.31 | 0.47 | [0.38, 0.56] |
| iching | pooled | anthropic/claude-opus-5.5 | 120 | 40 | 1.99 | 0.29 | [0.23, 0.35] | 0.36 | 0.23 | 0.50 | [0.42, 0.59] |
| iching | pooled | google/gemini-4-argon | 120 | 40 | 1.73 | 0.41 | [0.34, 0.48] | 0.25 | 0.56 | 0.63 | [0.54, 0.72] |
| iching | pooled | openai/gpt-6-astra | 120 | 40 | 2.27 | 0.30 | [0.22, 0.37] | 0.39 | 0.21 | 0.36 | [0.27, 0.46] |
| predict | pooled | anthropic/claude-opus-5.5 | 120 | 40 | 2.15 | 0.23 | [0.17, 0.31] | 0.43 | 0.11 | 0.42 | [0.33, 0.53] |
| predict | pooled | google/gemini-4-argon | 120 | 40 | 1.45 | 0.55 | [0.46, 0.63] | 0.22 | 0.77 | 0.78 | [0.69, 0.85] |
| predict | pooled | openai/gpt-6-astra | 120 | 40 | 2.40 | 0.22 | [0.15, 0.29] | 0.35 | 0.12 | 0.30 | [0.21, 0.40] |

### Model leaderboard by judge (prediction mode, all methods)

| judges | model | n | questions | mean rank | mean P(best) | P(acc) | P(prec) | win rate |
|---|---|---|---|---|---|---|---|---|
| typesafe/jev-1.13 | anthropic/claude-opus-5.5 | 360 | 40 | 1.98 | 0.30 | 0.38 | 0.23 | 0.51 |
| typesafe/jev-1.13 | google/gemini-4-argon | 360 | 40 | 1.78 | 0.41 | 0.24 | 0.56 | 0.61 |
| typesafe/jev-1.13 | openai/gpt-6-astra | 360 | 40 | 2.24 | 0.28 | 0.38 | 0.21 | 0.38 |

### Model leaderboard (full mode)

Each judge call ranks the generator models' readings for one (question, seed, method). `independent` keeps only judgments whose judge is not one of the ranked models (dropping single self-judged rows would bias the comparison).

| method | judges | model | n | questions | mean rank | mean P(best) | P(best) 95% CI | P(acc) | P(prec) | win rate | win 95% CI |
|---|---|---|---|---|---|---|---|---|---|---|---|
| all | pooled | anthropic/claude-opus-5.5 | 240 | 40 | 1.87 | 0.36 | [0.31, 0.42] | 0.35 | 0.33 | 0.57 | [0.49, 0.64] |
| all | pooled | google/gemini-4-argon | 240 | 40 | 1.98 | 0.34 | [0.30, 0.39] | 0.24 | 0.45 | 0.51 | [0.44, 0.58] |
| all | pooled | openai/gpt-6-astra | 240 | 40 | 2.15 | 0.29 | [0.23, 0.36] | 0.41 | 0.22 | 0.42 | [0.34, 0.51] |
| tarot | pooled | anthropic/claude-opus-5.5 | 120 | 40 | 1.79 | 0.41 | [0.34, 0.48] | 0.35 | 0.40 | 0.60 | [0.52, 0.70] |
| tarot | pooled | google/gemini-4-argon | 120 | 40 | 2.20 | 0.27 | [0.23, 0.32] | 0.24 | 0.34 | 0.40 | [0.32, 0.48] |
| tarot | pooled | openai/gpt-6-astra | 120 | 40 | 2.01 | 0.32 | [0.25, 0.39] | 0.41 | 0.26 | 0.50 | [0.42, 0.58] |
| iching | pooled | anthropic/claude-opus-5.5 | 120 | 40 | 1.94 | 0.32 | [0.26, 0.38] | 0.35 | 0.27 | 0.53 | [0.44, 0.61] |
| iching | pooled | google/gemini-4-argon | 120 | 40 | 1.76 | 0.41 | [0.35, 0.48] | 0.24 | 0.55 | 0.62 | [0.53, 0.70] |
| iching | pooled | openai/gpt-6-astra | 120 | 40 | 2.30 | 0.27 | [0.21, 0.34] | 0.41 | 0.18 | 0.35 | [0.25, 0.46] |

### Model leaderboard by judge (full mode, all methods)

| judges | model | n | questions | mean rank | mean P(best) | P(acc) | P(prec) | win rate |
|---|---|---|---|---|---|---|---|---|
| typesafe/jev-1.13 | anthropic/claude-opus-5.5 | 240 | 40 | 1.87 | 0.36 | 0.35 | 0.33 | 0.57 |
| typesafe/jev-1.13 | google/gemini-4-argon | 240 | 40 | 1.98 | 0.34 | 0.24 | 0.45 | 0.51 |
| typesafe/jev-1.13 | openai/gpt-6-astra | 240 | 40 | 2.15 | 0.29 | 0.41 | 0.22 | 0.42 |

### Model leaderboard (reading mode)

Each judge call ranks the generator models' readings for one (question, seed, method). `independent` keeps only judgments whose judge is not one of the ranked models (dropping single self-judged rows would bias the comparison).

| method | judges | model | n | questions | mean rank | mean P(best) | P(best) 95% CI | P(acc) | P(prec) | win rate | win 95% CI |
|---|---|---|---|---|---|---|---|---|---|---|---|
| all | pooled | anthropic/claude-opus-5.5 | 240 | 40 | 1.89 | 0.35 | [0.32, 0.38] | 0.35 | 0.40 | 0.56 | [0.49, 0.62] |
| all | pooled | google/gemini-4-argon | 240 | 40 | 2.06 | 0.34 | [0.30, 0.38] | 0.34 | 0.45 | 0.47 | [0.39, 0.55] |
| all | pooled | openai/gpt-6-astra | 240 | 40 | 2.05 | 0.31 | [0.27, 0.35] | 0.31 | 0.15 | 0.47 | [0.39, 0.55] |
| tarot_reading | pooled | anthropic/claude-opus-5.5 | 120 | 40 | 1.86 | 0.35 | [0.32, 0.39] | 0.35 | 0.43 | 0.57 | [0.50, 0.65] |
| tarot_reading | pooled | google/gemini-4-argon | 120 | 40 | 2.15 | 0.32 | [0.27, 0.36] | 0.32 | 0.39 | 0.42 | [0.33, 0.53] |
| tarot_reading | pooled | openai/gpt-6-astra | 120 | 40 | 1.99 | 0.33 | [0.29, 0.38] | 0.33 | 0.19 | 0.50 | [0.41, 0.59] |
| iching_reading | pooled | anthropic/claude-opus-5.5 | 120 | 40 | 1.92 | 0.35 | [0.32, 0.38] | 0.35 | 0.37 | 0.54 | [0.47, 0.62] |
| iching_reading | pooled | google/gemini-4-argon | 120 | 40 | 1.97 | 0.36 | [0.32, 0.40] | 0.36 | 0.51 | 0.52 | [0.42, 0.61] |
| iching_reading | pooled | openai/gpt-6-astra | 120 | 40 | 2.12 | 0.29 | [0.25, 0.33] | 0.29 | 0.11 | 0.44 | [0.34, 0.53] |

### Model leaderboard by judge (reading mode, all methods)

| judges | model | n | questions | mean rank | mean P(best) | P(acc) | P(prec) | win rate |
|---|---|---|---|---|---|---|---|---|
| typesafe/jev-1.13 | anthropic/claude-opus-5.5 | 240 | 40 | 1.89 | 0.35 | 0.35 | 0.40 | 0.56 |
| typesafe/jev-1.13 | google/gemini-4-argon | 240 | 40 | 2.06 | 0.34 | 0.34 | 0.45 | 0.47 |
| typesafe/jev-1.13 | openai/gpt-6-astra | 240 | 40 | 2.05 | 0.31 | 0.31 | 0.15 | 0.47 |

### Self-preference (model comparison)

Baseline judges are those whose own model is not being ranked (or all other judges if there are none). Flagged when a judge rates its own model's win rate at least 0.10 higher than the baseline does.

_No data._

## Per-domain breakdown

### Method scores by domain (prediction mode, pooled)

| domain | questions | tarot score | tarot win rate | iching score | iching win rate | predict score | predict win rate |
|---|---|---|---|---|---|---|---|
| business | 2 | 0.31 | 0.33 | 0.32 | 0.44 | 0.37 | 0.72 |
| culture | 5 | 0.25 | 0.43 | 0.22 | 0.34 | 0.53 | 0.72 |
| economics | 1 | 0.05 | 0.28 | 0.10 | 0.22 | 0.85 | 1.00 |
| geopolitics | 5 | 0.31 | 0.51 | 0.16 | 0.29 | 0.53 | 0.70 |
| law | 3 | 0.50 | 0.56 | 0.22 | 0.39 | 0.27 | 0.56 |
| other | 2 | 0.22 | 0.31 | 0.28 | 0.53 | 0.50 | 0.67 |
| politics | 6 | 0.23 | 0.39 | 0.33 | 0.48 | 0.44 | 0.63 |
| science | 8 | 0.30 | 0.52 | 0.20 | 0.35 | 0.50 | 0.62 |
| sports | 6 | 0.26 | 0.39 | 0.24 | 0.40 | 0.50 | 0.71 |
| tech | 2 | 0.45 | 0.61 | 0.18 | 0.28 | 0.37 | 0.61 |

### Method scores by domain (full mode, pooled)

| domain | questions | tarot score | tarot win rate | iching score | iching win rate |
|---|---|---|---|---|---|
| business | 2 | 0.50 | 0.44 | 0.50 | 0.56 |
| culture | 5 | 0.52 | 0.51 | 0.48 | 0.49 |
| economics | 1 | 0.44 | 0.44 | 0.56 | 0.56 |
| geopolitics | 5 | 0.62 | 0.69 | 0.38 | 0.31 |
| law | 3 | 0.65 | 0.70 | 0.35 | 0.30 |
| other | 2 | 0.41 | 0.39 | 0.59 | 0.61 |
| politics | 6 | 0.40 | 0.39 | 0.60 | 0.61 |
| science | 8 | 0.56 | 0.58 | 0.44 | 0.42 |
| sports | 6 | 0.47 | 0.50 | 0.53 | 0.50 |
| tech | 2 | 0.70 | 0.78 | 0.30 | 0.22 |

### Method scores by domain (reading mode, pooled)

| domain | questions | tarot_reading score | tarot_reading win rate | iching_reading score | iching_reading win rate |
|---|---|---|---|---|---|
| business | 2 | 0.60 | 0.56 | 0.40 | 0.44 |
| culture | 5 | 0.47 | 0.47 | 0.53 | 0.53 |
| economics | 1 | 0.37 | 0.22 | 0.63 | 0.78 |
| geopolitics | 5 | 0.57 | 0.58 | 0.43 | 0.42 |
| law | 3 | 0.51 | 0.56 | 0.49 | 0.44 |
| other | 2 | 0.52 | 0.50 | 0.48 | 0.50 |
| politics | 6 | 0.42 | 0.37 | 0.58 | 0.63 |
| science | 8 | 0.48 | 0.47 | 0.52 | 0.53 |
| sports | 6 | 0.43 | 0.33 | 0.57 | 0.67 |
| tech | 2 | 0.37 | 0.22 | 0.63 | 0.78 |

## Judge agreement

### Judge agreement

Rank correlation between two judges on the same group of readings.

_No data._

## Knowledge probes

### Knowledge probes

Cells: knows_outcome / correctness of stated answer. `EXCLUDE?` marks questions where a tested model claimed to know the outcome and was not wrong; `--exclude-known` drops them from the report.

| question | anthropic/claude-opus-5.5 | google/gemini-4-argon | openai/gpt-6-astra | flag |
|---|---|---|---|---|
| antarctic-ozone-hole-2026-nasa-noaa | no / ? | no / ? | no / ? |  |
| bank-of-canada-oct-2026-decision | no / ? | no / ? | no / ? |  |
| brazil-presidential-runoff-2026 | no / ? | no / ? | no / ? |  |
| bulin-47-trend-2026 | no / ? | no / ? | no / ? |  |
| collins-word-of-the-year-2026 | no / ? | no / ? | no / ? |  |
| copernicus-september-2026-global-temperature | no / ? | no / ? | no / ? |  |
| earhart-taraia-object-expedition-2026 | no / ? | no / ? | no / ? |  |
| el-clasico-barcelona-real-madrid-2026-10 | no / ? | no / ? | no / ? |  |
| el-salvador-haiti-response-2026 | no / ? | no / ? | no / ? |  |
| electric-plant-bombadil-2026 | no / ? | no / ? | no / ? |  |
| ema-narsoplimab-reexamination-2026 | no / ? | no / ? | no / ? |  |
| erin-patterson-appeal-2026 | no / ? | no / ? | no / ? |  |
| ethiopia-tigray-offensive-outcome-2026 | no / ? | no / ? | no / ? |  |
| f1-mexico-city-gp-2026-winner | no / ? | no / ? | no / ? |  |
| grab-foodpanda-taiwan-ftc-2026 | no / ? | no / ? | no / ? |  |
| herugavialis-cairensis-2026 | no / ? | no / ? | no / ? |  |
| hurricane-isaias-landfall-2026 | no / ? | no / ? | no / ? |  |
| israel-knesset-election-2026 | no / ? | no / ? | no / ? |  |
| jaxa-mmx-h3-f10-launch-2026 | no / ? | no / ? | no / ? |  |
| malaysia-perikatan-deregistration-2026 | no / ? | no / ? | no / ? |  |
| mcr-black-parade-20th-anniversary-charts-2026 | no / ? | no / ? | no / ? |  |
| melbourne-cup-2026 | no / ? | no / ? | no / ? |  |
| moio-immunotherapy-deescalation-esmo-2026 | no / ? | no / ? | no / ? |  |
| nobel-medicine-2026-field | no / ? | no / ? | no / ? |  |
| nyc-marathon-2026-men | no / ? | no / ? | no / ? |  |
| pakistan-kp-standoff-response-2026 | no / ? | no / ? | no / ? |  |
| paraguay-ueno-bank-affair-2026 | no / ? | no / ? | no / ? |  |
| phantom-blade-zero-launch-2026 | no / ? | no / ? | no / ? |  |
| prix-goncourt-2026 | no / ? | no / ? | no / ? |  |
| russia-ukraine-ceasefire-by-oct-2026 | no / ? | no / ? | no / ? |  |
| serbia-parliamentary-election-2026 | no / ? | no / ? | no / ? |  |
| sothebys-jodi-nanotyrannus-auction-2026 | no / ? | no / ? | no / ? |  |
| space-bunny-alpha-identity-2026 | no / ? | no / ? | no / ? |  |
| tesla-roadster-sub-1s-0-60-demo-2026 | no / ? | no / ? | no / ? |  |
| texas-senate-talarico-paxton-2026 | no / ? | no / ? | no / ? |  |
| tundu-lissu-treason-verdict-2026 | no / ? | no / ? | no / ? |  |
| ufc-333-yan-dvalishvili-3 | no / ? | no / ? | no / ? |  |
| us-strike-iran-before-midterms-2026 | no / ? | no / ? | no / ? |  |
| world-series-2026-brewers-rays | no / ? | no / ? | no / ? |  |
| yemen-bab-al-mandab-offensive-2026 | no / ? | no / ? | no / ? |  |

## Prediction blinding

### Predictions that mention divination

Simple keyword match; check examples by hand before trusting prediction-mode blinding.

| method | model | predictions | mentioning divination | first example |
|---|---|---|---|---|
| iching | anthropic/claude-opus-5.5 | 120 | 4 | bulin-47-trend-2026 s0: 'spread' |
| iching | google/gemini-4-argon | 120 | 0 |  |
| iching | openai/gpt-6-astra | 120 | 3 | bulin-47-trend-2026 s0: 'spread' |
| tarot | anthropic/claude-opus-5.5 | 120 | 6 | ufc-333-yan-dvalishvili-3 s0: 'cards' |
| tarot | google/gemini-4-argon | 120 | 1 | ufc-333-yan-dvalishvili-3 s2: 'the reading' |
| tarot | openai/gpt-6-astra | 120 | 3 | bank-of-canada-oct-2026-decision s0: 'spread' |

## Cost and coverage

### Cost (OpenRouter usage.cost, USD)

| stage | model | calls | cost $ | prompt tokens | completion tokens |
|---|---|---|---|---|---|
| generation | anthropic/claude-opus-5.5 | 600 | 19.68 | 723842 | 839161 |
| generation | google/gemini-4-argon | 600 | 6.05 | 505620 | 503663 |
| generation | openai/gpt-6-astra | 600 | 26.89 | 469848 | 443755 |
| judging | typesafe/jev-1.13 | 2734 | 1.80 | 42915176 | 612616 |
| probe | anthropic/claude-opus-5.5 | 40 | 0.16 | 14814 | 4904 |
| probe | google/gemini-4-argon | 40 | 0.04 | 12235 | 1400 |
| probe | openai/gpt-6-astra | 40 | 0.28 | 10356 | 3506 |
| total |  | 4654 | 54.89 | 44651891 | 2409005 |

### Coverage

| record | method | model / judge | n |
|---|---|---|---|
| judgment (methods, full) |  | typesafe/jev-1.13 | 360 |
| judgment (methods, prediction) |  | typesafe/jev-1.13 | 360 |
| judgment (methods, reading) |  | typesafe/jev-1.13 | 360 |
| judgment (models, full) |  | typesafe/jev-1.13 | 240 |
| judgment (models, prediction) |  | typesafe/jev-1.13 | 360 |
| judgment (models, reading) |  | typesafe/jev-1.13 | 240 |
| reading | iching | anthropic/claude-opus-5.5 | 120 |
| reading | iching | google/gemini-4-argon | 120 |
| reading | iching | openai/gpt-6-astra | 120 |
| reading | iching_reading | anthropic/claude-opus-5.5 | 120 |
| reading | iching_reading | google/gemini-4-argon | 120 |
| reading | iching_reading | openai/gpt-6-astra | 120 |
| reading | predict | anthropic/claude-opus-5.5 | 120 |
| reading | predict | google/gemini-4-argon | 120 |
| reading | predict | openai/gpt-6-astra | 120 |
| reading | tarot | anthropic/claude-opus-5.5 | 120 |
| reading | tarot | google/gemini-4-argon | 120 |
| reading | tarot | openai/gpt-6-astra | 120 |
| reading | tarot_reading | anthropic/claude-opus-5.5 | 120 |
| reading | tarot_reading | google/gemini-4-argon | 120 |
| reading | tarot_reading | openai/gpt-6-astra | 120 |

## Questions

### Questions

| id | domain | type | latest context source | event date | latest outcome source | notes |
|---|---|---|---|---|---|---|
| electric-plant-bombadil-2026 | business | open | 2025-02-24 | 2026-10-20 | 2026-10-20 | The white paper carries the date 19 Oct 2026, but the public launch (press release, TechCrunch, founder's post) was 20 Oct 2026, which is used as the event_date. The context source is a Feb 2025 founder essay that already discussed plants' electrical signalling and the company's mission. The context summary deliberately leaves out that mission so the answer is not given away. The company name, the Bloomscape background and the Tolkien nature-spirit name still hint at plants. A strong answer must add the foundation-model and electrophysiology specifics. Species counts vary by source (100 in the press release and white paper, 125+ on TechCrunch and the FAQ). |
| grab-foodpanda-taiwan-ftc-2026 | business | open | 2026-10-14 | 2026-10-21 | 2026-10-22 | No market found. Uber's voting share is given as 3.7% in the FTC's July notice and 3.9% in its October decision; equity is 13% (July) and 13.1% (October). Fortune (not cited) reported that the Uber board member who left in July was CEO Dara Khosrowshahi. Note that the decision came on 21 October, before the 27 October deadline; a prediction that only gives the deadline date should not be penalised for timing. |
| collins-word-of-the-year-2026 | culture | open | 2025-11-06 | 2026-11-03 | 2026-11-03 | The word "mogging" itself predates 2026. What is new is its selection, which was first made public on 3 Nov 2026. Dictionary.com had named "maxxing" (a related manosphere-derived slang form) its 2026 Word of the Year on 25 Oct 2026, before this event. It is left out of the context summary because it is a strong hint, but forecasters could legitimately have known it. "Maxxing" or "looksmaxxing" answers should get little credit. Other dictionaries (Oxford, Cambridge, Merriam-Webster) had not announced their 2026 words as of 7 Nov 2026. |
| mcr-black-parade-20th-anniversary-charts-2026 | culture | open | 2026-10-25 | 2026-10-30 | 2026-11-01 | event_date is the UK announcement (30 Oct 2026), the first time any part of the outcome was public. The US result followed on 1 Nov. All context sources are dated on or before 25 Oct, before UK midweek chart updates could hint at the result. The 2006 US No. 2 peak, held off by the Hannah Montana soundtrack, is stated in Billboard's post-event coverage and is long-standing chart history rather than new information. |
| phantom-blade-zero-launch-2026 | culture | open | 2026-10-28 | 2026-11-01 | 2026-11-02 | No market found. The 4 million figure is S-Game's own announcement (via its X account) and covers digital sales on all platforms; there is no official per-platform split. Sources disagree on the all-time Steam ranking (This Week in Video Games put the 723,876 day-one peak at 15th all-time; TweakTown put the 833,921 weekend peak in the top 10), so the judge should not lean on the exact all-time rank. The 88 Metacritic critic score was public before launch, so it is not really part of the outcome. |
| prix-goncourt-2026 | culture | open | 2026-11-02 | 2026-11-03 | 2026-11-03 | No real-money prediction market or bookmaker odds found; the only "market" was a free jouepredict.fr poll that closed on 5 October with too few participants to show a share, so market is omitted. Soft spots: Jaenada was the most-cited favourite (franceinfo afterwards: "Il était le favori"), so a well-informed forecaster had an edge, though pre-event previews split between Jaenada, Prudhomme and Haenel. The Le Figaro page returned 403 to direct fetch; its excerpt comes from the retrieved search result text. The Lire Magazine piece is truncated in the retrieved version, so only its standfirst is quoted. Earlier reports (franceinfo, Le Parisien, Sept 2026) gave the proclamation date as 4 November; all later sources and the Académie confirm 3 November. The Académie page misspells the title as "L'inconnu du quai de Javel"; the 20 Minutes source wrongly dates the Orélien withdrawal to 2025. The Orélien withdrawal (25 Sep) is just after the models' 22 Sep cutoff, so it is new information to them. |
| sothebys-jodi-nanotyrannus-auction-2026 | culture | open | 2026-10-06 | 2026-10-27 | 2026-10-27 | No market found. The Galerie page was first published on 7 October and updated on 27 October with the result; it is used only as an outcome source and dated to the update. A later Galerie monthly round-up said "five minutes of rapid bidding"; Sotheby's, Observer and Galerie's own update all say about 12 minutes with six bidders. The price includes buyer's premium. The AP story on the sale could not be fetched (timeout), so it is not cited. |
| bank-of-canada-oct-2026-decision | economics | open | 2026-10-28 | 2026-10-28 | 2026-10-28 | Polymarket daily prices from the CLOB price-history API. The hike was priced at only about 15% until the 19 October CPI release. Kalshi was about 81% before the decision. Market probabilities refer to the former closed framing (cut / hold / hike 25 bp / hike 50 bp or more); the question is now open. |
| el-salvador-haiti-response-2026 | geopolitics | open | 2026-10-20 | 2026-10-28 | 2026-10-29 | Open question with no market. The 100 special forces (22 Oct) and the 2 Nov offensive come from Wikipedia's Current events portal (citing AP and EFE). The "vehicle found, no trace" detail is from an AP report in early November. |
| ethiopia-tigray-offensive-outcome-2026 | geopolitics | open | 2026-09-26 | 2026-10-04 | 2026-10-18 | No market. The dates of town recaptures (Adigrat 10 Oct, Adwa 11 Oct) and of the embassy closure (1 Oct) come from Wikipedia's "2026 Ethiopian offensive" page, which cites Reuters, AFP and ACLED. The Critical Threats brief of 16 Oct describes the caretaker appointees as linked to Getachew Reda's Simret party and the Tigray Peace Forces. Low-level fighting and Fano activity in Amhara continued after Mekelle fell, so "war over" is not strictly accurate. |
| russia-ukraine-ceasefire-by-oct-2026 | geopolitics | open | 2026-10-21 | 2026-10-23 | 2026-10-31 | The market is a proxy: "Will Russia and Ukraine hold any diplomatic meeting by October 31, 2026?" (mediated meetings count). It traded at 0.185 at 12:00 UTC on 21 Oct, 0.24 on 22 Oct, then jumped to 0.99 on 23 Oct after the Oleshky announcement. The BBC published_date is approximate (the article reports evacuees arriving "on Saturday", i.e. 31 Oct). The market probability refers to that closed proxy (and to the former yes/no ceasefire framing); the question is now open. |
| us-strike-iran-before-midterms-2026 | geopolitics | open | 2026-10-09 | 2026-11-02 | 2026-11-07 | Market probabilities refer to the former closed framing ("Yes" = a US strike hitting Iranian territory before the end of 3 November); the question is now open. The market's own outcomes are inverted: "ceasefire continues" (= "No" above) traded at 0.945 at 12:00 UTC on 1 Nov, 0.82 on 26 Oct and ~0.75-0.80 in mid-October (Polymarket CLOB price history). Under the closed framing the outcome was a low-probability upset, although the strike was small and described as defensive. |
| yemen-bab-al-mandab-offensive-2026 | geopolitics | open | 2026-10-02 | 2026-10-05 | 2026-11-05 | No market. Control of Dhubab and of the coast near Bab al-Mandab was disputed throughout. The government said it had retaken Dhubab district, while the Houthis and Xinhua's government source said Mocha and Perim stayed under Houthi control. A judge should accept "contested / partial gains" framings. The 10 October Riyadh airport death toll (12, later 13) and the roughly two-week closure come from Wikipedia's October 2026 Current events portal (citing WSJ, Reuters and AFP). The claim that the Houthis retook the Dhubab airfield around 14 October comes from Al-Binaa's assessment of footage and is not independently confirmed. |
| erin-patterson-appeal-2026 | law | open | 2026-10-28 | 2026-10-30 | 2026-10-30 | No market found. The former multiple-choice options followed the four outcomes set out by AAP in its pre-judgment explainer "Six ways mushroom killer's appeal could turn out"; the question is now open. |
| malaysia-perikatan-deregistration-2026 | law | open | 2026-10-13 | 2026-10-20 | 2026-11-04 | No market. The question is framed as of about 14 October, after the High Court refused an interim stay. The New Straits Times reported the deregistration on the evening of 19 October; most outlets date it 20 October. This question is about a regulator and the courts, not about the Melaka vote result (polling is on 14 November, outside the window). The Straits Times headline says "after failed appeal", but the article describes PN's failed show-cause reply. The PN contest under component banners was floated by Takiyuddin (FMT, 20 Oct) but never happened. |
| tundu-lissu-treason-verdict-2026 | law | open | 2026-11-03 | 2026-11-06 | 2026-11-06 | No market found. Formerly multiple choice (convicted of treason / acquitted of treason but convicted of a lesser offence / acquitted and freed / postponed); now open. "Deadly protests" around the 2025 election is background (AFP via Mwanzo TV: "thousands were killed according to the opposition and rights activists"). |
| bulin-47-trend-2026 | other | open | 2025-07-11 | 2026-10-02 | 2026-10-30 | Bulin 47 the artist was well known before the window. Only the clip and trend are new, so the resolution criteria give little credit for describing the artist. The 2 Oct 2026 posting date comes from one AI-video-tool site (RapBlaze). Other sources only say "early October", and the MARCA story ran on 8 Oct. Sources disagree on the follow-up single's title ("Dame Hombro" per YupPop/RapBlaze, "Hombritos" per Extra.ec, 13 Oct 2026) and on view counts. Several outcome sources are commercial AI-meme-generator sites, backed up by MARCA and Nile FM. |
| hurricane-isaias-landfall-2026 | other | open | 2026-10-09 | 2026-10-09 | 2026-10-12 | No market included. Polymarket's Isaias market was about the landfall state (it resolved Florida). Kalshi's "Hurricane Isaias category" market appears to be about peak category, not landfall intensity: its Category 3+ bracket resolved Yes, so it does not match this question. No pre-event prices for either market could be retrieved. Soft spots: (1) The NHC Category 3 upgrade update is headed "720 AM CDT" but its summary says "0820 UTC", and the filename suggests 1218 UTC, so the exact time of the upgrade is slightly ambiguous. It is clearly on the morning of 9 October. (2) The Outage Pro page has no explicit publication date, so 2026-10-10 is the date of its peak reading. (3) WeatherNation's date is the page's "12 Oct 2026" stamp, which may be an update time. (4) CNBC calls the landfall "early on Saturday", but NHC gives 8:30 PM CDT Friday (0130 UTC Saturday). (5) Resolution uses the operational NHC landfall intensity. A later NHC Tropical Cyclone Report could revise it. (6) The AP landfall story could not be fetched (timeouts), so it is not cited. |
| brazil-presidential-runoff-2026 | politics | open | 2026-10-23 | 2026-10-25 | 2026-10-26 | Market prices from Preduck price log (https://blog.preduck.com/blog/brazil-election-odds) and Action Network preview: Polymarket Flávio 78% / Lula 22% on 22 Oct, Flávio 79.9% on 24 Oct; Kalshi Flávio 79% / Lula 22%. Market probabilities refer to the former closed framing (winner only); the question is now open. |
| israel-knesset-election-2026 | politics | open | 2026-10-26 | 2026-10-27 | 2026-11-08 | Official CEC results: https://votes26.bechirot.gov.il/?lang=en. Polymarket "next PM" market had Eisenkot favoured through most of the campaign (Israel Hayom); Netanyahu's odds jumped ~14 points after exit polls. Final PM not yet sworn in, so the question targets the election result. |
| pakistan-kp-standoff-response-2026 | politics | open | 2026-10-08 | 2026-10-11 | 2026-10-15 | No market. The context is fair rather than neutral: officials openly floated governor's rule, so the main uncertainty was whether and when Islamabad would act, and how harshly (the detention of the chief minister himself was not widely forecast). The advisory council, Article 245 army deployment and six-month horizon come from The News (11 Oct). The detention of Khan's sisters comes from The National (13 Oct, citing Reuters). The Express Tribune and Pakistan Today excerpts were captured via the search tool because direct page fetches timed out. |
| paraguay-ueno-bank-affair-2026 | politics | open | 2026-10-31 | 2026-11-06 | 2026-11-08 | No market. The question is framed as of about 31 October, before the resolution. The La República piece is dated 31 October but appears to reprint an interview from about a week earlier ("Fitch last week"). Wikipedia's Current events portal says the Senate vote to remove Peña was unanimous (AFP) and that he was placed under house arrest (UPI) before the pretrial detention order. Reuters (8 Nov) reports detention at a military facility. The BBC article's date (5 Nov) is inferred from its "3 days ago" stamp on 8 Nov. |
| serbia-parliamentary-election-2026 | politics | open | 2026-10-25 | 2026-10-25 | 2026-11-07 | Polymarket Student List price was ~32% a week before and ~28% a day before (Quiver Quantitative); the Vučić list was the market favourite (~70%+). Wikipedia published_date is the approximate access date of the article revision used. Market probabilities refer to the former closed framing (which list wins the most seats); the question is now open. |
| texas-senate-talarico-paxton-2026 | politics | open | 2026-10-27 | 2026-11-03 | 2026-11-04 | Kalshi had Talarico at 71% on 31 Oct (news.kalshi.com). Polymarket prices from Action Network 27 Oct. Texas SOS published_date is approximate (results page, no date stamp). Market probabilities refer to the former closed framing ("Yes" = Talarico wins); the question is now open. |
| antarctic-ozone-hole-2026-nasa-noaa | science | open | 2026-10-26 | 2026-11-04 | 2026-11-04 | No market. Most of the physical outcome was fixed by 13 October, and daily data were public on NASA Ozone Watch and CAMS before the 4 November release, so a forecaster with live access could have estimated the rank. The tested models only see the September and October context. Rankings differ between datasets: CAMS put its own six-hourly peak (27.44 million km2 on 20 September) third-highest in its record. Judge against the NASA/NOAA figures. |
| copernicus-september-2026-global-temperature | science | open | 2026-09-10 | 2026-10-09 | 2026-10-14 | No market. Date soft spot: the Copernicus press-release page is dated 14 October, but Yale Climate Connections said on 9 October that C3S had already rated September second-warmest, so the bulletin was public by then. event_date is 9 October, and all context sources are from 10 September or earlier. The figure of about 0.93 C above 1991-2020 for September 2023 is restated from the outcome bulletin. It was well known before the event, but no dated pre-event page carrying it was retrieved. The 1.63 C anomaly is a C3S/ERA5 figure. NOAA and NASA use different baselines. |
| earhart-taraia-object-expedition-2026 | science | open | 2026-10-10 | 2026-10-18 | 2026-10-22 | No market. The subject is American (Earhart, Purdue), but the site and part of the team are Kiribati. Departure date differs by source: Purdue's results release says 6 October, while Axios, BBC and Purdue's own pre-trip updates say 7 October local time. The "very likely" quote and the Phase 1-3 plan come from ALI material quoted in the Smithsonian outcome article. Smithsonian also gives the 17-person team size, which matches Purdue's roster. The steel-tube detail combines Purdue (about 30 inches, found in the lagoon) with a UWF/Newswise account (about 3 feet, judged unrelated to the aircraft). |
| ema-narsoplimab-reexamination-2026 | science | open | 2026-08-12 | 2026-10-15 | 2026-10-16 | No market. The base rate is that CHMP re-examinations usually confirm the original negative opinion, so the "what" was the more predictable part and the grounds are where precision matters. The EMA EPAR page shows no explicit publication date; 16 October is used, matching the Q&A release noted in the meeting highlights. The claim that the 12-15 October meeting would conclude the re-examination is an inference from the standard CHMP timetable, not from a retrieved pre-event source. The 25 June date of the initial opinion comes from the EMA's EPAR page. |
| herugavialis-cairensis-2026 | science | open | 2025-08-06 | 2026-10-06 | 2026-10-09 | Taxonomically this is a new genus for an already-described species (Tomistoma cairense, 1927 becomes Herugavialis cairensis), though press coverage calls it a "new species". The name itself gives away "gavial" and "Cairo", so the question also asks why it was named that way: the Sphinx and Heru link cannot be guessed from the Latin. Nautilus published at 6:00 PM CDT on 6 Oct 2026 (the embargo lift), so event_date is 6 Oct, while the paper's online date is 7 Oct. The UCL press release (7 Oct) was seen only through search snippets because direct fetches timed out, so it is not cited. |
| jaxa-mmx-h3-f10-launch-2026 | science | open | 2026-10-19 | 2026-10-20 | 2026-10-20 | No market field. I found no Polymarket, Kalshi or Manifold market. Clutch Predict, a play-money credits app, lists several resolved questions of the form "Will H3 launch MMX on 20 October?", with final crowd confidence of 67-86%. Those figures have no as-of timestamps and are not real-money prices, so I did not include them. Soft spots: (1) The press kit's published_date comes from its filename (20261016), not from a date printed in the document. (2) The claim that no H3 launch had ever gone without a postponement comes from a single Japanese preview (Mynavi TECH+) and was not independently verified. (3) The launch was on 20 October JST but 19 October UTC and in Europe and the Americas. Times are anchored to JST, the official JAXA date. event_date is 2026-10-20 JST, and the DLR outcome source is dated 19 October in CEST. (4) The reserved period was originally announced as running to 7 November and was later extended to 9 November. The question uses the later date. The likely prior is high for launch success (7 of H3's 9 prior flights succeeded) but more uncertain for on-time launch. |
| moio-immunotherapy-deescalation-esmo-2026 | science | open | 2026-10-20 | 2026-10-26 | 2026-10-27 | No market. Soft spot: the trial was halted in May 2026, and ClinicalTrials.gov showed it as "active, not recruiting". An attentive observer could have taken that as a warning sign before ESMO, but no public announcement of the halt or its reason was found before 26 October. The Medscape page carries no explicit date, and its 27 October date is an estimate. The Unicancer press release is undated in the text; its October 2026 upload path and ESMO timing suggest about 26 October. The touchONCOLOGY preview misspells the acronym as "MIOIO". HR confidence intervals differ slightly between reports (0.90-2.00 vs 0.90-2.04). |
| nobel-medicine-2026-field | science | open | 2026-10-05 | 2026-10-05 | 2026-10-05 | No liquid prediction market found; expert previews treated GLP-1 as the front-runner with optogenetics a strong alternative. Formerly multiple choice over research fields (GLP-1, optogenetics, OCT, orexin, other); now open. |
| el-clasico-barcelona-real-madrid-2026-10 | sports | open | 2026-10-25 | 2026-10-25 | 2026-10-26 | Probabilities normalised from DraftKings moneylines (-165 / +475 / +300). They refer to the former closed framing (win/draw/loss); the question is now open. |
| f1-mexico-city-gp-2026-winner | sports | open | 2026-11-01 | 2026-11-01 | 2026-11-01 | Probabilities normalised from bet365 race-day fractional odds (after qualifying). They refer to the former closed framing (race winner from a list of drivers); the question is now open. |
| melbourne-cup-2026 | sports | open | 2026-11-03 | 2026-11-03 | 2026-11-03 | Raw implied probabilities from race-morning fixed odds (not normalised). Point Of Law firmed back to favourite at the jump. Market probabilities cover only the winner, a narrower closed framing than this open question. |
| nyc-marathon-2026-men | sports | open | 2026-10-28 | 2026-11-01 | 2026-11-01 | Kalshi probabilities from LetsRun (thinly traded). They cover only the winner, a narrower closed framing than this open question. |
| ufc-333-yan-dvalishvili-3 | sports | open | 2026-10-23 | 2026-10-24 | 2026-10-24 | Probabilities normalised from FanDuel moneyline Yan -148 / Dvalishvili +120. They refer to the former closed framing ("Yes" = Yan retains); the question is now open. |
| world-series-2026-brewers-rays | sports | open | 2026-10-23 | 2026-10-28 | 2026-10-29 | Market probabilities are implied from American correct-score odds, normalised to remove the bookmaker margin. Series winner alone: Brewers about 0.60. They refer to the former closed framing (winner and series length); the question is now open. |
| space-bunny-alpha-identity-2026 | tech | open | 2026-09-18 | 2026-09-23 | 2026-10-19 | event_date is the day the listing first became public (23 Sep 2026). Its identity was only confirmed on 19 Oct 2026. The OpenRouter listing page now shows the post-reveal text, and its "Released Sep 23, 2026" field is used as the published date. The context summary describes OpenRouter's stealth-model practice, which hints that the listing is an anonymous model. The real unknown is the maker and the final product name. The token counts differ by source: 56.7T is OpenRouter-only, while MiniMax's 200T+ figure presumably covers all channels. |
| tesla-roadster-sub-1s-0-60-demo-2026 | tech | open | 2026-10-15 | 2026-10-15 | 2026-10-15 | The market probability refers to the former closed framing (a live timed sub-1-second 0-60 run); the question is now open. Polymarket CLOB price history at ~12:00 UTC on 15 Oct (first recorded point). High-volume market (~$6.8M). The companion 'Roadster flies for 1s+' market was ~0.67 just before the event and also resolved Yes. |
