"""Testes para o modulo standardizer."""
import pandas as pd
import pytest

from src.collection.standardizer import (
    SCHEMA_COLS,
    _fill_elo,
    _filter_window,
    _remove_duplicates,
)
from src.utils.config import REFERENCE_DATE_STR


def _make_row(**kwargs) -> dict:
    base = {
        "match_id": "test_001",
        "team": "Brazil",
        "opponent": "Argentina",
        "date": pd.Timestamp("2024-06-01"),
        "competition": "continental",
        "venue": "neutral",
        "goals_scored": 1,
        "goals_conceded": 0,
        "shots_for": 10,
        "shots_against": 8,
        "shots_on_target_for": 5,
        "shots_on_target_against": 3,
        "corners_for": 4,
        "corners_against": 2,
        "xg_for": 1.2,
        "xg_against": 0.8,
        "elo_team": None,
        "elo_opponent": None,
        "source": "statsbomb",
        "data_quality": "high",
    }
    base.update(kwargs)
    return base


class TestRemoveDuplicates:
    def test_keeps_high_over_low(self):
        row_high = _make_row(match_id="m1", data_quality="high", source="statsbomb")
        row_low = _make_row(match_id="m1", data_quality="low", source="eloratings")
        df = pd.DataFrame([row_high, row_low])
        result = _remove_duplicates(df)
        assert len(result) == 1
        assert result.iloc[0]["data_quality"] == "high"

    def test_keeps_medium_over_low(self):
        row_med = _make_row(match_id="m1", data_quality="medium", source="sofascore")
        row_low = _make_row(match_id="m1", data_quality="low", source="eloratings")
        df = pd.DataFrame([row_low, row_med])
        result = _remove_duplicates(df)
        assert len(result) == 1
        assert result.iloc[0]["data_quality"] == "medium"

    def test_unique_matches_kept(self):
        row1 = _make_row(match_id="m1")
        row2 = _make_row(match_id="m2", team="France", opponent="Germany")
        df = pd.DataFrame([row1, row2])
        result = _remove_duplicates(df)
        assert len(result) == 2


class TestFillElo:
    def _make_elo_hist(self) -> pd.DataFrame:
        return pd.DataFrame([
            {"team": "Brazil", "date": pd.Timestamp("2024-01-01"), "elo": 2100.0},
            {"team": "Argentina", "date": pd.Timestamp("2024-01-01"), "elo": 2080.0},
        ])

    def test_fills_elo_team_and_opponent(self):
        row = _make_row(elo_team=None, elo_opponent=None)
        df = pd.DataFrame([row])
        hist = self._make_elo_hist()
        result = _fill_elo(df, hist)
        assert result.iloc[0]["elo_team"] == pytest.approx(2100.0)
        assert result.iloc[0]["elo_opponent"] == pytest.approx(2080.0)

    def test_does_not_overwrite_existing_elo(self):
        row = _make_row(elo_team=1900.0, elo_opponent=1850.0)
        df = pd.DataFrame([row])
        hist = self._make_elo_hist()
        result = _fill_elo(df, hist)
        assert result.iloc[0]["elo_team"] == pytest.approx(1900.0)

    def test_unknown_team_uses_global_mean(self):
        row = _make_row(team="Unknown FC", opponent="Brazil", elo_team=None, elo_opponent=None)
        df = pd.DataFrame([row])
        hist = self._make_elo_hist()
        result = _fill_elo(df, hist)
        from src.utils.config import ELO_MEDIA_GLOBAL
        assert result.iloc[0]["elo_team"] == pytest.approx(ELO_MEDIA_GLOBAL)


class TestFilterWindow:
    def test_statsbomb_kept_outside_window(self):
        # World Cup 2022 e fora da janela de 3 anos mas deve ser mantido
        row = _make_row(date=pd.Timestamp("2022-07-10"), source="statsbomb")
        df = pd.DataFrame([row])
        df["date"] = pd.to_datetime(df["date"])
        result = _filter_window(df)
        assert len(result) == 1

    def test_eloratings_outside_window_removed(self):
        row = _make_row(date=pd.Timestamp("2020-01-01"), source="eloratings")
        df = pd.DataFrame([row])
        df["date"] = pd.to_datetime(df["date"])
        result = _filter_window(df)
        assert len(result) == 0

    def test_eloratings_inside_window_kept(self):
        row = _make_row(date=pd.Timestamp("2024-06-01"), source="eloratings")
        df = pd.DataFrame([row])
        df["date"] = pd.to_datetime(df["date"])
        result = _filter_window(df)
        assert len(result) == 1
