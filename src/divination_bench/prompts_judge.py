"""Decisions-API requests for ranking forecasts with a decision model (TypeSafe Jev).

A group of anonymised forecasts is ranked by repeatedly asking which of the remaining
forecasts is best. Each round asks two Choice questions in separate requests:
- accuracy: the judge sees the forecasts together with what actually happened;
- precision: the judge sees the forecasts and the pre-event background only, so that
  knowing the outcome cannot colour how specific a forecast looks.
"""

from __future__ import annotations

from .schemas import JudgeMode, Question, Reading

ACCURACY_INSTRUCTIONS = (
    "Compare each forecast with what actually happened. Which forecast's claims about "
    "the outcome best match what actually happened? The central outcome matters most; "
    "specific details count in a forecast's favour only if they came true, and count "
    "against it if they turned out false. Restating facts already known beforehand, "
    "and vague claims that cannot be checked, earn nothing. Ignore style, length and "
    "symbolism."
)

PRECISION_INSTRUCTIONS = (
    "Which forecast is the most precise and committal about how events will turn out? "
    "Judge only claims that go beyond the background known beforehand: a definite "
    "central outcome plus concrete checkable details (numbers, names, margins, dates) "
    "is precise; hedged, both-ways or unfalsifiable claims are not, however long. Do "
    "not judge whether a forecast is plausible or correct, only how specific it is."
)

FULL_MODE_NOTE = (
    " Each forecast consists of a divination reading and the standalone prediction "
    "derived from it; treat concrete claims in either as part of the forecast. Symbolic "
    "language that could fit any outcome makes no claim."
)

ACCURACY_CRITERION = (
    "Forecast {label}'s claims match what actually happened better than any other "
    "forecast's."
)
PRECISION_CRITERION = "Forecast {label} is more precise and committal than any other."

# Reading mode: divinatory readings written before the event that analyse the
# situation without forecasting it. The accuracy question is deliberately a plain
# hindsight judgement with no penalty for vagueness (a proxy for a client saying
# "so true"); it alone ranks the readings. Precision is recorded as a diagnostic.
READING_ACCURACY_INSTRUCTIONS = (
    "Each reading was done for this situation before the event. Knowing what actually "
    "happened, which reading best describes it? Which one, read in hindsight, best "
    "captures what really went on and how things turned out?"
)
READING_PRECISION_INSTRUCTIONS = (
    "Each reading was written before the event and analyses the situation without "
    "forecasting it. Which reading is the most specific and concrete about this "
    "particular situation and how it is developing? Judge only what goes beyond the "
    "background known beforehand: definite, checkable characterisations of the actors, "
    "forces and direction of events are specific; generic symbolism that would fit any "
    "situation is not, however long. Do not judge whether a reading is plausible or "
    "correct, only how specific it is."
)
READING_ACCURACY_CRITERION = (
    "Reading {label} describes what actually happened better than any other reading."
)
READING_PRECISION_CRITERION = (
    "Reading {label} is more specific and concrete about this situation than any other."
)


def _forecast(r: Reading, mode: JudgeMode, show_answer: bool) -> dict:
    if mode == "reading":
        return {"reading": (r.reading or "").strip()}
    out: dict = {}
    if mode == "full" and r.reading:
        out["reading"] = r.reading.strip()
    out["prediction"] = r.prediction.strip()
    if show_answer:
        out["chosen_answer"] = r.answer or "(none given)"
    return out


def _forecasts(q: Question, items: dict[str, Reading], mode: JudgeMode) -> dict:
    show_answer = q.question_type in ("binary", "multiple_choice")
    noun = "reading" if mode == "reading" else "forecast"
    return {
        f"{noun} {lab}": _forecast(r, mode, show_answer) for lab, r in items.items()
    }


def _question(q: Question) -> dict:
    out: dict = {"question": q.question.strip()}
    if q.options:
        out["options"] = q.options
    return out


def _choice(instructions: str, criterion: str, labels: list[str], mode: JudgeMode):
    return {
        "type": "choice",
        "instructions": instructions + (FULL_MODE_NOTE if mode == "full" else ""),
        "criteria": {lab: criterion.format(label=lab) for lab in labels},
    }


def accuracy_request(
    q: Question, items: dict[str, Reading], mode: JudgeMode
) -> tuple[dict, dict]:
    """(state, questions) asking which of `items` (label -> reading, in presentation
    order) best matches the outcome."""
    state = {
        **_question(q),
        "resolution_criteria": q.resolution_criteria.strip(),
        "what_actually_happened": q.outcome_summary.strip(),
        "resolved_answer": q.resolved_answer,
        "outcome_sources": [
            {
                "date": str(s.published_date),
                "publisher": s.publisher,
                "title": s.title,
                **({"excerpt": s.excerpt.strip()} if s.excerpt else {}),
            }
            for s in sorted(q.outcome_sources, key=lambda s: s.published_date)
        ],
        **_forecasts(q, items, mode),
    }
    if mode == "reading":
        text = (READING_ACCURACY_INSTRUCTIONS, READING_ACCURACY_CRITERION)
    else:
        text = (ACCURACY_INSTRUCTIONS, ACCURACY_CRITERION)
    question = _choice(*text, list(items), mode)
    return state, {"accuracy": question}


def precision_request(
    q: Question, items: dict[str, Reading], mode: JudgeMode
) -> tuple[dict, dict]:
    """(state, questions) asking which of `items` is most precise; never includes
    the outcome."""
    state = {
        **_question(q),
        "background_known_beforehand": q.context_summary.strip(),
        **_forecasts(q, items, mode),
    }
    if mode == "reading":
        text = (READING_PRECISION_INSTRUCTIONS, READING_PRECISION_CRITERION)
    else:
        text = (PRECISION_INSTRUCTIONS, PRECISION_CRITERION)
    question = _choice(*text, list(items), mode)
    return state, {"precision": question}
