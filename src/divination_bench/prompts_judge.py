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


def _forecast(r: Reading, mode: JudgeMode, show_answer: bool) -> dict:
    out: dict = {}
    if mode == "full" and r.reading:
        out["reading"] = r.reading.strip()
    out["prediction"] = r.prediction.strip()
    if show_answer:
        out["chosen_answer"] = r.answer or "(none given)"
    return out


def _forecasts(q: Question, items: dict[str, Reading], mode: JudgeMode) -> dict:
    show_answer = q.question_type in ("binary", "multiple_choice")
    return {
        f"forecast {lab}": _forecast(r, mode, show_answer) for lab, r in items.items()
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
    question = _choice(ACCURACY_INSTRUCTIONS, ACCURACY_CRITERION, list(items), mode)
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
    question = _choice(PRECISION_INSTRUCTIONS, PRECISION_CRITERION, list(items), mode)
    return state, {"precision": question}
