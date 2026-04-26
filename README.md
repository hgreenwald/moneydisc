# moneydisc
A repository designed to calculate and analyze statistics for ultimate frisbee teams from pass logs. Originally developed on top of outputs from the Statto App.

## Project structure

- `src/moneydisc/data_ingestion/`: data download utilities
- `src/moneydisc/analysis/`: analysis entrypoints
- `data/raw/`: downloaded source files
- `data/processed/`: computed outputs
- `tests/`: unit tests

## Make targets

- `make pull-data GDRIVE_FOLDER_URL="<google-drive-folder-url>"`
  - Downloads game CSV files from a Google Drive folder into `data/raw`.
- `make compute-stats`
  - Runs the full StatsBank pipeline over files in `data/raw`, writing player and game stats to `data/processed/`.

## Statistics glossary

All statistics output by the pipeline are defined below. The primary output is `data/processed/aggregated_player_stats.csv`.

### Game-level stats (`game_stats.csv`)

| Column | Description |
|--------|-------------|
| `game_id` | Internal Statto game key (opponent + timestamp) |
| `game_name` | Human-readable game label (e.g. "Heidees - Tom's Tourney") |
| `possessions` | Total possessions Wall City had |
| `opponent_possessions` | Total possessions the opponent had |
| `passes` | Total passes thrown |
| `points` | Total points played |
| `our_score` / `opponent_score` | Final score |
| `our_scoring_efficiency` | `our_score / possessions` |
| `opponent_scoring_efficiency` | `opponent_score / opponent_possessions` |
| `combined_scoring_efficiency` | `(our_score + opponent_score) / total_possessions` — used as the baseline penalty magnitude for turnovers |

### Player offensive stats

| Column | Description |
|--------|-------------|
| `throws` | Total pass attempts (including turnovers) |
| `completions` | Completed throws |
| `completion_percentage` | `completions / throws` |
| `touches` | `throws + goals` — total times the player had the disc |
| `assists` | Passes directly resulting in a score |
| `secondary_assists` | Second-to-last pass before a score |
| `goals` | Times the player caught a score |
| `hucks_thrown` / `hucks_completed` | Long passes attempted / completed |
| `swings` | Lateral passes thrown (side-to-side resets) |
| `dumps` | Short backward passes to reset the disc |
| `turnover_thrown` | Turnovers where the thrower was at fault (fractional if shared blame) |
| `receiver_turnovers` | Turnovers where the receiver was at fault (fractional if shared blame) |
| `total_turnovers` | `turnover_thrown + receiver_turnovers` |
| `throwing_meters_gained` | Total downfield distance gained on completed throws (meters) |
| `throwing_centering_meters_gained` | Total horizontal centering distance gained on completed throws |
| `receiving_meters_gained` | Total downfield distance gained on completed catches |
| `receiving_centering_meters_gained` | Total horizontal centering distance gained on completed catches |
| `off. plus/minus` | `goals + assists - total_turnovers` |
| `off. real plus/minus` | `(goals + assists) / 2 - total_turnovers` — each goal is split between passer and catcher |

### GPA (Goal Probability Added)

GPA measures how much a player moves the needle on scoring probability with each touch. It is computed from two logistic regression models trained on historical data: one predicting scoring probability from field position at the start of a possession, and one predicting it per-pass.

| Column | Description |
|--------|-------------|
| `thrower_gpa` | GPA contributed as the thrower (includes turnover penalty) |
| `receiver_gpa` | GPA contributed as the receiver (includes turnover penalty) |
| `total_offensive_gpa` | `thrower_gpa + receiver_gpa` |
| `thrower_gpa_no_turns` | Thrower GPA on completed throws only |
| `receiver_gpa_no_turns` | Receiver GPA on completed catches only |
| `total_offensive_gpa_no_turns` | Combined GPA excluding turnover plays |
| `max_gpa` | Theoretical maximum GPA achievable given the possessions a player was on the field for, divided by 2 (since credit is always shared between thrower and receiver) |
| `adjusted_gpa` / `adjusted_offensive_gpa` | `total_offensive_gpa / max_gpa` — opportunity-adjusted GPA |
| `adjusted_thrower_gpa` | `thrower_gpa / max_gpa` |
| `adjusted_receiver_gpa` | `receiver_gpa / max_gpa` |

### Directional GPA

These columns decompose throwing/receiving GPA into vertical and horizontal components using the possession model's marginal coefficients per meter.

| Column | Description |
|--------|-------------|
| `gpa_vert_throwing` | GPA from downfield throwing yardage |
| `gpa_horz_throwing` | GPA from horizontal centering on throws |
| `gpa_total_throwing` | `gpa_vert_throwing + gpa_horz_throwing` |
| `gpa_vert_receiving` | GPA from downfield receiving yardage |
| `gpa_horz_receiving` | GPA from horizontal centering on catches |
| `gpa_total_receiving` | `gpa_vert_receiving + gpa_horz_receiving` |

### Defensive stats

| Column | Description |
|--------|-------------|
| `blocks` | Number of defensive blocks recorded |
| `total_defensive_gpa` | `blocks × game_efficiency` — approximate value of defensive blocks |
| `total_gpa` | `total_offensive_gpa + total_defensive_gpa` |
