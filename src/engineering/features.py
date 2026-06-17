"""Features derivadas e ponderacao por Elo do adversario."""
import logging
from typing import Optional

import numpy as np
import pandas as pd

from src.utils.config import ELO_MEDIA_GLOBAL, REFERENCE_DATE_STR
from src.engineering.weights import (
    calcular_peso_competicao,
    calcular_peso_temporal,
    calcular_peso_final,
)

logger = logging.getLogger(__name__)


def ponderar_por_elo(
    metrica: float,
    elo_adversario: float,
    elo_media: float = ELO_MEDIA_GLOBAL,
) -> float:
    """
    Ajusta uma metrica pelo nivel do adversario usando o Elo dele.

    Adversarios mais fortes (Elo alto) tornam as metricas ofensivas mais valiosas
    e as defensivas mais impressionantes. O fator e linear centrado em 1.0.

    fator = elo_media / elo_adversario

    Exemplos:
        - vs adversario elo=1500 (media): fator=1.0 (sem ajuste)
        - vs adversario elo=1800 (elite): fator=0.83 (gol conta menos na ofensa)
        - vs adversario elo=1200 (fraco): fator=1.25 (gol conta menos na defesa)

    Args:
        metrica: Valor bruto da metrica (ex: gols, xG, chutes).
        elo_adversario: Elo do adversario na data da partida.
        elo_media: Elo medio global de referencia (padrao: 1500).

    Returns:
        Metrica ajustada pelo nivel do adversario.
    """
    if elo_adversario <= 0:
        logger.warning("Elo do adversario invalido: %.1f — sem ajuste", elo_adversario)
        return metrica
    fator = elo_media / elo_adversario
    return metrica * fator


def calcular_precisao_chutes(
    shots_on_target: Optional[float],
    shots_total: Optional[float],
) -> Optional[float]:
    """
    Calcula a precisao de finalizacao (chutes no alvo / chutes totais).

    Args:
        shots_on_target: Numero de chutes no alvo.
        shots_total: Numero total de chutes.

    Returns:
        Precisao entre 0 e 1, ou None se dados insuficientes.
    """
    if shots_on_target is None or shots_total is None:
        return None
    if shots_total == 0:
        return None
    return float(shots_on_target) / float(shots_total)


def calcular_razao_dominio(
    shots_for: Optional[float],
    shots_against: Optional[float],
) -> Optional[float]:
    """
    Calcula a razao de dominio territorial (shots_for / total shots).

    Args:
        shots_for: Chutes a favor.
        shots_against: Chutes contra.

    Returns:
        Razao entre 0 e 1 (0.5 = equilibrio), ou None se dados insuficientes.
    """
    if shots_for is None or shots_against is None:
        return None
    total = float(shots_for) + float(shots_against)
    if total == 0:
        return None
    return float(shots_for) / total


def add_weights(df: pd.DataFrame) -> pd.DataFrame:
    """
    Adiciona colunas de peso (competicao, temporal e final) ao DataFrame de partidas.

    Args:
        df: DataFrame no schema universal com colunas date e competition.

    Returns:
        DataFrame com colunas adicionais: peso_competicao, peso_temporal, peso_final.
    """
    ref_date = pd.Timestamp(REFERENCE_DATE_STR)

    df = df.copy()
    df["date"] = pd.to_datetime(df["date"])

    df["peso_competicao"] = df["competition"].apply(calcular_peso_competicao)
    df["peso_temporal"] = df["date"].apply(
        lambda d: calcular_peso_temporal(d.to_pydatetime(), ref_date.to_pydatetime())
    )
    df["peso_final"] = df["peso_competicao"] * df["peso_temporal"]

    return df


def add_elo_adjusted_metrics(df: pd.DataFrame) -> pd.DataFrame:
    """
    Adiciona metricas ofensivas e defensivas ajustadas pelo Elo do adversario.

    Para metricas ofensivas: multiplica pelo fator elo_media/elo_adversario
    (marcar contra adversario forte vale mais).

    Para metricas defensivas: multiplica pelo fator elo_adversario/elo_media
    (sofrer gol de adversario forte e menos penalizado).

    Args:
        df: DataFrame com colunas goals_scored, goals_conceded, shots_for,
            shots_against, xg_for, xg_against, elo_opponent.

    Returns:
        DataFrame com colunas _adj adicionadas para cada metrica.
    """
    df = df.copy()
    elo_opp = df["elo_opponent"].fillna(ELO_MEDIA_GLOBAL)

    # Fator ofensivo: maior Elo do adversario = metrica ofensiva mais valiosa
    fator_ofensivo = ELO_MEDIA_GLOBAL / elo_opp.clip(lower=1)
    # Fator defensivo: maior Elo do adversario = sofrer menos prejudicial
    fator_defensivo = elo_opp / ELO_MEDIA_GLOBAL

    for col in ["goals_scored", "shots_for", "xg_for"]:
        if col in df.columns:
            df[f"{col}_adj"] = pd.to_numeric(df[col], errors="coerce") * fator_ofensivo

    for col in ["goals_conceded", "shots_against", "xg_against"]:
        if col in df.columns:
            df[f"{col}_adj"] = pd.to_numeric(df[col], errors="coerce") * fator_defensivo

    # Precisao e dominio (sem ajuste por Elo — sao ratios intrinsecamente normalizados)
    df["precisao_chutes"] = df.apply(
        lambda r: calcular_precisao_chutes(r.get("shots_on_target_for"), r.get("shots_for")),
        axis=1,
    )
    df["razao_dominio"] = df.apply(
        lambda r: calcular_razao_dominio(r.get("shots_for"), r.get("shots_against")),
        axis=1,
    )

    return df


def build_feature_matrix(df: pd.DataFrame) -> pd.DataFrame:
    """
    Constroi a matriz de features ponderadas a partir do DataFrame padronizado.

    Pipeline completo:
    1. Adiciona pesos (competicao, temporal, final)
    2. Adiciona metricas ajustadas por Elo
    3. Retorna DataFrame enriquecido pronto para agregacao por time

    Args:
        df: DataFrame no schema universal (partidas_padronizadas_v1.parquet).

    Returns:
        DataFrame com todas as features adicionadas.
    """
    logger.info("Construindo matriz de features: %d partidas", len(df))
    df = add_weights(df)
    df = add_elo_adjusted_metrics(df)
    logger.info("Matriz de features concluida: %d colunas", len(df.columns))
    return df
