"""
Simulacao de placares via Poisson usando o grid do Dixon-Coles.

O penaltyblog ja aplica a correcao Dixon-Coles ao grid de probabilidades.
Extraimos os placares mais provaveis e as probabilidades de resultado diretamente
do grid sem necessidade de simulacao Monte Carlo adicional.
"""
import logging
from typing import Optional

import numpy as np
import pandas as pd
import penaltyblog

from src.utils.config import N_SIMULACOES

logger = logging.getLogger(__name__)


def get_score_distribution(
    grid: penaltyblog.models.FootballProbabilityGrid,
    max_goals: int = 8,
) -> pd.DataFrame:
    """
    Extrai a distribuicao de placares do grid Dixon-Coles.

    Args:
        grid: Objeto FootballProbabilityGrid retornado por model.predict().
        max_goals: Numero maximo de gols por time a considerar no output.

    Returns:
        DataFrame com colunas [goals_a, goals_b, probability] ordenado
        por probabilidade decrescente.
    """
    g = grid.grid[:max_goals + 1, :max_goals + 1]
    rows = []
    for i in range(g.shape[0]):
        for j in range(g.shape[1]):
            rows.append({
                "goals_a": i,
                "goals_b": j,
                "probability": float(g[i, j]),
            })
    df = pd.DataFrame(rows).sort_values("probability", ascending=False).reset_index(drop=True)
    return df


def resumir_probabilidades(
    grid: penaltyblog.models.FootballProbabilityGrid,
    team_a: str = "team_a",
    team_b: str = "team_b",
) -> dict:
    """
    Resume as probabilidades de resultado e os placares mais provaveis.

    Args:
        grid: Objeto FootballProbabilityGrid do penaltyblog.
        team_a: Nome do primeiro time (para labels no output).
        team_b: Nome do segundo time (para labels no output).

    Returns:
        Dicionario com:
        - prob_vitoria_a, prob_empate, prob_vitoria_b
        - xg_a, xg_b (expectativas do modelo)
        - placar_mais_provavel: dict com goals_a, goals_b, probability
        - top5_placares: lista dos 5 placares mais provaveis
    """
    # Probabilidades de resultado (1X2) em campo neutro
    # penaltyblog calcula a partir do grid
    prob_home_win = float(grid.home_win)
    prob_draw = float(grid.draw)
    prob_away_win = float(grid.away_win)

    dist = get_score_distribution(grid)
    top5 = dist.head(5).to_dict(orient="records")
    mais_provavel = top5[0] if top5 else {}

    return {
        f"prob_vitoria_{team_a}": round(prob_home_win, 4),
        "prob_empate": round(prob_draw, 4),
        f"prob_vitoria_{team_b}": round(prob_away_win, 4),
        "xg_a": round(float(grid.home_goal_expectation), 3),
        "xg_b": round(float(grid.away_goal_expectation), 3),
        "placar_mais_provavel": {
            "placar": f"{mais_provavel.get('goals_a', 0)}-{mais_provavel.get('goals_b', 0)}",
            "probabilidade": round(float(mais_provavel.get("probability", 0)), 4),
        },
        "top5_placares": [
            {
                "placar": f"{r['goals_a']}-{r['goals_b']}",
                "probabilidade": round(float(r["probability"]), 4),
            }
            for r in top5
        ],
    }
