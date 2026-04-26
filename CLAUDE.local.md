# CLAUDE.local.md — Wall City Stats: Dev Context

## Project background

This repository analyzes statistics for **Wall City**, a competitive club ultimate frisbee team. Game data is exported from **Statto**, a mobile app for tracking ultimate frisbee statistics via pass-level logs. The current pipeline:

1. Downloads CSVs from a Google Drive folder (`make pull-data`)
2. Runs the `StatsBank` analysis class to compute player and game stats (`make compute-stats`)
3. Outputs aggregated stats to `data/processed/`

The long-term vision is a web app where teammates can log in and explore personal and team visualizations — tendencies, efficiency charts, field heat maps. The current focus is the statistical pipeline; the web layer does not exist yet.

**Key data source:** Statto exports 5 file types per game: `Passes vs.`, `Possessions vs.`, `Points vs.`, `Player Stats vs.`, and `Defensive Blocks vs.`. These are the raw inputs to `StatsBank`.

---

## Ultimate frisbee — rules and concepts relevant to the code

### Field
- **Dimensions:** 100m long × 36m wide. Two endzones of 18m depth each; central playing zone 64m.
- **Statto coordinate system:**
  - **Y-axis:** 0 = back of the *opponent's* endzone (the end we're attacking), 1 = back of our own endzone. Code converts this to `dist_to_endzone` (meters from the opponent's endzone line) via `y * 100 - 18`. Negative values mean the pass ended in the endzone (a score or turnover there).
  - **X-axis:** 0 = left sideline, 1 = right sideline → converted to meters 0–36. Field center is at 18m.
- **Brick mark:** 18m from each endzone line, used for pull positioning.

### Scoring and possessions
- Each **point** starts with a pull (kickoff throw). The team catching the pull is on **offense**.
- A **possession** is one team's unbroken sequence of passes. It ends with a score or a **turnover**.
- On a turnover, the disc changes hands where it landed — no re-pull. The defending team becomes offense immediately.
- A **break** occurs when the defense scores on the same point (i.e., after getting a turnover, the D-line converts).

### Player roles
- **Handler:** Primary ball-handlers. Responsible for moving the disc, initiating offense, and resetting when needed. Often involved in the first 1–2 passes after a turnover (D-line handler).
- **Cutter:** Players who run routes to get open downfield. Typically generate scoring opportunities through deep cuts or under cuts.

### Lines
- **O-line (offense):** Starts the point on offense (catching the pull). Goal: maintain possession and score.
- **D-line (defense):** Starts the point on defense (pulling). Goal: get a turnover and then convert for a break.

### Key strategies
- **Force (marking strategy):** The marker forces the thrower to one side of the field. Common forces:
  - **Forehand force (flick):** Marker takes away the backhand lane; thrower must throw forehand.
  - **Backhand force:** Marker takes away the forehand lane.
  - **FM (Force Middle):** Marker positioned to push throws toward the center of the field.
- **Zone defense:** Multiple defenders cover zones rather than marking individuals. Often used in wind.
- **Stack:** The standard offensive formation — cutters line up in a vertical stack downfield.
- **Field switch / reset to break side:** After a possession starts, the handlers may need to move the disc to the opposite side of the field from where it was caught. In the D-line handler analysis, a "field switch" means the possession successfully attacked the break side within the first 2–3 passes — a key indicator of handler quality.
- **Huck:** A long throw downfield (typically 20m+). High risk, high reward.
- **Swing:** A lateral pass from one side of the field to the other. Used to reset field position.
- **Dump:** A short backward pass to a handler behind the thrower. Resets the stall count.

### Stall count
- The thrower has a 10-second stall count. If they don't release by stall 10, the disc turns over (**stall out**).

---

## GPA models

Two logistic regression models (serialized as pickle files) are required for the GPA computation:

| File | Used for | Input features |
|------|----------|----------------|
| `models/linear_point_scored.p` | Per-pass scoring probability | `dist_to_endzone`, `dist_from_sideline` |
| `models/linear_gp.p` | Per-possession scoring probability | `dist_to_endzone`, `dist_from_sideline` |

Both are `statsmodels` fitted result objects. The possession model's `params.values[1]` and `[2]` are used as marginal GPA-per-meter coefficients in the directional GPA breakdown.

**These models were trained externally** (not in this repo). The notebook `notebooks/analyze_statistics.py` contains the code that originally trained them, though the exact training run is not reproducible from this repo alone. Place the `.p` files in `models/` before running the pipeline.

---

## Known limitations

- **Defensive GPA is blocks-only.** It does not account for defensive coverage, pressure, or preventing throws. A block is the only observable defensive event in Statto.
- **`_compute_max_gpa_all`** is defined in `StatsBank` but never called in the production pipeline (only `_compute_max_gpa_game` is used). It is retained for notebook exploration.
- **Error attribution is approximate.** When both thrower and receiver error flags are set on a turnover, each gets 50% blame. This is a simplification — some plays are clearly one person's fault.
- **`dist_from_sideline`** is calculated as `18 - dist_from_middle`, which gives 0 at the sideline and 18 at the center. Despite the name, higher values = further from the sideline = closer to the center.

---

## Development workflow

```bash
# 1. Download game CSVs from Google Drive
make pull-data GDRIVE_FOLDER_URL="<url>"

# 2. Place model files
cp path/to/linear_gp.p models/
cp path/to/linear_point_scored.p models/

# 3. Run the full pipeline
make compute-stats

# 4. Run tests
pytest tests/ -v
pytest tests/ -v -k "not Integration"   # skip tests that need model files
```

---

## Best practices when working with Claude Code on this project

- **Always run tests before and after modifying stats logic.** `pytest tests/ -v -k "not Integration"` should stay green at all times. These tests catch regressions in coordinate math, credit splitting, and column naming.
- **Stat correctness > code elegance.** The pipeline is numerically sensitive. When refactoring, verify that `aggregated_player_stats.csv` output is unchanged (or intentionally changed) by comparing before/after CSVs.
- **The notebook is the spec.** `notebooks/analyze_statistics.py` is the ground truth for what the stats mean. If a stat's definition in the code is unclear, refer back to the notebook and the README glossary.
- **Keep exploratory analysis in notebooks.** Bayesian inference (PyMC), permutation tests, bootstrap CIs, and D-line handler analysis live in `notebooks/`. Do not move heavy statistical experimentation into `src/`.
- **When adding a new stat:** (1) implement in `stats_bank.py`, (2) add it to the `reorder_player_stat_columns` desired order, (3) add it to the README glossary, (4) add a unit test. All four steps in the same PR.
- **Player name normalization is in `config.py`.** If you see an unexpected player name in the output data, add a mapping to `NAME_MAPPINGS` there.
- **The `game_efficiency` column** is a per-pass artifact (set equal for all passes in a game). It represents the combined scoring rate for that game and is used as the defensive block value and previously as a flat turnover penalty (now replaced by opponent field position).
