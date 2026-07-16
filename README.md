# Lakers Rotation Optimizer

A small Python project for optimizing a 48-minute Lakers rotation from projected five-man lineup ratings.

The optimizer scores a rotation by assigning a projected net rating to each five-man lineup and averaging those ratings by minutes played. It also validates practical rotation rules such as minute caps, starter eligibility, and closing lineup requirements.

## Files

- `optimizer.py` - scoring, validation, and a simple local-search optimizer.
- `lineup_ratings_active.csv` - active lineup ratings used by the optimizer.
- `lineup_ratings_all.csv` - lineup rating audit table.
- `constraints.json` - editable rotation constraints.
- `current_rotation.csv` - current +11.99 seed rotation.
- `first9_luka_variant.csv` - comparison variant file.

## Usage

Validate the current rotation:

```bash
python optimizer.py
```

Run local search from the current seed:

```bash
python optimizer.py --mode local --iterations 200000 --seed 7
```

## Current seed result

The current seed rotation projects around **+11.99** and uses a 10-man rotation.

## Constraint reference

### Player minute limits

| Player | Minimum | Maximum |
|---|---:|---:|
| Luka | 24 | 36 |
| Reaves | 24 | 36 |
| Kessler | 24 | 34 |
| Grimes | 0 | 32 |
| Sandro | 0 | 28 |
| Vanderbilt | 0 | 28 |
| LaRavia | 0 | 28 |
| Sexton | 0 | 28 |
| Looney | 0 | 24 |
| Thiero | 0 | 24 |
| Ziaire | 0 | 24 |

### Per-half limits

Each player's per-half cap is:

```text
ceil(player_max_minutes / 2) + 1
```

### Stint and rest rules

- Player stint minimum: 4 minutes.
- Lineup segment minimum: 2 minutes.
- Standard max player stint: 12 minutes.
- Vanderbilt max player stint: 9 minutes.
- Minimum rest between separate stints inside a half: 2 minutes.
- If a player completes a max-length stint and later returns in the same half, the player must rest at least 4 minutes before returning.
- If a player is about to play a max-length stint and that stint does not begin at the start of a half, the player must have rested at least 4 minutes before that stint.
- Halftime resets stint and rest tracking.

### Starter rules

- The same starter lineup must start both halves.
- The starter lineup must include Luka, Reaves, and Kessler.
- The starter lineup must have a projected net rating of at least +10.
- Thiero, Looney, and Ziaire cannot be starters.

### Closing rule

The final 4 minutes must use:

```text
Luka / Reaves / Vanderbilt / Sandro / Kessler
```

### Rotation size

- Minimum players used: 8.
- Maximum players used: 11.
