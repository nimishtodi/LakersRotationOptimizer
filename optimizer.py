"""Lakers rotation optimizer with full active lineup pool.

This version embeds the full active lineup set from the conversation, excluding obsolete Ayton/Bronny lineups by default.
The historical full list is available in lineup_ratings_all.csv.

Run:
    python optimizer.py
"""

from __future__ import annotations
import math, random
from pathlib import Path
from typing import Dict, List, Tuple

PLAYERS = ['Luka','Reaves','Kessler','Vanderbilt','Sandro','Grimes','Sexton','LaRavia','Looney','Thiero','Ziaire']
MIN_MINUTES = {'Luka':24,'Reaves':24,'Kessler':24,'Vanderbilt':0,'Sandro':0,'Grimes':0,'Sexton':0,'LaRavia':0,'Looney':0,'Thiero':0,'Ziaire':0}
MAX_MINUTES = {'Luka':36,'Reaves':36,'Kessler':34,'Vanderbilt':28,'Sandro':28,'Grimes':32,'Sexton':28,'LaRavia':28,'Looney':24,'Thiero':24,'Ziaire':24}
HALF_CAPS = {p: math.ceil(MAX_MINUTES[p] / 2) + 1 for p in PLAYERS}
MAX_STINT = {p: 12 for p in PLAYERS}
MAX_STINT['Vanderbilt'] = 9
BANNED_STARTERS = {'Thiero','Looney','Ziaire'}

# Embedded active lineup pool. Keys are normalized slash-separated player names sorted alphabetically.
LINEUP_RATINGS: Dict[str, float] = {
    'Grimes/Kessler/LaRavia/Looney/Luka': 12.28,
    'Grimes/Kessler/LaRavia/Luka/Reaves': 11.64,
    'Grimes/Kessler/LaRavia/Luka/Sandro': 10.71,
    'Grimes/Kessler/LaRavia/Luka/Sexton': 3.87,
    'Grimes/Kessler/LaRavia/Luka/Thiero': 5.4,
    'Grimes/Kessler/LaRavia/Luka/Vanderbilt': 6.05,
    'Grimes/Kessler/LaRavia/Luka/Ziaire': 3.27,
    'Grimes/Kessler/LaRavia/Reaves/Sandro': 7.07,
    'Grimes/Kessler/LaRavia/Reaves/Sexton': 5.4,
    'Grimes/Kessler/LaRavia/Reaves/Vanderbilt': 4.21,
    'Grimes/Kessler/LaRavia/Reaves/Ziaire': 7.44,
    'Grimes/Kessler/Looney/Luka/Reaves': 9.01,
    'Grimes/Kessler/Luka/Reaves/Sandro': 12.91,
    'Grimes/Kessler/Luka/Reaves/Sexton': 5.3,
    'Grimes/Kessler/Luka/Reaves/Thiero': 9.0,
    'Grimes/Kessler/Luka/Reaves/Vanderbilt': 9.49,
    'Grimes/Kessler/Luka/Reaves/Ziaire': 7.66,
    'Grimes/Kessler/Luka/Sandro/Sexton': 6.84,
    'Grimes/Kessler/Luka/Sandro/Thiero': 13.0,
    'Grimes/Kessler/Luka/Sandro/Vanderbilt': 8.63,
    'Grimes/Kessler/Luka/Sandro/Ziaire': 8.21,
    'Grimes/Kessler/Luka/Sexton/Vanderbilt': 8.11,
    'Grimes/Kessler/Luka/Thiero/Vanderbilt': 4.37,
    'Grimes/Kessler/Luka/Vanderbilt/Ziaire': 6.75,
    'Grimes/Kessler/Reaves/Sandro/Sexton': 5.29,
    'Grimes/Kessler/Reaves/Sandro/Thiero': 2.89,
    'Grimes/Kessler/Reaves/Sandro/Vanderbilt': 4.99,
    'Grimes/Kessler/Reaves/Sandro/Ziaire': 8.13,
    'Grimes/Kessler/Reaves/Sexton/Vanderbilt': 5.94,
    'Grimes/Kessler/Reaves/Thiero/Vanderbilt': 1.76,
    'Grimes/LaRavia/Looney/Luka/Sandro': 10.08,
    'Grimes/LaRavia/Looney/Luka/Vanderbilt': 11.09,
    'Grimes/LaRavia/Looney/Reaves/Sandro': 10.75,
    'Grimes/LaRavia/Looney/Reaves/Sexton': 2.8,
    'Grimes/LaRavia/Looney/Reaves/Vanderbilt': 8.61,
    'Grimes/LaRavia/Luka/Reaves/Sandro': 8.81,
    'Grimes/LaRavia/Luka/Reaves/Sexton': -0.02,
    'Grimes/LaRavia/Luka/Sandro/Vanderbilt': 5.43,
    'Grimes/Looney/Luka/Reaves/Sandro': 11.1,
    'Grimes/Looney/Luka/Reaves/Thiero': 4.1,
    'Grimes/Looney/Luka/Reaves/Vanderbilt': 6.14,
    'Grimes/Looney/Luka/Sandro/Sexton': 8.91,
    'Grimes/Looney/Luka/Sandro/Thiero': 13.24,
    'Grimes/Looney/Luka/Sandro/Vanderbilt': 10.08,
    'Grimes/Looney/Luka/Sandro/Ziaire': 5.03,
    'Grimes/Looney/Luka/Vanderbilt/Ziaire': 4.07,
    'Grimes/Looney/Reaves/Sandro/Sexton': 9.13,
    'Grimes/Looney/Reaves/Sandro/Thiero': 7.28,
    'Grimes/Looney/Reaves/Sandro/Vanderbilt': 9.52,
    'Grimes/Looney/Reaves/Sandro/Ziaire': 4.37,
    'Grimes/Looney/Reaves/Sexton/Vanderbilt': 6.05,
    'Grimes/Looney/Reaves/Thiero/Vanderbilt': 6.37,
    'Grimes/Looney/Reaves/Vanderbilt/Ziaire': 2.71,
    'Grimes/Luka/Reaves/Sandro/Sexton': 10.88,
    'Grimes/Luka/Reaves/Sandro/Thiero': 5.82,
    'Grimes/Luka/Reaves/Sandro/Vanderbilt': 10.48,
    'Grimes/Luka/Reaves/Thiero/Vanderbilt': 3.16,
    'Kessler/LaRavia/Luka/Reaves/Sandro': 11.36,
    'Kessler/LaRavia/Luka/Reaves/Sexton': 7.79,
    'Kessler/LaRavia/Luka/Reaves/Thiero': 5.28,
    'Kessler/LaRavia/Luka/Reaves/Vanderbilt': 9.41,
    'Kessler/LaRavia/Luka/Sandro/Sexton': 4.88,
    'Kessler/LaRavia/Luka/Sexton/Thiero': 1.99,
    'Kessler/LaRavia/Luka/Sexton/Vanderbilt': 6.13,
    'Kessler/LaRavia/Reaves/Sandro/Sexton': 3.77,
    'Kessler/LaRavia/Reaves/Sandro/Thiero': 7.23,
    'Kessler/LaRavia/Reaves/Sandro/Vanderbilt': 2.32,
    'Kessler/LaRavia/Reaves/Sexton/Thiero': 2.15,
    'Kessler/LaRavia/Reaves/Sexton/Vanderbilt': 10.55,
    'Kessler/Looney/Luka/Reaves/Vanderbilt': 14.39,
    'Kessler/Luka/Reaves/Sandro/Sexton': 7.76,
    'Kessler/Luka/Reaves/Sandro/Thiero': 11.56,
    'Kessler/Luka/Reaves/Sandro/Vanderbilt': 14.01,
    'Kessler/Luka/Reaves/Sandro/Ziaire': 5.4,
    'Kessler/Luka/Reaves/Sexton/Thiero': 9.0,
    'Kessler/Luka/Reaves/Sexton/Vanderbilt': 6.98,
    'Kessler/Luka/Reaves/Thiero/Vanderbilt': 7.13,
    'Kessler/Luka/Reaves/Vanderbilt/Ziaire': 7.23,
    'Kessler/Luka/Sandro/Sexton/Thiero': 4.96,
    'Kessler/Luka/Sandro/Sexton/Vanderbilt': 7.69,
    'Kessler/Reaves/Sandro/Sexton/Thiero': 4.14,
    'Kessler/Reaves/Sandro/Sexton/Vanderbilt': 5.31,
    'Kessler/Reaves/Sexton/Thiero/Vanderbilt': 3.04,
    'LaRavia/Looney/Luka/Reaves/Sandro': 9.83,
    'LaRavia/Looney/Luka/Sexton/Vanderbilt': 2.45,
    'LaRavia/Looney/Reaves/Sandro/Sexton': 11.19,
    'LaRavia/Looney/Reaves/Sandro/Thiero': 6.62,
    'LaRavia/Looney/Reaves/Sandro/Vanderbilt': 3.6,
    'LaRavia/Looney/Reaves/Sexton/Vanderbilt': 2.51,
    'LaRavia/Looney/Reaves/Sexton/Ziaire': -0.11,
    'LaRavia/Luka/Reaves/Sandro/Sexton': 7.83,
    'LaRavia/Luka/Reaves/Sandro/Thiero': 7.29,
    'LaRavia/Luka/Reaves/Sandro/Vanderbilt': 10.13,
    'Looney/Luka/Reaves/Sandro/Sexton': 10.83,
    'Looney/Luka/Reaves/Sandro/Thiero': 16.14,
    'Looney/Luka/Reaves/Sandro/Vanderbilt': 10.2,
    'Looney/Luka/Reaves/Sandro/Ziaire': 9.54,
    'Looney/Reaves/Sandro/Sexton/Vanderbilt': 6.88,
    'Looney/Reaves/Sexton/Vanderbilt/Ziaire': 1.5,
    'Luka/Reaves/Sandro/Sexton/Vanderbilt': 9.23,
    'Luka/Reaves/Sandro/Vanderbilt/Ziaire': 7.59,
}

CURRENT_ROTATION = [
    (0,5,'Luka/Reaves/Grimes/Sandro/Kessler'),
    (5,7,'Reaves/Grimes/LaRavia/Sandro/Looney'),
    (7,12,'Luka/Grimes/LaRavia/Vanderbilt/Looney'),
    (12,16,'Reaves/Sexton/LaRavia/Vanderbilt/Kessler'),
    (16,20,'Luka/Grimes/Thiero/Sandro/Kessler'),
    (20,24,'Luka/Reaves/Vanderbilt/Sandro/Kessler'),
    (24,29,'Luka/Reaves/Grimes/Sandro/Kessler'),
    (29,31,'Reaves/Grimes/LaRavia/Sandro/Looney'),
    (31,36,'Luka/Grimes/LaRavia/Vanderbilt/Looney'),
    (36,40,'Reaves/Sexton/LaRavia/Vanderbilt/Kessler'),
    (40,42,'Luka/Reaves/Grimes/Thiero/Kessler'),
    (42,44,'Luka/Grimes/Thiero/Sandro/Kessler'),
    (44,48,'Luka/Reaves/Vanderbilt/Sandro/Kessler'),
]

def norm(lineup: str | Tuple[str, ...]) -> str:
    if isinstance(lineup, tuple):
        players = list(lineup)
    else:
        players = [p.strip() for p in lineup.split('/')]
    return '/'.join(sorted(players))

def rating(lineup: str) -> float:
    return LINEUP_RATINGS[norm(lineup)]

def score_rotation(rotation: List[Tuple[int,int,str]]) -> float:
    return sum((b-a) * rating(l) for a,b,l in rotation) / 48.0

def expand(rotation: List[Tuple[int,int,str]]) -> List[str]:
    out = [None] * 48
    for a,b,lineup in rotation:
        for t in range(a,b): out[t] = lineup
    if any(v is None for v in out):
        raise ValueError('rotation does not cover all 48 minutes')
    return out

def validate(rotation: List[Tuple[int,int,str]]) -> List[str]:
    errors = []
    minutes = expand(rotation)
    on = {p:[False]*48 for p in PLAYERS}
    for t,lineup in enumerate(minutes):
        for player in lineup.split('/'):
            on[player][t] = True

    starter = set(minutes[0].split('/'))
    if rating(minutes[0]) < 10: errors.append('starter rating below +10')
    if not {'Luka','Reaves','Kessler'}.issubset(starter): errors.append('starter must include Luka/Reaves/Kessler')
    if starter & BANNED_STARTERS: errors.append('starter includes banned starter')
    for t in list(range(0,5)) + list(range(24,29)):
        if set(minutes[t].split('/')) != starter:
            errors.append('same-starters-both-halves rule violated')
            break

    closing = set('Luka/Reaves/Vanderbilt/Sandro/Kessler'.split('/'))
    for t in range(44,48):
        if set(minutes[t].split('/')) != closing:
            errors.append('closing lineup rule violated')
            break

    for hs,he in [(0,24),(24,48)]:
        start = hs; cur = minutes[hs]
        for t in range(hs+1, he):
            if minutes[t] != cur:
                if t-start < 2: errors.append(f'lineup segment <2 at {start}-{t}')
                start = t; cur = minutes[t]
        if he-start < 2: errors.append(f'lineup segment <2 at {start}-{he}')

    for p in PLAYERS:
        total = sum(on[p])
        if total < MIN_MINUTES[p]: errors.append(f'{p} below min')
        if total > MAX_MINUTES[p]: errors.append(f'{p} above max')
        for hs,he in [(0,24),(24,48)]:
            if sum(on[p][hs:he]) > HALF_CAPS[p]: errors.append(f'{p} exceeds half cap')
            t = hs
            while t < he:
                val = on[p][t]; j = t
                while j < he and on[p][j] == val: j += 1
                d = j - t
                if val:
                    if d < 4: errors.append(f'{p} stint under 4 at {t}-{j}')
                    if d > MAX_STINT[p]: errors.append(f'{p} stint over max at {t}-{j}')
                    if d == MAX_STINT[p] and j < he:
                        k = j
                        while k < he and not on[p][k]: k += 1
                        if k < he and k-j < 4: errors.append(f'{p} returns too soon after max stint')
                else:
                    if t > hs and j < he and d < 2: errors.append(f'{p} rest under 2 at {t}-{j}')
                t = j
    return errors

def print_summary(rotation=CURRENT_ROTATION):
    print(f'Projected net rating: {score_rotation(rotation):.3f}')
    for a,b,lineup in rotation:
        print(f'{a:02d}-{b:02d} {lineup:55s} {rating(lineup):6.2f}')
    errors = validate(rotation)
    print('Validation:', 'passed' if not errors else 'failed')
    for e in errors: print('-', e)

if __name__ == '__main__':
    print(f'Active lineup count: {len(LINEUP_RATINGS)}')
    print_summary()
