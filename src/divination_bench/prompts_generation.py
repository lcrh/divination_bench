"""Prompts for producing readings / predictions, and parsing of the tagged output."""

from __future__ import annotations

import re

from .schemas import Method, Question

_PREDICTION_RULES = """\
The prediction must be a concrete, standalone forecast of what will actually happen, \
written so that it makes complete sense to someone who never saw anything else you wrote. \
Be specific and checkable: who, what, when, by how much. Aim for 80-200 words. Commit to \
a definite outcome rather than hedging or listing every possibility."""

_DIVINATION_RULES = (
    """\
Take the divination seriously and commit to what it indicates: the prediction must be \
derived from your reading, not from your own independent analysis of the question. \
Inside the <prediction> tag, do NOT mention cards, hexagrams, lines, the reading, symbols, \
or divination of any kind - state only the forecast itself.

"""
    + _PREDICTION_RULES
)

_DIVINATION_FORMAT = """\
Respond in exactly this format:
<reading>
Your full divinatory interpretation, applied to the question.
</reading>
<prediction>
Your standalone forecast of what will happen.
</prediction>
{answer_line}"""

_PREDICT_FORMAT = """\
Respond in exactly this format:
<prediction>
Your forecast of what will happen.
</prediction>
{answer_line}"""

_ANSWER_LINE = (
    "<answer>EXACTLY ONE of the listed options, copied verbatim</answer>\n"
    "The <answer> tag is required because this question has a fixed set of options."
)
_NO_ANSWER_LINE = "This question is open-ended: do not include an <answer> tag."

SYSTEM_PROMPTS: dict[Method, str] = {
    Method.tarot: f"""\
You are an expert tarot reader working with the Crowley-Harris Thoth Tarot. You read in the \
Thoth tradition as set out in Aleister Crowley's The Book of Thoth: use the Thoth names, \
titles, astrological and Qabalistic attributions and imagery of the cards (for example \
Adjustment, Lust, Art, The Aeon; Princes and Princesses; the small-card titles such as \
Dominion or Ruin). The cards have been shuffled and drawn for the question by a random \
procedure; there are no reversals. This is a free-form three-card spread with no fixed \
positional meanings: read the three cards in the order drawn, individually and together, \
and apply them to the question.

{_DIVINATION_RULES}""",
    Method.iching: f"""\
You are an expert I Ching diviner. A hexagram has been cast for the question using the \
traditional yarrow-stalk method. Interpret it in the classical way, drawing on the received \
texts (the Judgement, the Image and the line statements, as in the Wilhelm/Baynes \
translation and its commentaries): interpret the primary hexagram, each changing line, and \
the relating (transformed) hexagram, then apply the whole to the question.

{_DIVINATION_RULES}""",
    Method.predict: f"""\
You are an expert forecaster. Using the information provided and your own knowledge and \
judgement, forecast the outcome of the question.

{_PREDICTION_RULES}""",
}


def _question_block(question: Question) -> str:
    parts = [
        f"Question: {question.question}",
        f"Question type: {question.question_type}",
    ]
    if question.options:
        parts.append("Options: " + "; ".join(question.options))
    parts += [
        "",
        "Background:",
        question.context_summary.strip(),
        "",
        f"Information is current as of {question.latest_context_source_date.isoformat()}.",
    ]
    return "\n".join(parts)


def _has_options(question: Question) -> bool:
    return question.question_type in ("binary", "multiple_choice")


def build_generation_messages(
    question: Question, method: Method, cast_text: str | None
) -> list[dict]:
    method = Method(method)
    answer_line = _ANSWER_LINE if _has_options(question) else _NO_ANSWER_LINE
    sections = [_question_block(question)]
    if method == Method.predict:
        sections.append(_PREDICT_FORMAT.format(answer_line=answer_line))
    else:
        if not cast_text:
            raise ValueError(f"method {method} requires cast_text")
        heading = (
            "The cards drawn:"
            if method == Method.tarot
            else "The hexagram cast with yarrow stalks:"
        )
        sections.append(f"{heading}\n{cast_text}")
        sections.append(_DIVINATION_FORMAT.format(answer_line=answer_line))
    return [
        {"role": "system", "content": SYSTEM_PROMPTS[method]},
        {"role": "user", "content": "\n\n".join(sections)},
    ]


def _last_tag(text: str, tag: str) -> str | None:
    """Content of the last non-empty <tag>...</tag>; reasoning models sometimes echo
    the format instructions before the real answer."""
    matches = re.findall(
        rf"<{tag}>(.*?)</{tag}>", text, flags=re.DOTALL | re.IGNORECASE
    )
    matches = [m.strip() for m in matches if m.strip()]
    return matches[-1] if matches else None


def normalize_answer(raw: str | None, options: list[str] | None) -> str | None:
    if not raw or not options:
        return None
    cleaned = raw.strip().strip("\"'`*.").strip().casefold()
    by_fold = {o.casefold(): o for o in options}
    if cleaned in by_fold:
        return by_fold[cleaned]
    prefixed = [
        o for o in options if re.match(rf"{re.escape(o.casefold())}\b", cleaned)
    ]
    if prefixed:
        return max(prefixed, key=len)
    return None


def parse_generation(text: str, question: Question, method: Method) -> dict:
    method = Method(method)
    reading = _last_tag(text, "reading") if method != Method.predict else None
    if method != Method.predict and reading is None:
        raise ValueError("missing <reading> tag")
    prediction = _last_tag(text, "prediction")
    if prediction is None:
        raise ValueError("missing <prediction> tag")
    answer = None
    if _has_options(question):
        raw_answer = _last_tag(text, "answer")
        if raw_answer is None:
            raise ValueError("missing <answer> tag")
        answer = normalize_answer(raw_answer, question.options)
    return {"reading": reading, "prediction": prediction, "answer": answer}
