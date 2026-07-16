# Lakers Rotation Optimizer

This repository contains a small Python-based rotation optimizer and working notes for the Lakers rotation modeling exercise.

The model is intended to evaluate 48-minute NBA rotations using projected five-man lineup net ratings. It tries to maximize the minute-weighted net rating while respecting practical rotation constraints around player minutes, stint length, substitutions, starter realism, and recovery after long stints.

## Current modeling status

The latest stable regular-season baseline from the conversation was a **+11.99 projected net rating** rotation using a 10-man rotation:

| Player | Minutes |
|---|---:|
| Luka Doncic | 36 |
| Austin Reaves | 32 |
| Walker Kessler | 34 |
| Quentin Grimes | 32 |
| Sandro Mamukelashvili | 28 |
| Jarred Vanderbilt | 26 |
| Jake LaRavia | 22 |
| Kevon Looney | 14 |
| Adou Thiero | 8 |
| Collin Sexton | 8 |
| Ziaire Williams | 0 |

The latest model preferred keeping Reaves at 32 because the non-Reaves bridge lineups were rated very strongly, particularly:

- Luka / Grimes / LaRavia / Vanderbilt / Looney: **+11.09**
- Luka / Grimes / Thiero / Sandro / Kessler: **+13.00**

Manual first-nine-minutes Luka variants were explored, but the best clean version tested came in lower, around **+11.83**, because the added early Luka minutes had to displace stronger mid-half Luka minutes elsewhere.

## Key constraints currently represented

### Player minute caps

Regular-season caps used in the working model:

| Player | Max minutes |
|---|---:|
| Luka Doncic | 36 |
| Austin Reaves | 36 |
| Walker Kessler | 34 |
| Quentin Grimes | 32 |
| Sandro Mamukelashvili | 28 |
| Jarred Vanderbilt | 28 |
| Jake LaRavia | 28 |
| Collin Sexton | 28 |
| Kevon Looney | 24 |
| Adou Thiero | 24 |
| Ziaire Williams | 24 |

### Half-minute balance

Each player has a per-half cap of:

```text
ceil(max_minutes / 2) + 1
```

This prevents unrealistic splits like a player getting almost all of their max minutes in one half.

### Stint rules

- Player stint minimum: **4 minutes**
- Lineup segment minimum: **2 minutes**
- Standard max stint: **12 minutes**
- Vanderbilt max stint: **9 minutes**
- If a player plays a max-length stint, the player must have **4 minutes of rest before returning**.
- If a player is about to play a max-length stint and the stint does not start at the beginning of the half, the player must have had **4 minutes of rest before it**.
- Halftime resets continuous-stint tracking.

### Starter rules

The starter logic was refined over the conversation. The latest sane flexible rule was:

- Same starter lineup in both halves.
- Starter lineup must include Luka, Reaves, and Kessler.
- Starter lineup must have projected net rating of at least **+10**.
- Thiero, Looney, and Ziaire cannot be starters.

This avoids the optimizer selecting unrealistic starter groups such as Luka / Reaves / Thiero / Vanderbilt / Kessler just to satisfy downstream constraints.

### Closing rule

The current model forces the highest-rated lineup to close the final 4 minutes:

```text
Luka / Reaves / Vanderbilt / Sandro / Kessler = +14.01
```

## Current best rotation: +11.99

| Time | Lineup | Net |
|---:|---|---:|
| 0-5 | Luka / Reaves / Grimes / Sandro / Kessler | +12.91 |
| 5-7 | Reaves / Grimes / LaRavia / Sandro / Looney | +10.75 |
| 7-12 | Luka / Grimes / LaRavia / Vanderbilt / Looney | +11.09 |
| 12-16 | Reaves / Sexton / LaRavia / Vanderbilt / Kessler | +10.55 |
| 16-20 | Luka / Grimes / Thiero / Sandro / Kessler | +13.00 |
| 20-24 | Luka / Reaves / Vanderbilt / Sandro / Kessler | +14.01 |
| 24-29 | Luka / Reaves / Grimes / Sandro / Kessler | +12.91 |
| 29-31 | Reaves / Grimes / LaRavia / Sandro / Looney | +10.75 |
| 31-36 | Luka / Grimes / LaRavia / Vanderbilt / Looney | +11.09 |
| 36-40 | Reaves / Sexton / LaRavia / Vanderbilt / Kessler | +10.55 |
| 40-42 | Luka / Reaves / Grimes / Thiero / Kessler | +9.00 |
| 42-44 | Luka / Grimes / Thiero / Sandro / Kessler | +13.00 |
| 44-48 | Luka / Reaves / Vanderbilt / Sandro / Kessler | +14.01 |

Weighted average:

```text
11.989 projected net rating
```

## How the optimization model works

At a high level, the optimizer assigns one five-man lineup to each minute or time segment in a 48-minute game.

The objective is:

```text
maximize sum(lineup_rating * minutes_played_by_lineup) / 48
```

The model then checks whether the resulting schedule satisfies:

1. One lineup on the court at every game minute.
2. Player total-minute limits.
3. Player half-minute limits.
4. Player stint minimum and maximum rules.
5. Rest rules after max-length stints.
6. Starter-lineup realism rules.
7. Closing lineup rule.
8. Rotation size limits.

The repository includes both:

- a simple scorer for fixed rotations, and
- a local-search optimizer that starts from a seed rotation and tries randomized legal modifications.

The local-search optimizer is useful because the exact mixed-integer program becomes difficult as the number of lineups and constraints grows.

## Files

- `optimizer.py` - runnable Python script with lineup ratings, constraints, current seed rotation, validation, and local search.
- `lineup_ratings.csv` - lineup rating table used by the optimizer.
- `current_rotation.csv` - latest +11.99 rotation table.
- `first9_luka_variant.csv` - manually tested first-nine-minutes Luka variant.

## Notes and caveats

- Lineup ratings are treated as static inputs.
- The optimizer does not know player hierarchy unless encoded through constraints or small objective bonuses.
- Small differences like 0.01 to 0.05 in projected net rating should not be overinterpreted.
- Some outputs are local optima from randomized search rather than globally proven MILP optima.
- Ziaire currently does not enter the optimized rotation because the tested Ziaire lineups are mostly below the main rotation alternatives.
