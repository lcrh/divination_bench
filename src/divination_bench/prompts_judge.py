"""Prompt text for the judging stage."""

from __future__ import annotations

from .schemas import JudgeMode, Question, Reading

RUBRIC = """\
You are an impartial judge for a forecasting benchmark. [[MOCK:judge]]

You will see several anonymous forecasts about the same real-world question. \
They were written before the outcome was known, using only the background \
information shown to you. You are also told what actually happened. Your job \
is to rank the items by how well what they predicted matches what actually \
occurred.

Scoring rubric, in order of importance:
1. Core outcome. Did the item predict the outcome that actually happened (for \
binary / multiple-choice questions: the resolved answer)? This dominates \
everything else: an item that gets the core outcome right should normally \
outrank one that gets it wrong.
2. Specific, checkable details (numbers, margins, names, dates, sequence of \
events). Credit specifics only when the outcome information confirms them. \
Specifics that turned out wrong are penalised; a confident wrong detail is \
worse than no detail.
3. Vague, hedged, both-ways or unfalsifiable claims earn little credit, even \
if they can be read as consistent with the outcome. Restating facts that were \
already known beforehand is not a successful prediction.
4. Claims contradicted by the outcome are penalised.
Do not reward eloquence, length, confidence, symbolism or spiritual insight \
for their own sake. Judge only what the items claimed would happen against \
what did happen.

{mode_instructions}

Score each item from 0 to 10 on an absolute scale:
- 9-10: core outcome right and the specific details right.
- 7-8: core outcome right; specifics mostly right or sparse.
- 4-6: partially right, or right only in a vague / hedged way.
- 1-3: mostly wrong, or so vague it cannot be checked.
- 0: core outcome clearly wrong and details contradicted.

Then rank all items from best (rank 1) to worst (rank n). Ranks must be a \
permutation of 1..n with no ties; break near-ties on the correctness and \
specificity of checkable details. Ranks must agree with scores (a higher \
score never gets a worse rank).

Respond with only a JSON object and no other text, in this format:
{{"ranking": [{{"label": "A", "rank": 1, "score": 8, "rationale": "one or two sentences"}}, ...]}}
Include every item exactly once, using its letter as the label."""

MODE_INSTRUCTIONS: dict[str, str] = {
    "prediction": (
        "Each item is a standalone prediction, plus the chosen answer where the "
        "question has options. You are not told how the items were produced; "
        "judge them only on their content."
    ),
    "full": (
        "Each item is a full divination reading (a tarot spread or an I Ching "
        "hexagram interpreted for the question) followed by the standalone "
        "prediction derived from it. Read the whole item. Score primarily what "
        "the reading and prediction together claimed would happen versus what "
        "happened: the reading can earn credit where it clearly and specifically "
        "anticipated aspects of the outcome, and loses credit where it asserted "
        "things that did not happen. Symbolic language that could fit any "
        "outcome earns nothing."
    ),
}


def system_prompt(mode: JudgeMode) -> str:
    return RUBRIC.format(mode_instructions=MODE_INSTRUCTIONS[mode])


def _question_block(q: Question) -> str:
    lines = [
        "# Question",
        q.question.strip(),
        "",
        f"Question type: {q.question_type}",
    ]
    if q.options:
        lines.append("Options: " + " | ".join(q.options))
    lines += [
        f"Resolution criteria: {q.resolution_criteria.strip()}",
        "",
        f"# What was known beforehand (as of {q.context_as_of})",
        q.context_summary.strip(),
        "",
        f"# What actually happened (event date {q.event_date})",
        q.outcome_summary.strip(),
        "",
        f"Resolved answer: {q.resolved_answer}",
        "",
        "## Outcome sources",
    ]
    for s in sorted(q.outcome_sources, key=lambda s: s.published_date):
        lines.append(f"- {s.published_date} | {s.publisher}: {s.title}")
        if s.excerpt:
            lines.append(f"  Excerpt: {s.excerpt.strip()}")
    return "\n".join(lines)


def _item_block(label: str, r: Reading, mode: JudgeMode, show_answer: bool) -> str:
    lines = [f"[Item {label}]"]
    if mode == "full" and r.reading:
        lines += ["Reading:", _defang(r.reading.strip()), ""]
    lines += ["Prediction:", _defang(r.prediction.strip())]
    if show_answer:
        lines.append(f"Chosen answer: {r.answer or '(none given)'}")
    lines.append(f"[End of item {label}]")
    return "\n".join(lines)


def _defang(text: str) -> str:
    """Keep item text from forging an item header line."""
    return "\n".join(
        " " + line if line.startswith("[Item ") else line for line in text.splitlines()
    )


def user_prompt(q: Question, items: dict[str, Reading], mode: JudgeMode) -> str:
    show_answer = q.question_type in ("binary", "multiple_choice")
    blocks = [_item_block(lab, r, mode, show_answer) for lab, r in items.items()]
    labels = ", ".join(items)
    return (
        _question_block(q)
        + f"\n\n# Items to rank ({len(items)})\n\n"
        + "\n\n".join(blocks)
        + f"\n\nReturn the JSON ranking for all {len(items)} items ({labels})."
    )


def judge_messages(
    q: Question, items: dict[str, Reading], mode: JudgeMode
) -> list[dict]:
    return [
        {"role": "system", "content": system_prompt(mode)},
        {"role": "user", "content": user_prompt(q, items, mode)},
    ]


def retry_message(error: str, labels: list[str]) -> dict:
    return {
        "role": "user",
        "content": (
            f"Your previous response could not be used: {error}. Respond again with "
            "only the JSON object, ranking every item exactly once (labels "
            f"{', '.join(labels)}), ranks 1..{len(labels)} without ties."
        ),
    }
