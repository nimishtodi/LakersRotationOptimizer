# Lakers Rotation Optimizer

A small Python project for optimizing a 48-minute Lakers rotation from projected five-man lineup ratings.

The project answers one practical question: given a pool of rated lineups and realistic rotation rules, what minute-by-minute rotation produces the highest projected net rating?

## Repository contents

- `optimizer.py` - scoring, validation, local-search optimization, and segment-grid MILP optimization.
- `lineup_ratings_active.csv` - active lineup pool used by the optimizer. Contains **93** lineups.
- `lineup_ratings_all.csv` - audit trail of all captured lineups. Contains **103** lineups, including obsolete or superseded entries.
- `constraints.json` - editable rotation constraints.
- `current_rotation.csv` - current seed rotation, projected at about **+11.99**.
- `first9_luka_variant.csv` - comparison variant where Luka plays at least the first 9 minutes of the 1st and 3rd quarters.

## Current model setup

The optimizer uses regular-season workload limits, including Luka 36, Reaves 36, Kessler 34, Grimes 32, Sandro 28, Vanderbilt 28, LaRavia 28, Sexton 28, Looney 24, Thiero 24, and Ziaire 24.

The model also enforces starter realism, stint rules, rest rules, and a closing-lineup rule. The starter must include Luka, Reaves, and Kessler; must be rated at least +10; and cannot include Thiero, Looney, or Ziaire. The final 4 minutes use Luka / Reaves / Vanderbilt / Sandro / Kessler.

## How the optimizer works

A rotation is represented as a sequence of lineups covering all 48 minutes. Each lineup has a projected net rating. The objective is:

```text
maximize sum(lineup_rating * lineup_minutes) / 48
```

`optimizer.py` supports two optimization modes:

1. `local` - randomized free-minute local search from the current seed rotation.
2. `milp-segment` - exact mixed-integer optimization over a segment grid using scipy.

The validator checks player minute caps, half caps, minimum stints, maximum stints, rest after max stints, lineup segment length, starter rules, rotation size, and the closing lineup.


## Fidelity to the conversation model

The default validation and `--mode local` path matches the latest working free-minute model used for the +11.99 rotation. The `--mode milp-segment` path is a faster segment-grid approximation for diagnostics, not the full experimental minute-level MILP from the chat. See `FIDELITY_NOTES.md` for the exact comparison.

## Usage

Validate the current seed rotation:

```bash
python optimizer.py
```

Run free-minute local search:

```bash
python optimizer.py --mode local --iterations 200000 --seed 7
```

Run segment-grid MILP:

```bash
python optimizer.py --mode milp-segment --time-limit 120
```

## Notes

This is a research script, not a polished production solver. The lineup ratings are static inputs, and small differences in projected net rating should not be overinterpreted.
