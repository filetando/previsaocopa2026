"""Testes unitarios para src/collection/statsbomb_collector.py."""
import pandas as pd
import pytest

from src.collection.statsbomb_collector import (
    _extrair_metricas_eventos,
    collect_competition,
)


def _make_eventos(
    team: str = "Brazil",
    opponent: str = "Argentina",
    n_shots_team: int = 5,
    n_shots_opp: int = 3,
    xg_team: float = 1.2,
    xg_opp: float = 0.6,
    n_corners_team: int = 4,
    n_corners_opp: int = 2,
    include_penalty: bool = False,
) -> pd.DataFrame:
    """Gera DataFrame de eventos StatsBomb simplificado para testes."""
    rows = []

    for i in range(n_shots_team):
        rows.append({
            "type": "Shot",
            "team": team,
            "shot_statsbomb_xg": xg_team / n_shots_team,
            "shot_outcome": "Goal" if i == 0 else "Saved",
            "shot_type": "Penalty" if (include_penalty and i == 0) else "Open Play",
        })

    for i in range(n_shots_opp):
        rows.append({
            "type": "Shot",
            "team": opponent,
            "shot_statsbomb_xg": xg_opp / n_shots_opp,
            "shot_outcome": "Goal" if i == 0 else "Off T",
            "shot_type": "Open Play",
        })

    for _ in range(n_corners_team):
        rows.append({"type": "Pass", "team": team, "pass_type": "Corner"})

    for _ in range(n_corners_opp):
        rows.append({"type": "Pass", "team": opponent, "pass_type": "Corner"})

    rows.append({"type": "Pass", "team": team, "pass_type": "Throw-in"})

    return pd.DataFrame(rows)


def test_extrair_metricas_shots():
    eventos = _make_eventos(n_shots_team=5, n_shots_opp=3)
    metricas = _extrair_metricas_eventos(eventos, "Brazil")

    assert metricas["shots_for"] == 5
    assert metricas["shots_against"] == 3


def test_extrair_metricas_xg():
    eventos = _make_eventos(xg_team=1.2, xg_opp=0.6, n_shots_team=3, n_shots_opp=3)
    metricas = _extrair_metricas_eventos(eventos, "Brazil")

    assert metricas["xg_for"] == pytest.approx(1.2, abs=1e-6)
    assert metricas["xg_against"] == pytest.approx(0.6, abs=1e-6)


def test_extrair_metricas_exclui_penalty_do_xg():
    eventos = _make_eventos(
        xg_team=1.5, n_shots_team=3, include_penalty=True
    )
    metricas = _extrair_metricas_eventos(eventos, "Brazil")

    # xG do penalty (1.5/3 = 0.5) deve ser excluido
    assert metricas["xg_for"] == pytest.approx(1.0, abs=1e-6)


def test_extrair_metricas_corners():
    eventos = _make_eventos(n_corners_team=4, n_corners_opp=2)
    metricas = _extrair_metricas_eventos(eventos, "Brazil")

    assert metricas["corners_for"] == 4
    assert metricas["corners_against"] == 2


def test_extrair_metricas_shots_on_target():
    eventos = _make_eventos(n_shots_team=5, n_shots_opp=3)
    metricas = _extrair_metricas_eventos(eventos, "Brazil")

    # Fixture: primeiro chute = Goal, demais = Saved (team) ou Off T (opp)
    assert metricas["shots_on_target_for"] == 5   # Goal + 4x Saved
    assert metricas["shots_on_target_against"] == 1  # apenas o Goal


def test_extrair_metricas_eventos_vazio():
    metricas = _extrair_metricas_eventos(pd.DataFrame(), "Brazil")

    assert metricas["shots_for"] == 0
    assert metricas["xg_for"] is None
    assert metricas["corners_for"] == 0


def test_collect_competition_invalida():
    with pytest.raises(ValueError, match="desconhecida"):
        collect_competition("competicao_inexistente")
