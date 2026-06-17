"""Calculo de pesos de competicao e decaimento temporal para o modelo xG."""
import math
import logging
from datetime import datetime

from src.utils.config import COMPETITION_WEIGHTS, HALF_LIFE_DAYS

logger = logging.getLogger(__name__)


def calcular_peso_competicao(tipo: str) -> float:
    """
    Retorna o peso de importancia de uma competicao.

    Args:
        tipo: Tipo da competicao ("continental", "qualifier" ou "friendly").

    Returns:
        Peso: 1.2 para continental, 1.0 para qualifier, 0.8 para friendly.
        Retorna 1.0 se tipo desconhecido (com warning).
    """
    peso = COMPETITION_WEIGHTS.get(tipo)
    if peso is None:
        logger.warning("Tipo de competicao desconhecido: '%s' — usando peso 1.0", tipo)
        return 1.0
    return float(peso)


def calcular_peso_temporal(
    data_partida: datetime,
    data_referencia: datetime,
    meia_vida_dias: int = HALF_LIFE_DAYS,
) -> float:
    """
    Calcula o peso temporal via decaimento exponencial.

    Args:
        data_partida: Data em que a partida foi disputada.
        data_referencia: Data base para o calculo (normalmente hoje ou inicio Copa).
        meia_vida_dias: Dias para o peso cair a metade (padrao: 730 = 24 meses).

    Returns:
        Peso entre 0 e 1. Partidas na data de referencia retornam 1.0.
        Partidas futuras (data_partida > data_referencia) retornam 1.0.
    """
    delta = (data_referencia - data_partida).days
    if delta <= 0:
        return 1.0
    lambda_ = math.log(2) / meia_vida_dias
    return math.exp(-lambda_ * delta)


def calcular_peso_final(
    peso_competicao: float,
    peso_temporal: float,
) -> float:
    """
    Combina peso de competicao e peso temporal em um unico peso por partida.

    O Elo do adversario NAO e aplicado aqui — e ponderado individualmente
    por metrica na fase de feature engineering.

    Args:
        peso_competicao: Retorno de calcular_peso_competicao().
        peso_temporal: Retorno de calcular_peso_temporal().

    Returns:
        Peso final a ser aplicado em todas as metricas da partida.
    """
    return peso_competicao * peso_temporal
