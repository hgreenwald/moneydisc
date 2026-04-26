"""StatsBank: compute and aggregate Wall City ultimate frisbee statistics."""

from __future__ import annotations

import pickle
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import statsmodels.api as sm

from moneydisc.analysis.config import (
    ENDZONE_DEPTH_M,
    FIELD_CENTER_M,
    FIELD_LENGTH_M,
    FIELD_WIDTH_M,
    GAMES,
    NAME_MAPPINGS,
    POINT_MODEL_FILE,
    POSSESSION_MODEL_FILE,
)
from moneydisc.visualization.field import draw_field


class StatsBank:
    def __init__(
        self,
        data_dir: str | Path = "data/raw",
        output_dir: str | Path = "data/processed",
        model_dir: str | Path = "models",
        games: dict[str, str] | None = None,
        name_mappings: dict[str, str] | None = None,
    ) -> None:
        self.data_dir = Path(data_dir)
        self.output_dir = Path(output_dir)
        self.model_dir = Path(model_dir)
        self.games = games if games is not None else GAMES
        self.name_mappings = name_mappings if name_mappings is not None else NAME_MAPPINGS

        self._load_possession_model()
        self._load_point_model()

        self.aggregated_player_stats_df: pd.DataFrame = pd.DataFrame()
        self.game_stats_df: pd.DataFrame = pd.DataFrame()
        self.game_player_stats_df: pd.DataFrame = pd.DataFrame()
        self.point_stats_df: pd.DataFrame = pd.DataFrame()

        self.player_stats_dfs: dict[str, pd.DataFrame] = {}
        self.passes_dfs: dict[str, pd.DataFrame] = {}
        self.possessions_dfs: dict[str, pd.DataFrame] = {}
        self.points_dfs: dict[str, pd.DataFrame] = {}
        self.player_points_dfs: dict[str, pd.DataFrame] = {}
        self.blocks_dfs: dict[str, pd.DataFrame] = {}

    def load_data(self) -> None:
        """Load CSVs for each game into per-type dicts of DataFrames."""
        self.player_stats_dfs = {}
        self.passes_dfs = {}
        self.possessions_dfs = {}
        self.points_dfs = {}
        self.player_points_dfs = {}
        self.blocks_dfs = {}

        for game_id, game_name in self.games.items():
            self.player_stats_dfs[game_id] = pd.read_csv(
                self.data_dir / f"Player Stats vs. {game_id}.csv"
            )
            self.passes_dfs[game_id] = pd.read_csv(
                self.data_dir / f"Passes vs. {game_id}.csv"
            )
            self.possessions_dfs[game_id] = pd.read_csv(
                self.data_dir / f"Possessions vs. {game_id}.csv"
            )
            self.points_dfs[game_id] = pd.read_csv(
                self.data_dir / f"Points vs. {game_id}.csv"
            )
            try:
                self.blocks_dfs[game_id] = pd.read_csv(
                    self.data_dir / f"Defensive Blocks vs. {game_id}.csv"
                )
            except FileNotFoundError:
                self.blocks_dfs[game_id] = pd.DataFrame()
                print(f"No defensive blocks data for {game_id}")

            self.passes_dfs[game_id]["game"] = game_name
            self.possessions_dfs[game_id]["game"] = game_name
            self.points_dfs[game_id]["game"] = game_name
            self.blocks_dfs[game_id]["game"] = game_name

        assert len(self.player_stats_dfs) == len(self.games)
        assert len(self.passes_dfs) == len(self.games)
        assert len(self.possessions_dfs) == len(self.games)
        assert len(self.points_dfs) == len(self.games)

    def prepare_data(self) -> None:
        self.load_data()
        self._rename_columns()
        self._fix_player_names()
        self._transform_pass_stats()

    def _rename_columns(self) -> None:
        """Standardize column names across all per-game DataFrames."""
        coord_rename = {
            "Start X (0 -> 1 = left sideline -> right sideline)": "start_x",
            "Start Y (0 -> 1 = back of opponent endzone -> back of own endzone)": "start_y",
            "End X (0 -> 1 = left sideline -> right sideline)": "end_x",
            "End Y (0 -> 1 = back of opponent endzone -> back of own endzone)": "end_y",
        }
        for df in self.passes_dfs.values():
            df.rename(coord_rename, axis=1, inplace=True)
        for df in self.possessions_dfs.values():
            df.rename(coord_rename, axis=1, inplace=True)

        for game_id in self.games:
            self.passes_dfs[game_id].columns = self._clean_column_names(
                self.passes_dfs[game_id].columns
            )
            self.possessions_dfs[game_id].columns = self._clean_column_names(
                self.possessions_dfs[game_id].columns
            )
            self.points_dfs[game_id].columns = self._clean_column_names(
                self.points_dfs[game_id].columns
            )
            self.player_stats_dfs[game_id].columns = self._clean_column_names(
                self.player_stats_dfs[game_id].columns
            )
            self.blocks_dfs[game_id].columns = self._clean_column_names(
                self.blocks_dfs[game_id].columns
            )

    @staticmethod
    def _clean_column_names(columns: pd.Index) -> pd.Index:
        return columns.str.lower().str.replace(" ", "_").str.replace("?", "").str.replace("'", "")

    def _fix_player_names(self) -> None:
        """Normalize player name inconsistencies using NAME_MAPPINGS."""
        for df in self.passes_dfs.values():
            df["thrower"] = df["thrower"].replace(self.name_mappings)
            df["receiver"] = df["receiver"].replace(self.name_mappings)

        for df in self.player_stats_dfs.values():
            df["player"] = df["player"].replace(self.name_mappings)

        for df in self.blocks_dfs.values():
            if "player" in df.columns:
                df["player"] = df["player"].replace(self.name_mappings)

    def _transform_pass_stats(self) -> None:
        """Convert normalized field coordinates to distance metrics.

        Statto Y-axis: 0 = back of opponent endzone, 1 = back of own endzone.
        Converting to dist_to_endzone: y*100 gives meters from far end; subtracting
        18 (endzone depth) gives meters from the endzone line into the central zone.
        Statto X-axis: 0 = left sideline, 1 = right sideline → x*36 gives meters.
        dist_from_middle: distance from the center of the field (18m mark).
        dist_from_sideline: distance from the nearest sideline (18 - dist_from_middle).
        """
        for df in self.passes_dfs.values():
            df["dist_to_endzone_end"] = df["end_y"] * FIELD_LENGTH_M - ENDZONE_DEPTH_M
            df["dist_to_endzone_start"] = df["start_y"] * FIELD_LENGTH_M - ENDZONE_DEPTH_M
            df["dist_to_endzone_end_capped"] = df["dist_to_endzone_end"].clip(lower=0)
            df["start_x_m"] = df["start_x"] * FIELD_WIDTH_M
            df["end_x_m"] = df["end_x"] * FIELD_WIDTH_M
            df["dist_from_middle_start"] = abs(FIELD_CENTER_M - df["start_x_m"])
            df["dist_from_middle_end"] = abs(FIELD_CENTER_M - df["end_x_m"])
            df["dist_from_sideline_start"] = FIELD_CENTER_M - df["dist_from_middle_start"]
            df["dist_from_sideline_end"] = FIELD_CENTER_M - df["dist_from_middle_end"]
            df["dist_from_middle_diff"] = df["dist_from_middle_start"] - df["dist_from_middle_end"]
            df["dist_to_endzone_diff"] = (
                df["dist_to_endzone_start"] - df["dist_to_endzone_end_capped"]
            )

            assert (df.loc[df["assist"] == 1, "dist_to_endzone_end"] < 0).all()
            assert (df["dist_to_endzone_start"] >= 0).all()
            assert (df["dist_from_sideline_start"] <= FIELD_CENTER_M).all()
            assert (df["dist_from_sideline_start"] >= 0).all()

        for df in self.possessions_dfs.values():
            df["dist_to_endzone_start"] = df["start_y"] * FIELD_LENGTH_M - ENDZONE_DEPTH_M
            df["start_x_m"] = df["start_x"] * FIELD_WIDTH_M
            df["dist_from_middle_start"] = abs(FIELD_CENTER_M - df["start_x_m"])
            df["dist_from_sideline_start"] = FIELD_CENTER_M - df["dist_from_middle_start"]

    def _transform_points_played(self) -> None:
        """Explode the comma-separated points_played list into one row per player-point."""
        for game_id, df in self.player_stats_dfs.items():
            df["points_played"] = df["points_played"].astype(str)
            transformed_df = (
                df.assign(points_played=df["points_played"].str.split(","))
                .explode("points_played")[["player", "points_played"]]
            )
            transformed_df["points_played"] = pd.to_numeric(
                transformed_df["points_played"], errors="coerce"
            ).astype("Int64")
            transformed_df.dropna(subset=["points_played"], inplace=True)
            self.player_points_dfs[game_id] = transformed_df

    def compute_all_stats(self) -> None:
        self._transform_points_played()
        self._compute_game_stats()
        self._compute_scoring_probabilities()
        self._compute_gpa()
        self._compute_player_game_stats()
        self.aggregated_player_stats_df = self._compute_player_stats(
            self.aggregated_player_stats_df
        )
        self.game_player_stats_df = self._compute_player_stats(self.game_player_stats_df)

    def _compute_scoring_probabilities(self) -> None:
        """Assign start/end scoring probability to each pass using the point model."""
        for df in self.passes_dfs.values():
            df["scoring_prob_start"] = self.point_model.predict(
                sm.add_constant(df[["dist_to_endzone_start", "dist_from_sideline_start"]])
            )
            df["scoring_prob_end"] = self.point_model.predict(
                sm.add_constant(df[["dist_to_endzone_end_capped", "dist_from_sideline_end"]])
            )
            df["scoring_prob_end"] = df.apply(
                lambda x: 1 if x["assist"] == 1 else x["scoring_prob_end"], axis=1
            )
            df["scoring_prob_end"] = df.apply(
                lambda x: 0 if x["turnover"] == 1 else x["scoring_prob_end"], axis=1
            )
            df["opp_dist_to_endzone_end_capped"] = 70 - df["dist_to_endzone_end_capped"]
            df["scoring_prob_end_opp"] = self.point_model.predict(
                sm.add_constant(
                    df[["opp_dist_to_endzone_end_capped", "dist_from_sideline_end"]]
                )
            )

        for df in self.possessions_dfs.values():
            df["scoring_prob_start"] = self.possession_model.predict(
                sm.add_constant(df[["dist_to_endzone_start", "dist_from_sideline_start"]])
            )

    def _compute_gpa(self) -> None:
        """Compute Goal Probability Added (GPA) for each pass, split thrower/receiver."""
        for game_id, df in self.passes_dfs.items():
            df["game_efficiency"] = self.get_game_efficiency(game_id)
            df["gpa"] = df["scoring_prob_end"] - df["scoring_prob_start"]
            df["gpa"] = df.apply(self._make_turnover_correction, axis=1)
            df["thrower_gpa"] = df.apply(
                lambda x: self._assign_credit(x, "thrower"), axis=1
            )
            df["receiver_gpa"] = df.apply(
                lambda x: self._assign_credit(x, "receiver"), axis=1
            )

    def _compute_max_gpa_all(self) -> pd.DataFrame:
        """For each player, compute the maximum GPA achievable given their points played.

        Divides by 2 because credit for each scoring probability is split between
        the thrower and receiver — a single player cannot capture all of it alone.
        """
        max_gpas_df = pd.DataFrame()
        for game_id, df in self.possessions_dfs.items():
            player_possessions_df = pd.merge(
                self.player_points_dfs[game_id],
                df,
                left_on="points_played",
                right_on="point",
                how="left",
            )
            result = (
                player_possessions_df.groupby("player")["scoring_prob_start"].sum() / 2
            ).reset_index()
            result["game"] = self.games[game_id]
            max_gpas_df = pd.concat([max_gpas_df, result], ignore_index=True)
        max_gpas_df.columns = ["player", "game", "max_gpa"]
        return max_gpas_df

    def _compute_max_gpa_game(self, game_id: str) -> pd.DataFrame:
        """Compute per-player max GPA for a single game."""
        possession_df = self.possessions_dfs[game_id]
        player_possessions_df = pd.merge(
            self.player_points_dfs[game_id],
            possession_df,
            left_on="points_played",
            right_on="point",
            how="left",
        )
        result = (
            player_possessions_df.groupby("player")["scoring_prob_start"].sum() / 2
        ).reset_index()
        result.columns = ["player", "max_gpa"]
        return result

    def _compute_player_game_stats(self) -> None:
        """Compute per-game player stats and aggregate across all games."""
        self.game_player_stats_df = pd.DataFrame()
        for game_id, df in self.passes_dfs.items():
            offensive_game_stats = self._aggregate_offensive_player_stats(
                df, game=self.games[game_id]
            )
            defensive_game_stats = self._aggregate_defensive_player_stats(game_id=game_id)
            if defensive_game_stats is not None:
                game_stats = offensive_game_stats.merge(
                    defensive_game_stats, on="player", how="left"
                )
            else:
                game_stats = offensive_game_stats

            self.game_player_stats_df = pd.concat([self.game_player_stats_df, game_stats])

        self.aggregated_player_stats_df = self._aggregate_player_stats_all_games(
            self.game_player_stats_df
        )

    def _compute_defensive_blocks(self, game_id: str) -> pd.DataFrame:
        blocks_df = self.blocks_dfs[game_id].groupby("player").count()
        blocks_df.rename(columns={"created": "blocks"}, inplace=True)
        all_players = self.player_stats_dfs[game_id]["player"].values
        blocks_df = blocks_df.reindex(all_players, fill_value=0)
        blocks_df.reset_index(inplace=True)
        return blocks_df[["player", "blocks"]]

    def _compute_defensive_gpa(self, blocks_df: pd.DataFrame, game_id: str) -> pd.DataFrame:
        blocks_df["game_efficiency"] = self.get_game_efficiency(game_id)
        blocks_df["total_defensive_gpa"] = blocks_df["blocks"] * blocks_df["game_efficiency"]
        return blocks_df

    def _aggregate_defensive_player_stats(
        self, game_id: str
    ) -> pd.DataFrame | None:
        if len(self.blocks_dfs[game_id]) == 0:
            return None
        blocks_df = self._compute_defensive_blocks(game_id)
        blocks_df = self._compute_defensive_gpa(blocks_df, game_id)
        return blocks_df

    def _aggregate_offensive_player_stats(
        self, passes_df: pd.DataFrame, game: str | None = None
    ) -> pd.DataFrame:
        """Aggregate per-pass records into per-player offensive stats for one game."""
        passes_df["thrower_turnover_credit"] = passes_df.apply(
            lambda row: (
                0.5
                if (row["thrower_error"] == 1) and (row["receiver_error"] == 1)
                else 1
                if row["thrower_error"] == 1
                else 0
            )
            if row["turnover"] == 1
            else 0,
            axis=1,
        )
        passes_df["receiver_turnover_credit"] = passes_df.apply(
            lambda row: (
                0.5
                if (row["thrower_error"] == 1) and (row["receiver_error"] == 1)
                else 1
                if row["receiver_error"] == 1
                else 0
            )
            if row["turnover"] == 1
            else 0,
            axis=1,
        )

        stats_df = pd.DataFrame(index=self.get_players())

        completed_thrower_df = (
            passes_df.query("turnover==0")
            .groupby("thrower")
            .agg(
                {
                    "assist": "sum",
                    "secondary_assist": "sum",
                    "huck": "sum",
                    "swing": "sum",
                    "dump": "sum",
                    "dist_to_endzone_diff": "sum",
                    "dist_from_middle_diff": "sum",
                    "thrower": "count",
                    "thrower_gpa": "sum",
                }
            )
            .rename_axis("player")
            .rename(
                {
                    "dist_to_endzone_diff": "throwing_meters_gained",
                    "dist_from_middle_diff": "throwing_centering_meters_gained",
                    "assist": "assists",
                    "huck": "hucks_completed",
                    "secondary_assist": "secondary_assists",
                    "swing": "swings",
                    "dump": "dumps",
                    "thrower": "completions",
                    "thrower_gpa": "thrower_gpa_no_turns",
                },
                axis="columns",
            )
            .reset_index()
        )

        thrower_df = (
            passes_df.groupby("thrower")
            .agg(
                {
                    "thrower_turnover_credit": "sum",
                    "thrower_gpa": "sum",
                    "thrower": "count",
                    "huck": "sum",
                }
            )
            .rename_axis("player")
            .rename(
                {
                    "thrower_turnover_credit": "turnover_thrown",
                    "thrower": "throws",
                    "huck": "hucks_thrown",
                },
                axis="columns",
            )
            .reset_index()
        )

        thrower_df = pd.merge(thrower_df, completed_thrower_df, on="player", how="outer")
        thrower_df.fillna(0, inplace=True)

        completed_receiver_df = (
            passes_df.query("turnover==0")
            .groupby("receiver")
            .agg(
                {
                    "assist": "sum",
                    "huck": "sum",
                    "receiver": "count",
                    "dist_to_endzone_diff": "sum",
                    "dist_from_middle_diff": "sum",
                    "receiver_gpa": "sum",
                }
            )
            .rename_axis("player")
            .rename(
                {
                    "dist_to_endzone_diff": "receiving_meters_gained",
                    "dist_from_middle_diff": "receiving_centering_meters_gained",
                    "receiver": "catches",
                    "assist": "goals",
                    "huck": "hucks_received",
                    "receiver_gpa": "receiver_gpa_no_turns",
                },
                axis="columns",
            )
            .reset_index()
        )

        receiver_df = (
            passes_df.groupby("receiver")
            .agg({"receiver_turnover_credit": "sum", "receiver_gpa": "sum"})
            .rename_axis("player")
            .rename({"receiver_turnover_credit": "receiver_turnovers"}, axis="columns")
            .reset_index()
        )

        receiver_df = pd.merge(receiver_df, completed_receiver_df, on="player", how="outer")
        receiver_df.fillna(0, inplace=True)

        stats_df = pd.merge(
            stats_df, thrower_df, left_index=True, right_on="player", how="outer"
        )
        stats_df = pd.merge(
            stats_df,
            receiver_df,
            on="player",
            how="outer",
            suffixes=("_as_thrower", "_as_receiver"),
        )
        stats_df.fillna(0, inplace=True)

        stats_df["total_offensive_gpa"] = stats_df["thrower_gpa"] + stats_df["receiver_gpa"]
        stats_df["total_offensive_gpa_no_turns"] = (
            stats_df["thrower_gpa_no_turns"] + stats_df["receiver_gpa_no_turns"]
        )
        stats_df["total_turnovers"] = stats_df["turnover_thrown"] + stats_df["receiver_turnovers"]
        stats_df["touches"] = stats_df["throws"] + stats_df["goals"]
        stats_df["game"] = game

        game_id = {v: k for k, v in self.games.items()}[game]
        max_gpas_df = self._compute_max_gpa_game(game_id=game_id)
        stats_df = stats_df.merge(max_gpas_df, on="player", how="left")

        return stats_df

    def _aggregate_player_stats_all_games(self, df: pd.DataFrame) -> pd.DataFrame:
        result_df = df.groupby("player").sum().reset_index()
        result_df["games"] = df.groupby("player")["game"].nunique().values
        return result_df

    @staticmethod
    def _assign_credit(row: pd.Series, thrower_or_receiver: str) -> float:
        """Split GPA credit between thrower and receiver based on error attribution."""
        if thrower_or_receiver == "thrower":
            if (row["thrower_error"] == 1) and (row["receiver_error"] == 1):
                return row["gpa"] / 2
            elif row["thrower_error"] == 1:
                return row["gpa"]
            elif row["receiver_error"] == 1:
                return 0.0
            else:
                return row["gpa"] / 2
        else:  # receiver
            if (row["thrower_error"] == 1) and (row["receiver_error"] == 1):
                return row["gpa"] / 2
            elif row["receiver_error"] == 1:
                return row["gpa"]
            elif row["thrower_error"] == 1:
                return 0.0
            else:
                return row["gpa"] / 2

    def _load_possession_model(self) -> None:
        with open(self.model_dir / POSSESSION_MODEL_FILE, "rb") as f:
            self.possession_model = pickle.load(f)

    def _load_point_model(self) -> None:
        with open(self.model_dir / POINT_MODEL_FILE, "rb") as f:
            self.point_model = pickle.load(f)

    def _make_turnover_correction(self, row: pd.Series) -> float:
        """Adjust GPA for turnovers by accounting for the opponent's resulting field position.

        On a turnover, GPA = opponent's scoring probability from their new position (negated)
        minus our starting probability for that pass. This is more accurate than a flat
        game_efficiency penalty because it reflects where on the field the turnover happened.
        """
        if row["turnover"] == 1:
            return (1 - row["scoring_prob_end_opp"]) - row["scoring_prob_start"]
        return row["gpa"]

    def get_game_efficiency(self, game_id: str) -> float:
        """Return combined scoring efficiency for a game (used as turnover penalty baseline)."""
        return self.game_stats_df.loc[
            self.game_stats_df["game_id"] == game_id, "combined_scoring_efficiency"
        ].values[0]

    def get_players(self) -> list[str]:
        """Return deduplicated list of all players across all loaded games."""
        players: list[str] = []
        for df in self.player_stats_dfs.values():
            players += list(df["player"].unique())
        return list(set(players))

    def _compute_game_stats(self) -> None:
        """Compute game-level stats needed downstream for GPA and efficiency calculations."""
        for game_id, name in self.games.items():
            points_df = self.points_dfs[game_id]
            game_stats: dict = {}
            game_stats["game_id"] = game_id
            game_stats["game_name"] = name
            points_df["opponent_possessions"] = points_df.apply(
                self._compute_opponent_possessions, axis=1
            )
            game_stats["possessions"] = points_df["possessions"].sum()
            game_stats["opponent_possessions"] = points_df["opponent_possessions"].sum()
            game_stats["passes"] = points_df["passes"].sum()
            game_stats["points"] = points_df["point"].max() - 1.0
            game_stats["our_score"], game_stats["opponent_score"] = self._get_final_score(
                points_df
            )
            game_stats["our_scoring_efficiency"] = (
                game_stats["our_score"] / game_stats["possessions"]
            )
            game_stats["opponent_scoring_efficiency"] = (
                game_stats["opponent_score"] / game_stats["opponent_possessions"]
            )
            game_stats["combined_scoring_efficiency"] = (
                game_stats["our_score"] + game_stats["opponent_score"]
            ) / (game_stats["opponent_possessions"] + game_stats["possessions"])
            self.game_stats_df = pd.concat(
                [self.game_stats_df, pd.DataFrame([game_stats])], ignore_index=True
            )

    def _compute_player_stats(self, df: pd.DataFrame) -> pd.DataFrame:
        """Derive normalized and composite stats from the aggregated player DataFrame."""
        df["adjusted_offensive_gpa"] = df["total_offensive_gpa"] / df["max_gpa"]
        df["adjusted_thrower_gpa"] = df["thrower_gpa"] / df["max_gpa"]
        df["adjusted_receiver_gpa"] = df["receiver_gpa"] / df["max_gpa"]
        df["adjusted_gpa"] = df["adjusted_offensive_gpa"]  # alias for notebook compatibility
        df["total_gpa"] = df["total_offensive_gpa"] + df["total_defensive_gpa"]

        df["off. plus/minus"] = df["goals"] + df["assists"] - df["total_turnovers"]
        df["off. real plus/minus"] = (df["goals"] + df["assists"]) / 2 - df["total_turnovers"]

        # GPA decomposed into vertical (downfield) and horizontal (centering) components,
        # using possession model coefficients as the marginal value of each yard.
        vert_coef = self.possession_model.params.values[1]
        horz_coef = self.possession_model.params.values[2]
        df["gpa_vert_throwing"] = df["throwing_meters_gained"] * -vert_coef
        df["gpa_horz_throwing"] = df["throwing_centering_meters_gained"] * horz_coef
        df["gpa_total_throwing"] = df["gpa_vert_throwing"] + df["gpa_horz_throwing"]
        df["gpa_vert_receiving"] = df["receiving_meters_gained"] * -vert_coef
        df["gpa_horz_receiving"] = df["receiving_centering_meters_gained"] * -horz_coef
        df["gpa_total_receiving"] = df["gpa_vert_receiving"] + df["gpa_horz_receiving"]

        df["completion_percentage"] = df["completions"] / df["throws"]

        df = self.reorder_player_stat_columns(df)
        return df

    @staticmethod
    def _compute_opponent_possessions(point_row: pd.Series) -> int:
        """Derive opponent possession count from our recorded possession count.

        Logic: if we started on offense AND scored → we had one more possession than them.
               If we started on offense XOR scored → equal possessions.
               If neither → they had one more possession than us.
        """
        a = point_row["scored"] + point_row["started_on_offense"]
        return point_row["possessions"] - (a - 1)

    @staticmethod
    def _get_final_score(points_df: pd.DataFrame) -> tuple[int, int]:
        last_row = points_df.iloc[-1]
        return last_row["our_score_at_pull"], last_row["opponents_score_at_pull"]

    def plot_events(
        self,
        event: str,
        thrower: str | None = None,
        receiver: str | None = None,
        games: list[str] | None = None,
        draw_arrows: bool = False,
    ) -> None:
        """Plot field positions for a given pass event type.

        Args:
            event: One of 'passes', 'turnover', 'assist', 'huck'.
            thrower: If set, filter to passes thrown by this player.
            receiver: If set, filter to passes received by this player.
            games: Game IDs to include. Defaults to all loaded games.
            draw_arrows: If True, draw pass lines; otherwise draw start points only.
        """
        if games is None:
            games = list(self.games.keys())

        ax = draw_field()

        assert not (thrower and receiver), "Cannot specify both thrower and receiver"

        if thrower or receiver:
            player = thrower or receiver
            ax.set_title(f"{event}s for {player}")
        else:
            player = None
            ax.set_title(f"{event}s")

        for game_id in games:
            if game_id not in self.passes_dfs:
                print(f"Warning: game '{game_id}' not found in loaded passes data.")
                continue

            passes_df = self.passes_dfs[game_id].copy()
            events_df = passes_df if event == "passes" else passes_df[passes_df[event] == 1]

            if player is not None:
                col = "thrower" if thrower else "receiver"
                events_df = events_df[events_df[col] == player]
                if len(events_df) == 0:
                    print(f"No {event} found for '{player}' in game '{game_id}'.")
                    continue

            for _, row in events_df.iterrows():
                start_y = row["dist_to_endzone_start"]
                end_y = row["dist_to_endzone_end"]
                start_x = row["start_x_m"]
                end_x = row["end_x_m"]

                if draw_arrows:
                    ax.plot([start_x, end_x], [start_y, end_y], color="red", linewidth=1)
                    ax.plot(end_x, end_y, "x", color="red", markersize=6, markeredgewidth=1.5)
                ax.plot(start_x, start_y, "o", color="blue", markersize=4)

        plt.show()

    def plot_assists(self, **kwargs: object) -> None:
        self.plot_events("assist", **kwargs)

    def plot_turnovers(self, **kwargs: object) -> None:
        self.plot_events("turnover", **kwargs)

    def plot_passes(self, **kwargs: object) -> None:
        self.plot_events("passes", **kwargs)

    def plot_hucks(self, **kwargs: object) -> None:
        self.plot_events("huck", **kwargs)

    def reorder_player_stat_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        desired_order = [
            "player",
            "games",
            "total_gpa",
            "total_offensive_gpa",
            "total_defensive_gpa",
            "adjusted_gpa",
            "adjusted_offensive_gpa",
            "adjusted_thrower_gpa",
            "adjusted_receiver_gpa",
            "touches",
            "throws",
            "completions",
            "completion_percentage",
            "blocks",
            "goals",
            "assists",
            "total_turnovers",
            "off. plus/minus",
            "off. real plus/minus",
            "total_offensive_gpa_no_turns",
            "max_gpa",
            "turnover_thrown",
            "thrower_gpa",
            "hucks_thrown",
            "secondary_assists",
            "hucks_completed",
            "swings",
            "dumps",
            "throwing_meters_gained",
            "throwing_centering_meters_gained",
            "thrower_gpa_no_turns",
            "receiver_turnovers",
            "receiver_gpa",
            "hucks_received",
            "catches",
            "receiving_meters_gained",
            "receiving_centering_meters_gained",
            "receiver_gpa_no_turns",
            "gpa_vert_throwing",
            "gpa_horz_throwing",
            "gpa_total_throwing",
            "gpa_vert_receiving",
            "gpa_horz_receiving",
            "gpa_total_receiving",
            "game_efficiency",
            "game",
        ]
        ordered_columns = [col for col in desired_order if col in df.columns]
        return df[ordered_columns]

    def export_stats(self) -> None:
        """Write aggregated and per-game player stats CSVs to output_dir."""
        self.output_dir.mkdir(parents=True, exist_ok=True)
        for game_id in self.games:
            game_name = self.games[game_id]
            df = self.game_player_stats_df.query("game == @game_name")
            df.to_csv(self.output_dir / f"{game_name}_player_stats.csv", index=False)

        self.aggregated_player_stats_df.to_csv(
            self.output_dir / "aggregated_player_stats.csv", index=False
        )
        self.game_stats_df.to_csv(self.output_dir / "game_stats.csv", index=False)
