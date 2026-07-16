# Lakers Rotation Optimizer

This repository contains the Lakers rotation optimizer work-in-progress from the conversation. This regenerated version includes the **full lineup rating pool** that was captured, rather than only the small subset used in the README summary.

## Files

- `optimizer.py` - runnable Python script with embedded active lineup ratings and validation for the current rotation.
- `lineup_ratings_active.csv` - active post-Ayton lineup pool used by the optimizer. Contains **101** active lineups.
- `lineup_ratings_all.csv` - complete historical pool captured from the conversation, including obsolete Ayton/Bronny-era entries. Contains **134** total lineups.
- `current_rotation.csv` - current +11.99 regular-season rotation.
- `first9_luka_variant.csv` - first-9-minutes Luka variant tested around +11.83.
- `GITHUB_UPLOAD.md` - commands to push this folder to GitHub.

## Current best regular-season result

The current preferred regular-season rotation is the +11.99 model result:

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

## Key constraints

- Regular-season minute caps:
  - Luka 36
  - Reaves 36
  - Kessler 34
  - Grimes 32
  - Sandro 28
  - Vanderbilt 28
  - LaRavia 28
  - Sexton 28
  - Looney 24
  - Thiero 24
  - Ziaire 24
- Half cap: `ceil(max_minutes / 2) + 1`
- Player stint minimum: 4 minutes
- Lineup segment minimum: 2 minutes
- Max stint: 12 minutes, except Vanderbilt 9 minutes
- Max-length stint requires 4 minutes rest before returning
- Same starters both halves
- Starter must include Luka, Reaves, and Kessler
- Starter must be rated at least +10
- Thiero, Looney, and Ziaire cannot be starters
- Best lineup closes final 4 minutes

## Model summary

The optimizer assigns one five-man lineup to each minute or minute segment of a 48-minute game and maximizes:

```text
sum(lineup_rating * lineup_minutes) / 48
```

subject to the rotation constraints above. The exact MILP formulation became expensive, so the working script emphasizes validation and a reproducible current rotation. The ratings CSVs contain the broader lineup universe needed to run fuller searches locally.
