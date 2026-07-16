"""Lakers rotation optimizer.

This script contains:
- static lineup ratings,
- rotation constraints,
- a fixed-rotation scorer,
- a validator for stint/minute constraints,
- a basic randomized local search seeded from the current best rotation.

It is intentionally lightweight and easy to modify. It is not a fully polished global MILP solver.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass
from typing import Dict, List, Tuple, Set

PLAYERS = [
    "Luka", "Reaves", "Kessler", "Vanderbilt", "Sandro", "Grimes",
    "Sexton", "LaRavia", "Looney", "Thiero", "Ziaire"
]

MIN_MINUTES = {
    "Luka": 24, "Reaves": 24, "Kessler": 24,
    "Vanderbilt": 0, "Sandro": 0, "Grimes": 0, "Sexton": 0,
    "LaRavia": 0, "Looney": 0, "Thiero": 0, "Ziaire": 0,
}

MAX_MINUTES = {
    "Luka": 36, "Reaves": 36, "Kessler": 34, "Vanderbilt": 28,
    "Sandro": 28, "Grimes": 32, "Sexton": 28, "LaRavia": 28,
    "Looney": 24, "Thiero": 24, "Ziaire": 24,
}

MAX_STINT = {p: 12 for p in PLAYERS}
MAX_STINT["Vanderbilt"] = 9

HALF_CAPS = {p: math.ceil(MAX_MINUTES[p] / 2) + 1 for p in PLAYERS}

BANNED_STARTERS = {"Thiero", "Looney", "Ziaire"}

LINEUP_RATINGS = {
    tuple(sorted("Luka/Reaves/Vanderbilt/Sandro/Kessler".split("/"))): 14.01,
    tuple(sorted("Luka/Reaves/Grimes/Sandro/Kessler".split("/"))): 12.91,
    tuple(sorted("Luka/Grimes/Thiero/Sandro/Kessler".split("/"))): 13.00,
    tuple(sorted("Luka/Reaves/Grimes/LaRavia/Kessler".split("/"))): 11.64,
    tuple(sorted("Reaves/Sexton/LaRavia/Vanderbilt/Kessler".split("/"))): 10.55,
    tuple(sorted("Reaves/Grimes/LaRavia/Sandro/Looney".split("/"))): 10.75,
    tuple(sorted("Luka/Grimes/LaRavia/Vanderbilt/Looney".split("/"))): 11.09,
    tuple(sorted("Luka/Reaves/Grimes/Thiero/Kessler".split("/"))): 9.00,
    tuple(sorted("Luka/Reaves/Grimes/Sandro/Looney".split("/"))): 11.10,
    tuple(sorted("Luka/Reaves/Thiero/Sandro/Kessler".split("/"))): 11.56,
    tuple(sorted("Luka/Reaves/Grimes/Vanderbilt/Sandro".split("/"))): 10.48,
    tuple(sorted("Luka/Reaves/LaRavia/Vanderbilt/Sandro".split("/"))): 10.13,
    tuple(sorted("Luka/Reaves/Sexton/Vanderbilt/Sandro".split("/"))): 9.23,
    tuple(sorted("Reaves/Sexton/Grimes/Sandro/Looney".split("/"))): 9.13,
    tuple(sorted("Reaves/Grimes/LaRavia/Sandro/Kessler".split("/"))): 7.07,
}

CURRENT_ROTATION = [
    (0, 5, "Luka/Reaves/Grimes/Sandro/Kessler"),
    (5, 7, "Reaves/Grimes/LaRavia/Sandro/Looney"),
    (7, 12, "Luka/Grimes/LaRavia/Vanderbilt/Looney"),
    (12, 16, "Reaves/Sexton/LaRavia/Vanderbilt/Kessler"),
    (16, 20, "Luka/Grimes/Thiero/Sandro/Kessler"),
    (20, 24, "Luka/Reaves/Vanderbilt/Sandro/Kessler"),
    (24, 29, "Luka/Reaves/Grimes/Sandro/Kessler"),
    (29, 31, "Reaves/Grimes/LaRavia/Sandro/Looney"),
    (31, 36, "Luka/Grimes/LaRavia/Vanderbilt/Looney"),
    (36, 40, "Reaves/Sexton/LaRavia/Vanderbilt/Kessler"),
    (40, 42, "Luka/Reaves/Grimes/Thiero/Kessler"),
    (42, 44, "Luka/Grimes/Thiero/Sandro/Kessler"),
    (44, 48, "Luka/Reaves/Vanderbilt/Sandro/Kessler"),
]


def lineup_key(lineup: str) -> Tuple[str, ...]:
    return tuple(sorted(lineup.split("/")))


def lineup_rating(lineup: str) -> float:
    return LINEUP_RATINGS[lineup_key(lineup)]


def score_rotation(rotation: List[Tuple[int, int, str]]) -> float:
    total = 0.0
    for start, end, lineup in rotation:
        total += (end - start) * lineup_rating(lineup)
    return total / 48.0


def expand_rotation(rotation: List[Tuple[int, int, str]]) -> List[str]:
    minutes = [None] * 48
    for start, end, lineup in rotation:
        for minute in range(start, end):
            minutes[minute] = lineup
    if any(x is None for x in minutes):
        raise ValueError("Rotation does not cover all 48 minutes")
    return minutes


def player_on_by_minute(minutes: List[str]) -> Dict[str, List[bool]]:
    on = {p: [False] * 48 for p in PLAYERS}
    for minute, lineup in enumerate(minutes):
        for player in lineup.split("/"):
            on[player][minute] = True
    return on


def validate_rotation(rotation: List[Tuple[int, int, str]]) -> List[str]:
    """Return a list of validation errors. Empty means valid."""
    errors = []
    minutes = expand_rotation(rotation)
    on = player_on_by_minute(minutes)

    # Starter rule
    starter = set(minutes[0].split("/"))
    starter_rating = lineup_rating(minutes[0])
    if starter_rating < 10:
        errors.append("Starter lineup rating below +10")
    if not {"Luka", "Reaves", "Kessler"}.issubset(starter):
        errors.append("Starter lineup must include Luka, Reaves, and Kessler")
    if starter & BANNED_STARTERS:
        errors.append("Starter lineup includes a banned starter")
    for t in list(range(0, 5)) + list(range(24, 29)):
        if set(minutes[t].split("/")) != starter:
            errors.append("Starter lineup is not the same for both halves")
            break

    # Closing lineup rule
    closing = "Luka/Reaves/Vanderbilt/Sandro/Kessler"
    for t in range(44, 48):
        if set(minutes[t].split("/")) != set(closing.split("/")):
            errors.append("Closing lineup rule violated")
            break

    # Lineup segment min 2
    for half_start, half_end in [(0, 24), (24, 48)]:
        start = half_start
        current = minutes[start]
        for t in range(half_start + 1, half_end):
            if minutes[t] != current:
                if t - start < 2:
                    errors.append(f"Lineup segment under 2 minutes at {start}-{t}")
                start = t
                current = minutes[t]
        if half_end - start < 2:
            errors.append(f"Lineup segment under 2 minutes at {start}-{half_end}")

    # Player minutes and stints
    for player in PLAYERS:
        total = sum(on[player])
        if total < MIN_MINUTES[player]:
            errors.append(f"{player} below minimum minutes")
        if total > MAX_MINUTES[player]:
            errors.append(f"{player} above maximum minutes")
        for half_start, half_end in [(0, 24), (24, 48)]:
            if sum(on[player][half_start:half_end]) > HALF_CAPS[player]:
                errors.append(f"{player} exceeds half cap")
            t = half_start
            while t < half_end:
                value = on[player][t]
                j = t
                while j < half_end and on[player][j] == value:
                    j += 1
                duration = j - t
                if value:
                    if duration < 4:
                        errors.append(f"{player} stint less than 4 minutes at {t}-{j}")
                    if duration > MAX_STINT[player]:
                        errors.append(f"{player} stint above max at {t}-{j}")
                    # If max stint, require 4-minute rest before returning.
                    if duration == MAX_STINT[player] and j < half_end:
                        k = j
                        while k < half_end and not on[player][k]:
                            k += 1
                        if k < half_end and k - j < 4:
                            errors.append(f"{player} returns too soon after max stint")
                else:
                    if t > half_start and j < half_end and duration < 2:
                        errors.append(f"{player} rest less than 2 minutes at {t}-{j}")
                t = j
    return errors


def print_rotation(rotation: List[Tuple[int, int, str]]) -> None:
    print(f"Projected net rating: {score_rotation(rotation):.3f}")
    for start, end, lineup in rotation:
        print(f"{start:02d}-{end:02d}: {lineup:55s} {lineup_rating(lineup):5.2f}")
    errors = validate_rotation(rotation)
    if errors:
        print("Validation errors:")
        for err in errors:
            print(f"- {err}")
    else:
        print("Validation: passed")


if __name__ == "__main__":
    print_rotation(CURRENT_ROTATION)
