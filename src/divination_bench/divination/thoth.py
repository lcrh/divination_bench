"""The 78-card Crowley-Harris Thoth Tarot and a free-form 3-card draw."""

from __future__ import annotations

import hashlib
import random

MAJOR_ARCANA: list[tuple[str, str]] = [
    ("0", "The Fool"),
    ("I", "The Magus"),
    ("II", "The Priestess"),
    ("III", "The Empress"),
    ("IV", "The Emperor"),
    ("V", "The Hierophant"),
    ("VI", "The Lovers"),
    ("VII", "The Chariot"),
    ("VIII", "Adjustment"),
    ("IX", "The Hermit"),
    ("X", "Fortune"),
    ("XI", "Lust"),
    ("XII", "The Hanged Man"),
    ("XIII", "Death"),
    ("XIV", "Art"),
    ("XV", "The Devil"),
    ("XVI", "The Tower"),
    ("XVII", "The Star"),
    ("XVIII", "The Moon"),
    ("XIX", "The Sun"),
    ("XX", "The Aeon"),
    ("XXI", "The Universe"),
]

SUITS = ["Wands", "Cups", "Swords", "Disks"]
COURT_RANKS = ["Knight", "Queen", "Prince", "Princess"]
NUMBER_WORDS = {
    2: "Two",
    3: "Three",
    4: "Four",
    5: "Five",
    6: "Six",
    7: "Seven",
    8: "Eight",
    9: "Nine",
    10: "Ten",
}
SMALL_CARD_TITLES: dict[str, list[str]] = {
    "Wands": [
        "Dominion",
        "Virtue",
        "Completion",
        "Strife",
        "Victory",
        "Valour",
        "Swiftness",
        "Strength",
        "Oppression",
    ],
    "Cups": [
        "Love",
        "Abundance",
        "Luxury",
        "Disappointment",
        "Pleasure",
        "Debauch",
        "Indolence",
        "Happiness",
        "Satiety",
    ],
    "Swords": [
        "Peace",
        "Sorrow",
        "Truce",
        "Defeat",
        "Science",
        "Futility",
        "Interference",
        "Cruelty",
        "Ruin",
    ],
    "Disks": [
        "Change",
        "Works",
        "Power",
        "Worry",
        "Success",
        "Failure",
        "Prudence",
        "Gain",
        "Wealth",
    ],
}


def build_deck() -> list[dict]:
    deck: list[dict] = [
        {"name": name, "arcana": "major", "atu": numeral}
        for numeral, name in MAJOR_ARCANA
    ]
    for suit in SUITS:
        deck.append(
            {"name": f"Ace of {suit}", "arcana": "minor", "suit": suit, "rank": "Ace"}
        )
        for n, title in zip(range(2, 11), SMALL_CARD_TITLES[suit], strict=True):
            deck.append(
                {
                    "name": f"{NUMBER_WORDS[n]} of {suit} ({title})",
                    "arcana": "minor",
                    "suit": suit,
                    "rank": str(n),
                    "title": title,
                }
            )
        for rank in COURT_RANKS:
            deck.append(
                {
                    "name": f"{rank} of {suit}",
                    "arcana": "minor",
                    "suit": suit,
                    "rank": rank,
                }
            )
    return deck


DECK = build_deck()


def _rng(question_id: str, seed: int) -> random.Random:
    digest = hashlib.sha256(f"{question_id}|tarot|{seed}".encode()).hexdigest()
    return random.Random(int(digest, 16))


def cast_tarot(question_id: str, seed: int) -> dict:
    """Shuffle the deck and draw three cards, upright (Thoth uses no reversals)."""
    deck = [dict(card) for card in DECK]
    _rng(question_id, seed).shuffle(deck)
    return {"deck": "Thoth", "spread": "three-card", "cards": deck[:3]}


def _describe(card: dict) -> str:
    if card["arcana"] == "major":
        return f"Atu {card['atu']}: {card['name']} - Major Arcana"
    return f"{card['name']} - Minor Arcana, suit of {card['suit']}"


def format_tarot(cast: dict) -> str:
    lines = ["Thoth Tarot, three-card spread (cards in the order drawn, all upright):"]
    lines += [f"{i}. {_describe(card)}" for i, card in enumerate(cast["cards"], 1)]
    return "\n".join(lines)
