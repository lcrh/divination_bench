"""I Ching casting by the yarrow-stalk method, with the King Wen sequence."""

from __future__ import annotations

import hashlib
import random
from typing import NamedTuple


class Trigram(NamedTuple):
    pinyin: str
    english: str
    image: str
    lines: tuple[int, int, int]  # bottom to top, 1 = yang


TRIGRAMS: dict[str, Trigram] = {
    t.pinyin: t
    for t in [
        Trigram("Qian", "The Creative", "Heaven", (1, 1, 1)),
        Trigram("Dui", "The Joyous", "Lake", (1, 1, 0)),
        Trigram("Li", "The Clinging", "Fire", (1, 0, 1)),
        Trigram("Zhen", "The Arousing", "Thunder", (1, 0, 0)),
        Trigram("Xun", "The Gentle", "Wind", (0, 1, 1)),
        Trigram("Kan", "The Abysmal", "Water", (0, 1, 0)),
        Trigram("Gen", "Keeping Still", "Mountain", (0, 0, 1)),
        Trigram("Kun", "The Receptive", "Earth", (0, 0, 0)),
    ]
}


class Hexagram(NamedTuple):
    number: int
    pinyin: str
    english: str
    lower: str
    upper: str

    @property
    def lines(self) -> tuple[int, ...]:
        return TRIGRAMS[self.lower].lines + TRIGRAMS[self.upper].lines

    @property
    def image(self) -> str:
        return f"{TRIGRAMS[self.upper].image} over {TRIGRAMS[self.lower].image}"

    def to_dict(self) -> dict:
        return {
            "number": self.number,
            "pinyin": self.pinyin,
            "english": self.english,
            "lower": self.lower,
            "upper": self.upper,
            "image": self.image,
            "lines": list(self.lines),
        }


# (number, pinyin, English after Wilhelm/Baynes, lower trigram, upper trigram)
_KING_WEN = [
    (1, "Qian", "The Creative", "Qian", "Qian"),
    (2, "Kun", "The Receptive", "Kun", "Kun"),
    (3, "Zhun", "Difficulty at the Beginning", "Zhen", "Kan"),
    (4, "Meng", "Youthful Folly", "Kan", "Gen"),
    (5, "Xu", "Waiting (Nourishment)", "Qian", "Kan"),
    (6, "Song", "Conflict", "Kan", "Qian"),
    (7, "Shi", "The Army", "Kan", "Kun"),
    (8, "Bi", "Holding Together (Union)", "Kun", "Kan"),
    (9, "Xiao Chu", "The Taming Power of the Small", "Qian", "Xun"),
    (10, "Lü", "Treading (Conduct)", "Dui", "Qian"),
    (11, "Tai", "Peace", "Qian", "Kun"),
    (12, "Pi", "Standstill (Stagnation)", "Kun", "Qian"),
    (13, "Tong Ren", "Fellowship with Men", "Li", "Qian"),
    (14, "Da You", "Possession in Great Measure", "Qian", "Li"),
    (15, "Qian", "Modesty", "Gen", "Kun"),
    (16, "Yu", "Enthusiasm", "Kun", "Zhen"),
    (17, "Sui", "Following", "Zhen", "Dui"),
    (18, "Gu", "Work on What Has Been Spoiled (Decay)", "Xun", "Gen"),
    (19, "Lin", "Approach", "Dui", "Kun"),
    (20, "Guan", "Contemplation (View)", "Kun", "Xun"),
    (21, "Shi He", "Biting Through", "Zhen", "Li"),
    (22, "Bi", "Grace", "Li", "Gen"),
    (23, "Bo", "Splitting Apart", "Kun", "Gen"),
    (24, "Fu", "Return (The Turning Point)", "Zhen", "Kun"),
    (25, "Wu Wang", "Innocence (The Unexpected)", "Zhen", "Qian"),
    (26, "Da Chu", "The Taming Power of the Great", "Qian", "Gen"),
    (27, "Yi", "The Corners of the Mouth (Providing Nourishment)", "Zhen", "Gen"),
    (28, "Da Guo", "Preponderance of the Great", "Xun", "Dui"),
    (29, "Kan", "The Abysmal (Water)", "Kan", "Kan"),
    (30, "Li", "The Clinging, Fire", "Li", "Li"),
    (31, "Xian", "Influence (Wooing)", "Gen", "Dui"),
    (32, "Heng", "Duration", "Xun", "Zhen"),
    (33, "Dun", "Retreat", "Gen", "Qian"),
    (34, "Da Zhuang", "The Power of the Great", "Qian", "Zhen"),
    (35, "Jin", "Progress", "Kun", "Li"),
    (36, "Ming Yi", "Darkening of the Light", "Li", "Kun"),
    (37, "Jia Ren", "The Family (The Clan)", "Li", "Xun"),
    (38, "Kui", "Opposition", "Dui", "Li"),
    (39, "Jian", "Obstruction", "Gen", "Kan"),
    (40, "Xie", "Deliverance", "Kan", "Zhen"),
    (41, "Sun", "Decrease", "Dui", "Gen"),
    (42, "Yi", "Increase", "Zhen", "Xun"),
    (43, "Guai", "Break-through (Resoluteness)", "Qian", "Dui"),
    (44, "Gou", "Coming to Meet", "Xun", "Qian"),
    (45, "Cui", "Gathering Together (Massing)", "Kun", "Dui"),
    (46, "Sheng", "Pushing Upward", "Xun", "Kun"),
    (47, "Kun", "Oppression (Exhaustion)", "Kan", "Dui"),
    (48, "Jing", "The Well", "Xun", "Kan"),
    (49, "Ge", "Revolution (Molting)", "Li", "Dui"),
    (50, "Ding", "The Caldron", "Xun", "Li"),
    (51, "Zhen", "The Arousing (Shock, Thunder)", "Zhen", "Zhen"),
    (52, "Gen", "Keeping Still, Mountain", "Gen", "Gen"),
    (53, "Jian", "Development (Gradual Progress)", "Gen", "Xun"),
    (54, "Gui Mei", "The Marrying Maiden", "Dui", "Zhen"),
    (55, "Feng", "Abundance (Fullness)", "Li", "Zhen"),
    (56, "Lü", "The Wanderer", "Gen", "Li"),
    (57, "Xun", "The Gentle (The Penetrating, Wind)", "Xun", "Xun"),
    (58, "Dui", "The Joyous, Lake", "Dui", "Dui"),
    (59, "Huan", "Dispersion (Dissolution)", "Kan", "Xun"),
    (60, "Jie", "Limitation", "Dui", "Kan"),
    (61, "Zhong Fu", "Inner Truth", "Dui", "Xun"),
    (62, "Xiao Guo", "Preponderance of the Small", "Gen", "Zhen"),
    (63, "Ji Ji", "After Completion", "Li", "Kan"),
    (64, "Wei Ji", "Before Completion", "Kan", "Li"),
]

HEXAGRAMS: dict[int, Hexagram] = {row[0]: Hexagram(*row) for row in _KING_WEN}
BY_LINES: dict[tuple[int, ...], Hexagram] = {h.lines: h for h in HEXAGRAMS.values()}

TOTAL_STALKS = 50
# The dividing hand splits the bundle roughly in half; the offset range spans a
# whole number of periods of 4 so that the traditional 1/16, 5/16, 7/16, 3/16
# line probabilities hold exactly.
SPLIT_OFFSETS = range(-8, 8)
LINE_NAMES = {6: "old yin", 7: "young yang", 8: "young yin", 9: "old yang"}


def _rng(question_id: str, seed: int) -> random.Random:
    digest = hashlib.sha256(f"{question_id}|iching|{seed}".encode()).hexdigest()
    return random.Random(int(digest, 16))


def _count_off(n: int) -> int:
    """Remainder when counting a heap off by fours (a full final group counts as 4)."""
    return n % 4 or 4


def stalks_removed(stalks: int, left: int) -> int:
    """One change: split into `left` and the rest, take one from the right heap,
    count both heaps by fours and set aside that stalk plus both remainders."""
    right = stalks - left - 1
    return 1 + _count_off(left) + _count_off(right)


def line_from_splits(splits: list[int]) -> int:
    """Line value 6-9 from the three split offsets of the three changes."""
    stalks = TOTAL_STALKS - 1
    for offset in splits:
        stalks -= stalks_removed(stalks, stalks // 2 + offset)
    return stalks // 4


def cast_line(rng: random.Random) -> int:
    return line_from_splits([rng.choice(SPLIT_OFFSETS) for _ in range(3)])


def _is_yang(value: int) -> int:
    return 1 if value in (7, 9) else 0


def cast_iching(question_id: str, seed: int) -> dict:
    rng = _rng(question_id, seed)
    values = [cast_line(rng) for _ in range(6)]
    primary = BY_LINES[tuple(_is_yang(v) for v in values)]
    changing = [i for i, v in enumerate(values, 1) if v in (6, 9)]
    relating = None
    if changing:
        transformed = tuple(
            1 - _is_yang(v) if v in (6, 9) else _is_yang(v) for v in values
        )
        relating = BY_LINES[transformed].to_dict()
    return {
        "method": "yarrow stalks",
        "line_values": values,
        "primary": primary.to_dict(),
        "changing_lines": changing,
        "relating": relating,
    }


def _hex_label(h: dict) -> str:
    return f"{h['number']} {h['pinyin']} / {h['english']} ({h['image']})"


def _line_glyph(value: int) -> str:
    glyph = "━━━━━━━━━" if _is_yang(value) else "━━━   ━━━"
    marker = {6: " x", 9: " o"}.get(value, "  ")
    return f"{glyph}{marker}"


def format_iching(cast: dict) -> str:
    values = cast["line_values"]
    changing = cast["changing_lines"]
    out = [f"Primary hexagram: {_hex_label(cast['primary'])}"]
    if changing:
        out.append(f"Changing lines: {', '.join(map(str, changing))}")
        out.append(f"Relating hexagram: {_hex_label(cast['relating'])}")
    else:
        out.append("Changing lines: none (no relating hexagram)")
    out.append("")
    out.append("Lines (top to bottom; o = old yang 9, x = old yin 6):")
    for pos in range(6, 0, -1):
        v = values[pos - 1]
        out.append(f"  {pos}  {_line_glyph(v)}   {v} ({LINE_NAMES[v]})")
    return "\n".join(out)
