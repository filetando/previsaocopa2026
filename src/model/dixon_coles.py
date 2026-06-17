"""
Modelo Dixon-Coles para estimativa de taxas de gols esperados (xG).

Treina com penaltyblog usando peso_final por partida. A Copa 2026 e
disputada em campo neutro, entao neutral_venue=True para todas as predicoes.
"""
import logging
import pickle
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd
import penaltyblog

from src.utils.config import DATA_PROCESSED, ROOT_DIR

logger = logging.getLogger(__name__)

MODEL_PATH = ROOT_DIR / "outputs" / "model" / "dixon_coles_v1.pkl"


def _prepare_training_data(df: pd.DataFrame) -> pd.DataFrame:
    """
    Prepara os dados para o treinamento do Dixon-Coles.

    O modelo precisa de uma linha por partida com team_home e team_away.
    Como o dataset tem duas linhas por partida (uma por time), consolidamos
    em uma linha usando o criterio de venue:
    - "home" = equipe e team_home
    - "away" = equipe e team_away
    - "neutral" = usamos a perspectiva do time com menor nome (ordenacao alfabetica)
      para garantir unicidade sem perder dados.

    Args:
        df: DataFrame no schema universal com colunas team, opponent, venue,
            goals_scored, goals_conceded, peso_final.

    Returns:
        DataFrame com colunas goals_home, goals_away, team_home, team_away,
        weights, neutral_venue para uso no penaltyblog.
    """
    rows: list[dict] = []
    seen: set[str] = set()

    for _, row in df.iterrows():
        team = str(row["team"])
        opp = str(row["opponent"])
        venue = str(row["venue"])

        # Cria ID unico para cada par de times por data (evita duplicatas)
        date_str = str(row.get("date", ""))
        pair_key = f"{min(team, opp)}_{max(team, opp)}_{date_str}"
        if pair_key in seen:
            continue
        seen.add(pair_key)

        if venue == "home":
            home, away = team, opp
            g_home = int(row["goals_scored"])
            g_away = int(row["goals_conceded"])
            neutral = 0
        elif venue == "away":
            home, away = opp, team
            g_home = int(row["goals_conceded"])
            g_away = int(row["goals_scored"])
            neutral = 0
        else:
            # Neutral: ordem alfabetica para consistencia
            if team <= opp:
                home, away = team, opp
                g_home = int(row["goals_scored"])
                g_away = int(row["goals_conceded"])
            else:
                home, away = opp, team
                g_home = int(row["goals_conceded"])
                g_away = int(row["goals_scored"])
            neutral = 1

        rows.append({
            "team_home": home,
            "team_away": away,
            "goals_home": g_home,
            "goals_away": g_away,
            "weight": float(row.get("peso_final", 1.0)),
            "neutral": neutral,
        })

    return pd.DataFrame(rows)


def train(df_features: pd.DataFrame) -> penaltyblog.models.DixonColesGoalModel:
    """
    Treina o modelo Dixon-Coles com os dados de feature engineering.

    Args:
        df_features: DataFrame com peso_final calculado (saida de build_feature_matrix).

    Returns:
        Modelo treinado.
    """
    logger.info("Preparando dados de treino...")
    train_df = _prepare_training_data(df_features)
    logger.info("Partidas de treino: %d (sem duplicatas)", len(train_df))

    import numpy as np
    # .values.copy() necessario: penaltyblog nao aceita arrays read-only do pandas
    model = penaltyblog.models.DixonColesGoalModel(
        goals_home=train_df["goals_home"].values.copy(),
        goals_away=train_df["goals_away"].values.copy(),
        teams_home=train_df["team_home"].values.copy(),
        teams_away=train_df["team_away"].values.copy(),
        weights=train_df["weight"].values.copy(),
        neutral_venue=train_df["neutral"].values.copy(),
    )
    model.fit()

    params = model.get_params()
    n_teams = sum(1 for k in params if k.startswith("attack_"))
    logger.info(
        "Modelo treinado: %d times com parametros de ataque/defesa",
        n_teams,
    )
    return model


def save_model(model: penaltyblog.models.DixonColesGoalModel) -> None:
    """
    Salva o modelo treinado em disco.

    Args:
        model: Modelo Dixon-Coles treinado.
    """
    MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(MODEL_PATH, "wb") as f:
        pickle.dump(model, f)
    logger.info("Modelo salvo: %s", MODEL_PATH)


def load_model() -> penaltyblog.models.DixonColesGoalModel:
    """
    Carrega o modelo Dixon-Coles do disco.

    Returns:
        Modelo treinado.

    Raises:
        FileNotFoundError: Se o modelo nao foi treinado ainda.
    """
    if not MODEL_PATH.exists():
        raise FileNotFoundError(
            f"Modelo nao encontrado: {MODEL_PATH}. Execute dixon_coles.py primeiro."
        )
    with open(MODEL_PATH, "rb") as f:
        return pickle.load(f)


def prever_xg(
    model: penaltyblog.models.DixonColesGoalModel,
    team_a: str,
    team_b: str,
) -> tuple[float, float]:
    """
    Prevê as taxas de gols esperados (lambda) para um confronto em campo neutro.

    Args:
        model: Modelo Dixon-Coles treinado.
        team_a: Nome do primeiro time.
        team_b: Nome do segundo time.

    Returns:
        Tupla (lambda_a, lambda_b) com os xG esperados por time.
    """
    grid = model.predict(team_a, team_b, neutral_venue=True)
    lambda_a = float(grid.home_goal_expectation)
    lambda_b = float(grid.away_goal_expectation)
    logger.info(
        "xG previsto: %s=%.3f | %s=%.3f",
        team_a, lambda_a, team_b, lambda_b,
    )
    return lambda_a, lambda_b


if __name__ == "__main__":
    import logging as _logging
    _logging.basicConfig(level=_logging.INFO, format="%(levelname)s %(message)s")

    from src.engineering.features import build_feature_matrix

    df = pd.read_parquet(DATA_PROCESSED / "matches" / "partidas_padronizadas_v1.parquet")
    df_features = build_feature_matrix(df)

    model = train(df_features)
    save_model(model)

    # Teste rapido
    for matchup in [("Brazil", "France"), ("Argentina", "Spain"), ("Morocco", "Japan")]:
        la, lb = prever_xg(model, *matchup)
        print(f"{matchup[0]} vs {matchup[1]}: {la:.3f} x {lb:.3f}")
