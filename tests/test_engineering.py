"""Testes para os modulos de feature engineering."""
import math
from datetime import datetime

import numpy as np
import pandas as pd
import pytest

from src.engineering.weights import (
    calcular_peso_competicao,
    calcular_peso_temporal,
    calcular_peso_final,
)
from src.engineering.features import (
    ponderar_por_elo,
    calcular_precisao_chutes,
    calcular_razao_dominio,
    add_weights,
    add_elo_adjusted_metrics,
)
from src.engineering.profiles import _weighted_mean, build_team_profile


class TestPesoCompetição:
    def test_continental(self):
        assert calcular_peso_competicao("continental") == pytest.approx(1.2)

    def test_qualifier(self):
        assert calcular_peso_competicao("qualifier") == pytest.approx(1.0)

    def test_friendly(self):
        assert calcular_peso_competicao("friendly") == pytest.approx(0.8)

    def test_desconhecido_retorna_1(self):
        assert calcular_peso_competicao("xpto") == pytest.approx(1.0)


class TestPesoTemporal:
    def test_partida_hoje_retorna_1(self):
        hoje = datetime(2026, 6, 11)
        assert calcular_peso_temporal(hoje, hoje) == pytest.approx(1.0)

    def test_partida_futura_retorna_1(self):
        ref = datetime(2026, 6, 11)
        futuro = datetime(2027, 1, 1)
        assert calcular_peso_temporal(futuro, ref) == pytest.approx(1.0)

    def test_meia_vida_730_dias(self):
        ref = datetime(2026, 6, 11)
        passado = datetime(2024, 6, 11)  # exatamente 730 dias antes
        peso = calcular_peso_temporal(passado, ref, meia_vida_dias=730)
        assert peso == pytest.approx(0.5, rel=1e-3)

    def test_partida_antiga_peso_baixo(self):
        ref = datetime(2026, 6, 11)
        antiga = datetime(2020, 6, 11)  # ~6 anos
        peso = calcular_peso_temporal(antiga, ref)
        assert peso < 0.15


class TestPesoFinal:
    def test_produto_simples(self):
        assert calcular_peso_final(1.2, 0.5) == pytest.approx(0.6)

    def test_friendly_antiga(self):
        peso = calcular_peso_final(0.8, 0.3)
        assert peso == pytest.approx(0.24)


class TestPonderarElo:
    def test_adversario_na_media_sem_ajuste(self):
        assert ponderar_por_elo(2.0, 1500.0, elo_media=1500.0) == pytest.approx(2.0)

    def test_adversario_forte_reduz_metrica_ofensiva(self):
        # Marcar contra adversario forte (1800) vale mais do ponto de vista
        # do ataque sendo avaliado: fator = 1500/1800 < 1
        resultado = ponderar_por_elo(2.0, 1800.0, elo_media=1500.0)
        assert resultado < 2.0

    def test_adversario_fraco_reduz_valor(self):
        resultado = ponderar_por_elo(2.0, 1200.0, elo_media=1500.0)
        assert resultado > 2.0  # fator = 1500/1200 > 1

    def test_elo_zero_sem_ajuste(self):
        assert ponderar_por_elo(2.0, 0.0) == pytest.approx(2.0)


class TestPrecisaoChutes:
    def test_calculo_correto(self):
        assert calcular_precisao_chutes(4, 10) == pytest.approx(0.4)

    def test_zero_chutes_retorna_none(self):
        assert calcular_precisao_chutes(0, 0) is None

    def test_none_retorna_none(self):
        assert calcular_precisao_chutes(None, 10) is None


class TestRazaoDominio:
    def test_equilibrio(self):
        assert calcular_razao_dominio(5, 5) == pytest.approx(0.5)

    def test_dominio_total(self):
        assert calcular_razao_dominio(10, 0) == pytest.approx(1.0)

    def test_sem_chutes_retorna_none(self):
        assert calcular_razao_dominio(0, 0) is None

    def test_none_retorna_none(self):
        assert calcular_razao_dominio(None, 5) is None


class TestAddWeights:
    def _make_df(self) -> pd.DataFrame:
        return pd.DataFrame([{
            "date": pd.Timestamp("2024-06-01"),
            "competition": "continental",
            "team": "Brazil",
            "elo_opponent": 1500.0,
        }])

    def test_colunas_criadas(self):
        df = add_weights(self._make_df())
        assert "peso_competicao" in df.columns
        assert "peso_temporal" in df.columns
        assert "peso_final" in df.columns

    def test_peso_continental(self):
        df = add_weights(self._make_df())
        assert df.iloc[0]["peso_competicao"] == pytest.approx(1.2)


class TestWeightedMean:
    def test_media_ponderada_simples(self):
        v = pd.Series([1.0, 3.0])
        w = pd.Series([1.0, 1.0])
        assert _weighted_mean(v, w) == pytest.approx(2.0)

    def test_ignora_nan(self):
        v = pd.Series([1.0, float("nan"), 3.0])
        w = pd.Series([1.0, 1.0, 1.0])
        assert _weighted_mean(v, w) == pytest.approx(2.0)

    def test_todos_nan_retorna_nan(self):
        v = pd.Series([float("nan")])
        w = pd.Series([1.0])
        assert math.isnan(_weighted_mean(v, w))
