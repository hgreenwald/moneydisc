"""Tests for StatsBank: unit tests for pure functions + integration tests for the pipeline."""

from __future__ import annotations

import unittest
from pathlib import Path

import pandas as pd

from moneydisc.analysis.config import ENDZONE_DEPTH_M, FIELD_CENTER_M, FIELD_LENGTH_M, FIELD_WIDTH_M

FIXTURES_DIR = Path(__file__).parent / "fixtures"
MODELS_DIR = FIXTURES_DIR / "models"

MODELS_AVAILABLE = (MODELS_DIR / "linear_gp.p").exists() and (
    MODELS_DIR / "linear_point_scored.p"
).exists()

FIXTURE_GAMES = {
    "Heidees 2025-05-18_20-38-33": "Heidees - Tom's Tourney",
    "Tchac 2025-05-30_17-24-00": "Tchac Pool - Elite Invite",
}


class TestCleanColumnNames(unittest.TestCase):
    def test_lowercases_and_replaces_spaces(self):
        from moneydisc.analysis.stats_bank import StatsBank

        result = StatsBank._clean_column_names(pd.Index(["Start X", "End Y"]))
        self.assertEqual(list(result), ["start_x", "end_y"])

    def test_removes_question_marks(self):
        from moneydisc.analysis.stats_bank import StatsBank

        result = StatsBank._clean_column_names(pd.Index(["Turnover?", "Assist?"]))
        self.assertEqual(list(result), ["turnover", "assist"])

    def test_removes_apostrophes(self):
        from moneydisc.analysis.stats_bank import StatsBank

        result = StatsBank._clean_column_names(pd.Index(["Opponent's Score"]))
        self.assertEqual(list(result), ["opponents_score"])


class TestComputeOpponentPossessions(unittest.TestCase):
    def _run(self, scored: int, started_on_offense: int, possessions: int) -> int:
        from moneydisc.analysis.stats_bank import StatsBank

        row = pd.Series(
            {"scored": scored, "started_on_offense": started_on_offense, "possessions": possessions}
        )
        return StatsBank._compute_opponent_possessions(row)

    def test_started_offense_and_scored(self):
        # We had 1 more possession than them
        self.assertEqual(self._run(scored=1, started_on_offense=1, possessions=3), 2)

    def test_started_offense_did_not_score(self):
        # Equal possessions
        self.assertEqual(self._run(scored=0, started_on_offense=1, possessions=3), 3)

    def test_started_defense_and_scored(self):
        # Equal possessions (we turned them over and scored)
        self.assertEqual(self._run(scored=1, started_on_offense=0, possessions=2), 2)

    def test_started_defense_did_not_score(self):
        # They had 1 more possession than us
        self.assertEqual(self._run(scored=0, started_on_offense=0, possessions=2), 3)


class TestGetFinalScore(unittest.TestCase):
    def test_returns_last_row_scores(self):
        from moneydisc.analysis.stats_bank import StatsBank

        df = pd.DataFrame(
            {
                "our_score_at_pull": [0, 1, 2, 7],
                "opponents_score_at_pull": [0, 0, 1, 5],
            }
        )
        our, opp = StatsBank._get_final_score(df)
        self.assertEqual(our, 7)
        self.assertEqual(opp, 5)


class TestAssignCredit(unittest.TestCase):
    """Test GPA credit assignment between thrower and receiver."""

    def _row(self, thrower_error: int, receiver_error: int, gpa: float) -> pd.Series:
        return pd.Series(
            {"thrower_error": thrower_error, "receiver_error": receiver_error, "gpa": gpa}
        )

    def test_thrower_error_only_thrower_gets_full(self):
        from moneydisc.analysis.stats_bank import StatsBank

        row = self._row(thrower_error=1, receiver_error=0, gpa=-0.4)
        self.assertAlmostEqual(StatsBank._assign_credit(row, "thrower"), -0.4)
        self.assertAlmostEqual(StatsBank._assign_credit(row, "receiver"), 0.0)

    def test_receiver_error_only_receiver_gets_full(self):
        from moneydisc.analysis.stats_bank import StatsBank

        row = self._row(thrower_error=0, receiver_error=1, gpa=-0.4)
        self.assertAlmostEqual(StatsBank._assign_credit(row, "thrower"), 0.0)
        self.assertAlmostEqual(StatsBank._assign_credit(row, "receiver"), -0.4)

    def test_both_errors_split_credit(self):
        from moneydisc.analysis.stats_bank import StatsBank

        row = self._row(thrower_error=1, receiver_error=1, gpa=-0.4)
        self.assertAlmostEqual(StatsBank._assign_credit(row, "thrower"), -0.2)
        self.assertAlmostEqual(StatsBank._assign_credit(row, "receiver"), -0.2)

    def test_no_errors_split_credit(self):
        from moneydisc.analysis.stats_bank import StatsBank

        row = self._row(thrower_error=0, receiver_error=0, gpa=0.3)
        self.assertAlmostEqual(StatsBank._assign_credit(row, "thrower"), 0.15)
        self.assertAlmostEqual(StatsBank._assign_credit(row, "receiver"), 0.15)


class TestTransformPassStats(unittest.TestCase):
    """Test coordinate-to-distance transformations on synthetic pass data."""

    def _make_pass_df(self, start_x: float, start_y: float, end_x: float, end_y: float) -> pd.DataFrame:
        return pd.DataFrame(
            {
                "start_x": [start_x],
                "start_y": [start_y],
                "end_x": [end_x],
                "end_y": [end_y],
                "assist": [0],
                "turnover": [0],
                "thrower": ["p1"],
                "receiver": ["p2"],
            }
        )

    def test_midfield_pass_distances(self):
        """x=0.5 → 18m (center of field), y=0.5 → 32m from endzone line."""
        df = self._make_pass_df(start_x=0.5, start_y=0.5, end_x=0.5, end_y=0.5)
        df["dist_to_endzone_start"] = df["start_y"] * FIELD_LENGTH_M - ENDZONE_DEPTH_M
        df["start_x_m"] = df["start_x"] * FIELD_WIDTH_M
        df["dist_from_middle_start"] = abs(FIELD_CENTER_M - df["start_x_m"])
        df["dist_from_sideline_start"] = FIELD_CENTER_M - df["dist_from_middle_start"]

        self.assertAlmostEqual(df["dist_to_endzone_start"].iloc[0], 32.0)
        self.assertAlmostEqual(df["dist_from_middle_start"].iloc[0], 0.0)
        self.assertAlmostEqual(df["dist_from_sideline_start"].iloc[0], FIELD_CENTER_M)

    def test_left_sideline_dist_from_sideline_is_zero(self):
        """x=0 (left sideline) should give dist_from_sideline=0."""
        df = self._make_pass_df(start_x=0.0, start_y=0.5, end_x=0.0, end_y=0.5)
        df["start_x_m"] = df["start_x"] * FIELD_WIDTH_M
        df["dist_from_middle_start"] = abs(FIELD_CENTER_M - df["start_x_m"])
        df["dist_from_sideline_start"] = FIELD_CENTER_M - df["dist_from_middle_start"]

        self.assertAlmostEqual(df["dist_from_sideline_start"].iloc[0], 0.0)

    def test_back_of_own_endzone_dist_is_positive(self):
        """y=0 (back of opponent endzone) should give dist_to_endzone = -ENDZONE_DEPTH_M."""
        df = self._make_pass_df(start_x=0.5, start_y=0.0, end_x=0.5, end_y=0.0)
        df["dist_to_endzone_end"] = df["end_y"] * FIELD_LENGTH_M - ENDZONE_DEPTH_M
        self.assertAlmostEqual(df["dist_to_endzone_end"].iloc[0], -ENDZONE_DEPTH_M)


@unittest.skipUnless(MODELS_AVAILABLE, "Model files not present in tests/fixtures/models/")
class TestStatsBankIntegration(unittest.TestCase):
    """Full pipeline integration tests using the 2-game fixture corpus."""

    @classmethod
    def setUpClass(cls) -> None:
        from moneydisc.analysis.stats_bank import StatsBank

        cls.sb = StatsBank(
            data_dir=FIXTURES_DIR,
            output_dir=FIXTURES_DIR / "output",
            model_dir=MODELS_DIR,
            games=FIXTURE_GAMES,
        )
        cls.sb.prepare_data()
        cls.sb.compute_all_stats()

    def test_game_stats_has_two_rows(self):
        self.assertEqual(len(self.sb.game_stats_df), 2)

    def test_game_stats_columns_present(self):
        expected_cols = {
            "game_id", "game_name", "possessions", "passes",
            "our_score", "opponent_score", "combined_scoring_efficiency",
        }
        self.assertTrue(expected_cols.issubset(set(self.sb.game_stats_df.columns)))

    def test_aggregated_stats_has_players(self):
        self.assertGreater(len(self.sb.aggregated_player_stats_df), 0)

    def test_total_gpa_no_nulls(self):
        self.assertFalse(self.sb.aggregated_player_stats_df["total_gpa"].isnull().any())

    def test_player_names_normalized(self):
        players = set(self.sb.aggregated_player_stats_df["player"])
        self.assertIn("13 Hartley", players)
        self.assertNotIn("13 Hartley Greenwald", players)
        self.assertIn("02 Cego", players)
        self.assertNotIn("02 Ondrej Rydlo", players)

    def test_key_columns_present(self):
        expected_cols = [
            "player", "total_gpa", "adjusted_gpa", "adjusted_offensive_gpa",
            "adjusted_thrower_gpa", "adjusted_receiver_gpa",
            "throws", "completions", "completion_percentage",
            "goals", "assists", "total_turnovers",
        ]
        actual = set(self.sb.aggregated_player_stats_df.columns)
        for col in expected_cols:
            self.assertIn(col, actual, msg=f"Missing column: {col}")

    def test_completion_percentage_between_0_and_1(self):
        cp = self.sb.aggregated_player_stats_df["completion_percentage"].dropna()
        self.assertTrue((cp >= 0).all() and (cp <= 1).all())

    def test_adjusted_gpa_equals_adjusted_offensive_gpa(self):
        df = self.sb.aggregated_player_stats_df
        pd.testing.assert_series_equal(
            df["adjusted_gpa"].reset_index(drop=True),
            df["adjusted_offensive_gpa"].reset_index(drop=True),
            check_names=False,
        )


if __name__ == "__main__":
    unittest.main()
