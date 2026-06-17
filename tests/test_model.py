"""Testes para os modulos de modelo Dixon-Coles e Poisson."""
import math

import numpy as np
import pandas as pd
import pytest

from src.model.dixon_coles import _prepare_training_data
from src.model.matchup import classify_style, apply_style_adjustment
from src.model.poisson import get_score_distribution, resumir_probabilidades


def _make_match(team="Brazil", opp="France", venue="neutral",
                gs=1, gc=0, peso=1.0) -> dict:
    return {
        "team": team, "opponent": opp, "venue": venue,
        "goals_scored": gs, "goals_conceded": gc,
        "peso_final": peso, "date": "2024-06-01",
    }


class TestPrepareTrainingData:
    def test_neutral_deduplica(self):
        rows = [
            _make_match("Brazil", "France", "neutral", gs=1, gc=0),
            _make_match("France", "Brazil", "neutral", gs=0, gc=1),
        ]
        df = pd.DataFrame(rows)
        result = _prepare_training_data(df)
        assert len(result) == 1

    def test_home_away_deduplica(self):
        rows = [
            _make_match("Brazil", "France", "home", gs=2, gc=1),
            _make_match("France", "Brazil", "away", gs=1, gc=2),
        ]
        df = pd.DataFrame(rows)
        result = _prepare_training_data(df)
        assert len(result) == 1

    def test_partidas_distintas_mantidas(self):
        rows = [
            _make_match("Brazil", "France", "neutral", gs=1, gc=0),
            _make_match("Brazil", "Germany", "neutral", gs=2, gc=1),
        ]
        df = pd.DataFrame(rows)
        result = _prepare_training_data(df)
        assert len(result) == 2

    def test_coluna_neutral_marcada_corretamente(self):
        rows = [
            _make_match("Brazil", "France", "neutral"),
            _make_match("Argentina", "Uruguay", "home"),
        ]
        df = pd.DataFrame(rows)
        result = _prepare_training_data(df)
        neutral_vals = result["neutral"].tolist()
        assert 1 in neutral_vals
        assert 0 in neutral_vals


class TestClassifyStyle:
    def _make_index(self, dominio, volume, solidez=5.0) -> pd.Series:
        return pd.Series({
            "dominio_territorial": dominio,
            "volume_ataque": volume,
            "solidez_defensiva": solidez,
        })

    def test_high_press_alto_dominio_e_volume(self):
        assert classify_style(self._make_index(7, 7)) == "high_press"

    def test_possession_alto_dominio_baixo_volume(self):
        assert classify_style(self._make_index(7, 4)) == "possession"

    def test_direct_baixo_dominio_alto_volume(self):
        assert classify_style(self._make_index(4, 7)) == "direct"

    def test_low_block_baixo_dominio_baixo_volume(self):
        assert classify_style(self._make_index(3, 3)) == "low_block"

    def test_none_retorna_direct(self):
        assert classify_style(None) == "direct"

    def test_nan_dominio_usa_solidez(self):
        idx = pd.Series({"dominio_territorial": float("nan"),
                         "volume_ataque": float("nan"),
                         "solidez_defensiva": 8.0})
        assert classify_style(idx) == "low_block"


class TestApplyStyleAdjustment:
    def test_sem_ajuste_para_estilos_iguais(self):
        la, lb = apply_style_adjustment(1.5, 1.2, "direct", "direct")
        assert la == pytest.approx(1.5)
        assert lb == pytest.approx(1.2)

    def test_high_press_vs_low_block_aumenta_lambda_a(self):
        la, lb = apply_style_adjustment(1.0, 1.0, "high_press", "low_block")
        assert la > 1.0  # high_press atacando low_block: mais gols esperados
        assert lb < 1.0

    def test_simetria_invertida(self):
        la_hp, lb_lb = apply_style_adjustment(1.0, 1.0, "high_press", "low_block")
        la_lb, lb_hp = apply_style_adjustment(1.0, 1.0, "low_block", "high_press")
        assert la_hp == pytest.approx(lb_hp)
        assert lb_lb == pytest.approx(la_lb)


class TestGetScoreDistribution:
    def _make_grid(self):
        """Cria um grid de probabilidades fake para testes."""
        import penaltyblog
        # Matrix 5x5 com probabilidades uniformes
        matrix = np.full((10, 10), 0.01)
        matrix[1, 1] = 0.20  # 1-1 mais provavel
        return penaltyblog.models.FootballProbabilityGrid(
            goal_matrix=matrix,
            home_goal_expectation=1.2,
            away_goal_expectation=1.1,
            normalize=True,
        )

    def test_retorna_dataframe(self):
        grid = self._make_grid()
        df = get_score_distribution(grid, max_goals=3)
        assert isinstance(df, pd.DataFrame)
        assert "goals_a" in df.columns
        assert "goals_b" in df.columns
        assert "probability" in df.columns

    def test_ordenado_por_probabilidade_decrescente(self):
        grid = self._make_grid()
        df = get_score_distribution(grid)
        probs = df["probability"].tolist()
        assert probs == sorted(probs, reverse=True)

    def test_primeiro_placar_e_mais_provavel(self):
        grid = self._make_grid()
        df = get_score_distribution(grid)
        assert df.iloc[0]["goals_a"] == 1
        assert df.iloc[0]["goals_b"] == 1


class TestResumirProbabilidades:
    def _make_grid(self):
        import penaltyblog
        matrix = np.full((10, 10), 0.005)
        matrix[1, 0] = 0.25  # 1-0 mais provavel
        return penaltyblog.models.FootballProbabilityGrid(
            goal_matrix=matrix,
            home_goal_expectation=1.3,
            away_goal_expectation=0.9,
            normalize=True,
        )

    def test_probabilidades_somam_1(self):
        grid = self._make_grid()
        r = resumir_probabilidades(grid, "TeamA", "TeamB")
        total = r["prob_vitoria_TeamA"] + r["prob_empate"] + r["prob_vitoria_TeamB"]
        assert total == pytest.approx(1.0, abs=0.01)

    def test_top5_tem_5_entradas(self):
        grid = self._make_grid()
        r = resumir_probabilidades(grid)
        assert len(r["top5_placares"]) == 5

    def test_xg_presente(self):
        grid = self._make_grid()
        r = resumir_probabilidades(grid, "TeamA", "TeamB")
        assert "xg_a" in r
        assert "xg_b" in r
