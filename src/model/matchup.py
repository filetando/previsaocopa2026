"""
Camada de ajuste de estilos para confrontos especificos.

Aplica multiplicadores ao xG base do Dixon-Coles com base no contraste
tatico entre os dois times (ex: alta pressao vs bloco baixo).
"""
import logging
from typing import Optional

import pandas as pd

logger = logging.getLogger(__name__)

# Multiplicadores por tipo de confronto (valor > 1 beneficia o atacante do par)
# Pares sao (estilo_time_a, estilo_time_b) -> (mult_a, mult_b)
STYLE_MULTIPLIERS: dict[tuple[str, str], tuple[float, float]] = {
    ("high_press", "low_block"): (1.08, 0.95),   # pressao alta vs bloco baixo
    ("low_block", "high_press"): (0.95, 1.08),
    ("high_press", "possession"): (1.02, 0.98),  # pressao vs posse
    ("possession", "high_press"): (0.98, 1.02),
    ("direct", "possession"): (1.04, 0.96),      # jogo direto vs posse
    ("possession", "direct"): (0.96, 1.04),
}


def classify_style(index_row: Optional[pd.Series]) -> str:
    """
    Classifica o estilo de jogo de uma selecao baseado em seus indices taticos.

    Args:
        index_row: Serie com indices 0-10 (saida do team_indexer).

    Returns:
        Estilo: "high_press" | "possession" | "direct" | "low_block"
    """
    if index_row is None or index_row.empty:
        return "direct"

    dominio = index_row.get("dominio_territorial", 5.0)
    volume = index_row.get("volume_ataque", 5.0)
    solidez = index_row.get("solidez_defensiva", 5.0)

    # Logica simples baseada em percentis (indices ja sao 0-10)
    if pd.isna(dominio) or pd.isna(volume):
        # Sem dados de dominio/volume (time sem StatsBomb): usa solidez
        if not pd.isna(solidez) and solidez >= 7:
            return "low_block"
        return "direct"

    if dominio >= 6 and volume >= 6:
        return "high_press"
    elif dominio >= 6:
        return "possession"
    elif volume >= 6:
        return "direct"
    else:
        return "low_block"


def apply_style_adjustment(
    lambda_a: float,
    lambda_b: float,
    style_a: str,
    style_b: str,
) -> tuple[float, float]:
    """
    Aplica multiplicador de estilo ao par de taxas de gols esperados.

    Args:
        lambda_a: Taxa de gols esperados do time A (Dixon-Coles).
        lambda_b: Taxa de gols esperados do time B (Dixon-Coles).
        style_a: Estilo classificado do time A.
        style_b: Estilo classificado do time B.

    Returns:
        Tupla (lambda_a_adj, lambda_b_adj) com ajuste de estilo aplicado.
    """
    mult_a, mult_b = STYLE_MULTIPLIERS.get((style_a, style_b), (1.0, 1.0))
    if mult_a != 1.0 or mult_b != 1.0:
        logger.info(
            "Ajuste de estilo: %s(%s) vs %s(%s) -> mult=(%.2f, %.2f)",
            style_a, f"λ={lambda_a:.3f}",
            style_b, f"λ={lambda_b:.3f}",
            mult_a, mult_b,
        )
    return lambda_a * mult_a, lambda_b * mult_b
