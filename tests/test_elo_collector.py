"""Testes unitarios para src/collection/elo_collector.py."""
from datetime import datetime

import pandas as pd
import pytest

from src.collection.elo_collector import (
    _detectar_codigo_time,
    _parse_historico,
    get_elo_on_date,
)


def _make_tsv_df(team_code: str = "BR") -> pd.DataFrame:
    """Gera DataFrame simulando TSV bruto do eloratings.net."""
    opp = "AR"
    rows = [
        # [year, month, day, t1, t2, g1, g2, comp, ?, elo_chg, elo_t1, elo_t2, ...]
        [2022, 1, 10, team_code, opp, "1", "0", "F", None, "10", "1800", "1750", "0", "0", "1", "2"],
        [2022, 6, 15, opp, team_code, "2", "1", "Q", None, "-5", "1755", "1795", "0", "0", "2", "1"],
        [2023, 3, 20, team_code, opp, "0", "0", "F", None, "3", "1798", "1752", "0", "0", "1", "2"],
    ]
    return pd.DataFrame(rows)


def test_detectar_codigo_time():
    df = _make_tsv_df("BR")
    assert _detectar_codigo_time(df) == "BR"


def test_parse_historico_datas_e_elo():
    df = _make_tsv_df("BR")
    historico = _parse_historico(df, "BR")

    assert len(historico) == 3
    assert list(historico.columns) == ["date", "elo"]
    # Linha 1: BR eh team1, elo_after_t1 = 1800
    assert historico.iloc[0]["elo"] == pytest.approx(1800.0)
    # Linha 2: BR eh team2, elo_after_t2 = 1795
    assert historico.iloc[1]["elo"] == pytest.approx(1795.0)
    # Linha 3: BR eh team1, elo_after_t1 = 1798
    assert historico.iloc[2]["elo"] == pytest.approx(1798.0)


def test_parse_historico_ordenado_por_data():
    df = _make_tsv_df("BR")
    historico = _parse_historico(df, "BR")

    datas = historico["date"].tolist()
    assert datas == sorted(datas)


def test_get_elo_on_date_exato():
    historico = pd.DataFrame({
        "team": ["Brazil", "Brazil", "Brazil"],
        "date": pd.to_datetime(["2022-01-10", "2022-06-15", "2023-03-20"]),
        "elo": [1800.0, 1795.0, 1798.0],
    })
    elo = get_elo_on_date(historico, "Brazil", datetime(2022, 6, 15))
    assert elo == pytest.approx(1795.0)


def test_get_elo_on_date_interpolacao_anterior():
    historico = pd.DataFrame({
        "team": ["Brazil", "Brazil"],
        "date": pd.to_datetime(["2022-01-10", "2023-03-20"]),
        "elo": [1800.0, 1798.0],
    })
    # Data entre os dois registros -> deve retornar o mais recente anterior
    elo = get_elo_on_date(historico, "Brazil", datetime(2022, 9, 1))
    assert elo == pytest.approx(1800.0)


def test_get_elo_on_date_time_desconhecido():
    historico = pd.DataFrame({
        "team": ["Brazil"],
        "date": pd.to_datetime(["2022-01-10"]),
        "elo": [1800.0],
    })
    # Time nao encontrado -> retorna ELO_MEDIA_GLOBAL (1500)
    elo = get_elo_on_date(historico, "Narnia", datetime(2023, 1, 1))
    assert elo == pytest.approx(1500.0)
