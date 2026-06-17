"""Testes para o modulo de validacao."""
import math

import pandas as pd
import pytest

from src.model.validation import brier_score, _get_result_label, compute_metrics


class TestBrierScore:
    def test_previsao_perfeita_retorna_zero(self):
        probs = [(1.0, 0.0, 0.0)]
        results = ["win_a"]
        assert brier_score(probs, results) == pytest.approx(0.0)

    def test_previsao_uniforme_retorna_um_terco(self):
        probs = [(1/3, 1/3, 1/3)]
        results = ["win_a"]
        bs = brier_score(probs, results)
        # Brier = ((1/3-1)^2 + (1/3-0)^2 + (1/3-0)^2) / 3 = (4/9 + 1/9 + 1/9) / 3 = 2/9
        assert bs == pytest.approx(2 / 9, abs=1e-4)

    def test_previsao_errada_retorna_alto(self):
        probs = [(0.9, 0.05, 0.05)]
        results = ["win_b"]
        bs = brier_score(probs, results)
        assert bs > 0.25

    def test_media_de_varias_partidas(self):
        probs = [(1.0, 0.0, 0.0), (0.0, 1.0, 0.0)]
        results = ["win_a", "draw"]
        bs = brier_score(probs, results)
        assert bs == pytest.approx(0.0)


class TestGetResultLabel:
    def test_vitoria_a(self):
        assert _get_result_label(2, 1) == "win_a"

    def test_empate(self):
        assert _get_result_label(1, 1) == "draw"

    def test_vitoria_b(self):
        assert _get_result_label(0, 3) == "win_b"

    def test_zero_zero_e_empate(self):
        assert _get_result_label(0, 0) == "draw"


class TestComputeMetrics:
    def _make_results(self) -> pd.DataFrame:
        return pd.DataFrame([
            {
                "team_a": "Brazil", "team_b": "France",
                "goals_a": 1, "goals_b": 0,
                "lambda_a": 1.4, "lambda_b": 1.1,
                "prob_win_a": 0.45, "prob_draw": 0.28, "prob_win_b": 0.27,
                "result": "win_a",
            },
            {
                "team_a": "Spain", "team_b": "Germany",
                "goals_a": 2, "goals_b": 1,
                "lambda_a": 1.5, "lambda_b": 1.3,
                "prob_win_a": 0.42, "prob_draw": 0.30, "prob_win_b": 0.28,
                "result": "win_a",
            },
        ])

    def test_retorna_brier_score(self):
        metrics = compute_metrics(self._make_results())
        assert "brier_score" in metrics
        assert 0 <= metrics["brier_score"] <= 1

    def test_retorna_mae_xg(self):
        metrics = compute_metrics(self._make_results())
        assert "mae_xg" in metrics
        assert metrics["mae_xg"] >= 0

    def test_retorna_accuracy(self):
        metrics = compute_metrics(self._make_results())
        assert "accuracy_result" in metrics
        assert 0 <= metrics["accuracy_result"] <= 1

    def test_n_partidas_correto(self):
        metrics = compute_metrics(self._make_results())
        assert metrics["n_partidas"] == 2
