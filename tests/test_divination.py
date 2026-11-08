from collections import Counter
from fractions import Fraction
from itertools import product

import pytest

from divination_bench.divination import cast, cast_iching, cast_tarot, format_iching
from divination_bench.divination.iching import (
    BY_LINES,
    HEXAGRAMS,
    SPLIT_OFFSETS,
    cast_line,
    line_from_splits,
)
from divination_bench.divination.thoth import DECK
from divination_bench.schemas import Method


def test_deck_has_78_unique_cards():
    names = [c["name"] for c in DECK]
    assert len(names) == 78
    assert len(set(names)) == 78
    assert sum(c["arcana"] == "major" for c in DECK) == 22
    for suit in ("Wands", "Cups", "Swords", "Disks"):
        assert sum(c.get("suit") == suit for c in DECK) == 14


@pytest.mark.parametrize(
    "name",
    [
        "The Fool",
        "The Magus",
        "Adjustment",
        "Lust",
        "Art",
        "The Aeon",
        "The Universe",
        "Ace of Disks",
        "Two of Wands (Dominion)",
        "Seven of Cups (Debauch)",
        "Ten of Swords (Ruin)",
        "Five of Disks (Worry)",
        "Prince of Swords",
        "Princess of Cups",
        "Knight of Wands",
        "Queen of Disks",
    ],
)
def test_thoth_names(name):
    assert name in {c["name"] for c in DECK}


def test_no_rws_names():
    names = {c["name"] for c in DECK}
    for rws in ("The Magician", "Justice", "Strength", "Judgement", "The World"):
        assert rws not in names
    assert not any("Pentacles" in n or "Page" in n for n in names)


def test_tarot_cast_deterministic_and_distinct():
    a = cast_tarot("q1", 0)
    assert a == cast_tarot("q1", 0)
    assert a != cast_tarot("q1", 1)
    assert a != cast_tarot("q2", 0)
    assert len({c["name"] for c in a["cards"]}) == 3
    assert a["deck"] == "Thoth"


def test_tarot_draws_cover_deck():
    seen = {c["name"] for s in range(400) for c in cast_tarot("q", s)["cards"]}
    assert len(seen) == 78


def test_cast_dispatch():
    assert cast("q", Method.predict, 0) == (None, None)
    data, text = cast("q", Method.tarot, 3)
    assert data == cast_tarot("q", 3)
    assert all(c["name"] in text for c in data["cards"])
    data, text = cast("q", Method.iching, 3)
    assert data == cast_iching("q", 3)
    assert text == format_iching(data)


def test_yarrow_probabilities_exact():
    counts = Counter(
        line_from_splits(list(s)) for s in product(SPLIT_OFFSETS, repeat=3)
    )
    total = sum(counts.values())
    probs = {v: Fraction(n, total) for v, n in counts.items()}
    assert probs == {
        6: Fraction(1, 16),
        7: Fraction(5, 16),
        8: Fraction(7, 16),
        9: Fraction(3, 16),
    }


def test_yarrow_sampling_matches():
    import random

    rng = random.Random(0)
    n = 40000
    counts = Counter(cast_line(rng) for _ in range(n))
    for value, p in {6: 1 / 16, 7: 5 / 16, 8: 7 / 16, 9: 3 / 16}.items():
        assert abs(counts[value] / n - p) < 0.01


def test_hexagram_table_complete_and_unique():
    assert sorted(HEXAGRAMS) == list(range(1, 65))
    assert len(BY_LINES) == 64
    assert set(BY_LINES) == set(product((0, 1), repeat=6))


def test_king_wen_pairs():
    # Each even hexagram is its predecessor turned upside down, or its complement
    # when the predecessor is symmetric.
    for n in range(1, 65, 2):
        a, b = HEXAGRAMS[n].lines, HEXAGRAMS[n + 1].lines
        expected = tuple(1 - x for x in a) if a == a[::-1] else a[::-1]
        assert b == expected, n


@pytest.mark.parametrize(
    "number,pinyin,english,lower,upper",
    [
        (1, "Qian", "The Creative", "Qian", "Qian"),
        (2, "Kun", "The Receptive", "Kun", "Kun"),
        (3, "Zhun", "Difficulty at the Beginning", "Zhen", "Kan"),
        (11, "Tai", "Peace", "Qian", "Kun"),
        (12, "Pi", "Standstill (Stagnation)", "Kun", "Qian"),
        (24, "Fu", "Return (The Turning Point)", "Zhen", "Kun"),
        (29, "Kan", "The Abysmal (Water)", "Kan", "Kan"),
        (30, "Li", "The Clinging, Fire", "Li", "Li"),
        (31, "Xian", "Influence (Wooing)", "Gen", "Dui"),
        (43, "Guai", "Break-through (Resoluteness)", "Qian", "Dui"),
        (49, "Ge", "Revolution (Molting)", "Li", "Dui"),
        (50, "Ding", "The Caldron", "Xun", "Li"),
        (51, "Zhen", "The Arousing (Shock, Thunder)", "Zhen", "Zhen"),
        (54, "Gui Mei", "The Marrying Maiden", "Dui", "Zhen"),
        (61, "Zhong Fu", "Inner Truth", "Dui", "Xun"),
        (63, "Ji Ji", "After Completion", "Li", "Kan"),
        (64, "Wei Ji", "Before Completion", "Kan", "Li"),
    ],
)
def test_hexagram_spot_checks(number, pinyin, english, lower, upper):
    h = HEXAGRAMS[number]
    assert (h.pinyin, h.english, h.lower, h.upper) == (pinyin, english, lower, upper)


def test_hexagram_line_patterns():
    assert HEXAGRAMS[24].lines == (1, 0, 0, 0, 0, 0)
    assert HEXAGRAMS[23].lines == (0, 0, 0, 0, 0, 1)
    assert HEXAGRAMS[63].lines == (1, 0, 1, 0, 1, 0)
    assert HEXAGRAMS[64].lines == (0, 1, 0, 1, 0, 1)
    assert HEXAGRAMS[24].image == "Earth over Thunder"


def test_iching_cast_consistent():
    for seed in range(200):
        c = cast_iching("q", seed)
        assert c == cast_iching("q", seed)
        values = c["line_values"]
        assert len(values) == 6 and set(values) <= {6, 7, 8, 9}
        yang = tuple(int(v in (7, 9)) for v in values)
        assert tuple(c["primary"]["lines"]) == yang
        assert c["changing_lines"] == [
            i + 1 for i, v in enumerate(values) if v in (6, 9)
        ]
        if c["changing_lines"]:
            flipped = tuple(
                1 - y if i + 1 in c["changing_lines"] else y for i, y in enumerate(yang)
            )
            assert tuple(c["relating"]["lines"]) == flipped
        else:
            assert c["relating"] is None
    assert cast_iching("q", 0) != cast_iching("q", 1)


def test_format_iching_mentions_everything():
    for seed in range(50):
        c = cast_iching("fmt", seed)
        text = format_iching(c)
        assert f"{c['primary']['number']} {c['primary']['pinyin']}" in text
        if c["relating"]:
            assert f"Relating hexagram: {c['relating']['number']}" in text
            assert ", ".join(map(str, c["changing_lines"])) in text
        else:
            assert "no relating hexagram" in text
