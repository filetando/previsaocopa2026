"""Testes para o modulo de indices taticos."""
import math

import numpy as np
import pandas as pd
import pytest

from src.model.team_indexer import _normalize_to_index, build_indices, DIMENSIONS


class TestNormalizeToIndex:
    def test_maior_valor_recebe_10(self):
        s = pd.Series([1.0, 2.0, 3.0])
        result = _normalize_to_index(s, higher_is_better=True)
        assert result.max() == pytest.approx(10.0)

    def test_menor_valor_recebe_baixo(self):
        s = pd.Series([1.0, 2.0, 3.0])
        result = _normalize_to_index(s, higher_is_better=True)
        assert result.min() < 5.0

    def test_lower_is_better_inverte(self):
        s = pd.Series([1.0, 2.0, 3.0])
        result_asc = _normalize_to_index(s, higher_is_better=True)
        result_desc = _normalize_to_index(s, higher_is_better=False)
        # Menor valor deve ter indice alto quando lower_is_better
        assert result_desc.iloc[0] > result_desc.iloc[2]

    def test_nan_permanece_nan(self):
        s = pd.Series([1.0, float("nan"), 3.0])
        result = _normalize_to_index(s, higher_is_better=True)
        assert math.isnan(result.iloc[1])

    def test_resultado_entre_0_e_10(self):
        s = pd.Series([100.0, 200.0, 50.0, 300.0])
        result = _normalize_to_index(s)
        assert result.dropna().min() >= 0.0
        assert result.dropna().max() <= 10.0


class TestBuildIndices:
    def _make_profiles(self) -> pd.DataFrame:
        return pd.DataFrame({
            "gols_marcados_adj": [2.0, 1.0, 1.5],
            "gols_sofridos_adj": [0.5, 1.5, 1.0],
            "xg_for_adj": [1.8, float("nan"), 1.2],
            "xg_against_adj": [0.6, float("nan"), 1.0],
            "razao_dominio": [0.6, float("nan"), 0.5],
            "precisao_finalizacao": [0.4, float("nan"), 0.3],
            "chutes_for_adj": [12.0, float("nan"), 9.0],
        }, index=["TeamA", "TeamB", "TeamC"])

    def test_colunas_de_dimensoes_criadas(self):
        df = build_indices(self._make_profiles())
        for dim in DIMENSIONS:
            assert dim["name"] in df.columns

    def test_indice_geral_criado(self):
        df = build_indices(self._make_profiles())
        assert "indice_geral" in df.columns

    def test_time_sem_xg_recebe_nan_em_xg(self):
        df = build_indices(self._make_profiles())
        assert math.isnan(df.loc["TeamB", "qualidade_finalizacao"])

    def test_indice_geral_ignora_nan(self):
        df = build_indices(self._make_profiles())
        # TeamB tem NaN em xg mas deve ter indice_geral valido (baseado nos outros)
        assert not math.isnan(df.loc["TeamB", "indice_geral"])

    def test_melhor_ataque_tem_forca_maior(self):
        df = build_indices(self._make_profiles())
        # TeamA tem gols_adj=2.0 (maior), deve ter forca_ofensiva maior que TeamC (1.5) e TeamB (1.0)
        assert df.loc["TeamA", "forca_ofensiva"] > df.loc["TeamC", "forca_ofensiva"]
        assert df.loc["TeamC", "forca_ofensiva"] > df.loc["TeamB", "forca_ofensiva"]

    def test_melhor_defesa_tem_solidez_maior(self):
        df = build_indices(self._make_profiles())
        # TeamA tem gols_sofridos_adj=0.5 (menor), deve ter solidez_defensiva maior
        assert df.loc["TeamA", "solidez_defensiva"] > df.loc["TeamC", "solidez_defensiva"]
        assert df.loc["TeamC", "solidez_defensiva"] > df.loc["TeamB", "solidez_defensiva"]
