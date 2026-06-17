"""
Agrega metricas ponderadas por selecao para gerar perfis taticos.

Cada selecao recebe um perfil com:
- Ataque: gols, xG, chutes (ajustados por Elo e ponderados por competicao/tempo)
- Defesa: gols sofridos, xG concedido (idem)
- Estilo: precisao de finalizacao, razao de dominio, escanteios
"""
import logging
from typing import Optional

import numpy as np
import pandas as pd

from src.collection.teams import COPA_2026_TEAMS
from src.engineering.features import build_feature_matrix
from src.utils.config import DATA_PROCESSED, DATA_RAW

logger = logging.getLogger(__name__)


def _weighted_mean(
    values: pd.Series,
    weights: pd.Series,
) -> float:
    """
    Media ponderada ignorando NaNs.

    Args:
        values: Serie de valores numericos.
        weights: Serie de pesos correspondentes.

    Returns:
        Media ponderada ou NaN se nao houver dados validos.
    """
    mask = values.notna() & weights.notna() & (weights > 0)
    v = values[mask]
    w = weights[mask]
    if len(v) == 0:
        return float("nan")
    return float(np.average(v, weights=w))


def build_team_profile(team_df: pd.DataFrame) -> dict:
    """
    Calcula o perfil ponderado de uma selecao a partir de suas partidas.

    Args:
        team_df: DataFrame filtrado para um unico time, com colunas
                 de features (peso_final, *_adj, precisao_chutes, etc.).

    Returns:
        Dicionario com metricas por partida ponderadas.
    """
    w = team_df["peso_final"]
    n = len(team_df)

    def wm(col: str) -> float:
        if col not in team_df.columns:
            return float("nan")
        return _weighted_mean(team_df[col], w)

    # Metricas brutas por partida (medias ponderadas)
    goals_for_raw = wm("goals_scored")
    goals_against_raw = wm("goals_conceded")

    # Metricas ajustadas por Elo (principais inputs do modelo)
    goals_for_adj = wm("goals_scored_adj")
    goals_against_adj = wm("goals_conceded_adj")
    xg_for_adj = wm("xg_for_adj")
    xg_against_adj = wm("xg_against_adj")
    shots_for_adj = wm("shots_for_adj")
    shots_against_adj = wm("shots_against_adj")

    # Metricas de estilo (ratios, sem ajuste Elo)
    precisao = wm("precisao_chutes")
    dominio = wm("razao_dominio")
    corners_for = wm("corners_for")
    corners_against = wm("corners_against")

    # Cobertura de dados
    n_high = int((team_df["data_quality"] == "high").sum())
    n_xg = int(team_df["xg_for"].notna().sum())

    return {
        "n_partidas": n,
        "n_high_quality": n_high,
        "n_com_xg": n_xg,
        # Ataque
        "gols_marcados_raw": goals_for_raw,
        "gols_marcados_adj": goals_for_adj,
        "xg_for_adj": xg_for_adj,
        "chutes_for_adj": shots_for_adj,
        "precisao_finalizacao": precisao,
        # Defesa
        "gols_sofridos_raw": goals_against_raw,
        "gols_sofridos_adj": goals_against_adj,
        "xg_against_adj": xg_against_adj,
        "chutes_against_adj": shots_against_adj,
        # Estilo
        "razao_dominio": dominio,
        "escanteios_for": corners_for,
        "escanteios_against": corners_against,
    }


def build_all_profiles(df_features: pd.DataFrame) -> pd.DataFrame:
    """
    Gera perfis taticos ponderados para todas as 48 selecoes.

    Args:
        df_features: DataFrame com matriz de features (saida de build_feature_matrix).

    Returns:
        DataFrame com uma linha por selecao e todas as metricas de perfil.
    """
    profiles: list[dict] = []

    for team in COPA_2026_TEAMS:
        team_df = df_features[df_features["team"] == team]
        if team_df.empty:
            logger.warning("Sem dados para %s — perfil vazio", team)
            profiles.append({"team": team})
            continue

        profile = build_team_profile(team_df)
        profile["team"] = team
        profiles.append(profile)
        logger.info(
            "%s: %d partidas | gols_adj=%.2f | gols_sofridos_adj=%.2f",
            team,
            profile["n_partidas"],
            profile.get("gols_marcados_adj", float("nan")),
            profile.get("gols_sofridos_adj", float("nan")),
        )

    df = pd.DataFrame(profiles).set_index("team")
    logger.info("Perfis gerados: %d selecoes", len(df))
    return df


def save_profiles(df: pd.DataFrame) -> None:
    """
    Salva os perfis de selecoes em data/processed/team_profiles/.

    Args:
        df: DataFrame com perfis (index=team).
    """
    out_dir = DATA_PROCESSED / "team_profiles"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "perfis_v1.parquet"
    df.to_parquet(out_path)
    logger.info("Salvo: %s (%d times)", out_path, len(df))


def save_features(df: pd.DataFrame) -> None:
    """
    Salva a matriz de features em data/processed/features/.

    Args:
        df: DataFrame com features calculadas.
    """
    out_dir = DATA_PROCESSED / "features"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "features_v1.parquet"
    df.to_parquet(out_path, index=False)
    logger.info("Salvo: %s (%d linhas)", out_path, len(df))


if __name__ == "__main__":
    import logging as _logging
    _logging.basicConfig(level=_logging.INFO, format="%(levelname)s %(message)s")

    partidas = pd.read_parquet(DATA_PROCESSED / "matches" / "partidas_padronizadas_v1.parquet")
    df_features = build_feature_matrix(partidas)
    save_features(df_features)

    df_profiles = build_all_profiles(df_features)
    save_profiles(df_profiles)
