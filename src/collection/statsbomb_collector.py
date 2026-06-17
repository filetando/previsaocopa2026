"""Coleta e padroniza dados do StatsBomb Open Data para selecoes nacionais."""
import logging
import warnings
from typing import Any

import pandas as pd
from statsbombpy import sb
from tqdm import tqdm

from src.utils.config import DATA_RAW, STATSBOMB_COMPETITIONS

logger = logging.getLogger(__name__)

COMPETITION_TYPE: dict[str, str] = {
    "copa_america_2024": "continental",
    "euro_2024": "continental",
    "afcon_2023": "continental",
    "world_cup_2022": "continental",
    "euro_2020": "continental",
}

SCHEMA_COLS: list[str] = [
    "match_id", "team", "opponent", "date", "competition", "venue",
    "goals_scored", "goals_conceded", "shots_for", "shots_against",
    "shots_on_target_for", "shots_on_target_against", "corners_for",
    "corners_against", "xg_for", "xg_against", "elo_team", "elo_opponent",
    "source", "data_quality",
]


def _extrair_metricas_eventos(
    eventos: pd.DataFrame, team: str
) -> dict[str, Any]:
    """
    Extrai xG, chutes, chutes no alvo e escanteios de eventos StatsBomb.

    Args:
        eventos: DataFrame de eventos de uma partida (statsbombpy.sb.events()).
        team: Nome exato do time conforme aparece nos dados StatsBomb.

    Returns:
        Dicionario com metricas ofensivas e defensivas do time.
    """
    resultado: dict[str, Any] = {
        "shots_for": 0,
        "shots_against": 0,
        "shots_on_target_for": 0,
        "shots_on_target_against": 0,
        "xg_for": None,
        "xg_against": None,
        "corners_for": 0,
        "corners_against": 0,
    }

    if eventos.empty:
        return resultado

    # --- Chutes ---
    chutes_mask = eventos["type"] == "Shot"
    if chutes_mask.any():
        chutes = eventos[chutes_mask]
        chutes_team = chutes[chutes["team"] == team]
        chutes_opp = chutes[chutes["team"] != team]

        resultado["shots_for"] = len(chutes_team)
        resultado["shots_against"] = len(chutes_opp)

        if "shot_type" in chutes.columns:
            pen_team = chutes_team["shot_type"] == "Penalty"
            pen_opp = chutes_opp["shot_type"] == "Penalty"
        else:
            pen_team = pd.Series(False, index=chutes_team.index)
            pen_opp = pd.Series(False, index=chutes_opp.index)

        if "shot_statsbomb_xg" in chutes.columns:
            resultado["xg_for"] = float(
                chutes_team.loc[~pen_team, "shot_statsbomb_xg"].fillna(0).sum()
            )
            resultado["xg_against"] = float(
                chutes_opp.loc[~pen_opp, "shot_statsbomb_xg"].fillna(0).sum()
            )

        if "shot_outcome" in chutes.columns:
            on_target = {"Saved", "Goal"}
            resultado["shots_on_target_for"] = int(
                chutes_team["shot_outcome"].isin(on_target).sum()
            )
            resultado["shots_on_target_against"] = int(
                chutes_opp["shot_outcome"].isin(on_target).sum()
            )

    # --- Escanteios ---
    passes_mask = eventos["type"] == "Pass"
    if passes_mask.any() and "pass_type" in eventos.columns:
        passes = eventos[passes_mask]
        corner_mask = passes["pass_type"] == "Corner"
        resultado["corners_for"] = int(
            (corner_mask & (passes["team"] == team)).sum()
        )
        resultado["corners_against"] = int(
            (corner_mask & (passes["team"] != team)).sum()
        )

    return resultado


def collect_competition(competition_key: str) -> pd.DataFrame:
    """
    Coleta todas as partidas de uma competicao StatsBomb no schema universal.

    Cada partida gera duas linhas (uma por time). Os campos elo_team e
    elo_opponent ficam None aqui e sao preenchidos pelo standardizer.

    Args:
        competition_key: Chave da competicao conforme STATSBOMB_COMPETITIONS.

    Returns:
        DataFrame no schema universal com duas linhas por partida.

    Raises:
        ValueError: Se competition_key nao for reconhecida.
    """
    if competition_key not in STATSBOMB_COMPETITIONS:
        raise ValueError(f"Competicao desconhecida: '{competition_key}'")

    comp = STATSBOMB_COMPETITIONS[competition_key]
    comp_type = COMPETITION_TYPE.get(competition_key, "continental")

    logger.info(
        "Iniciando coleta: %s (competition_id=%s, season_id=%s)",
        competition_key, comp["competition_id"], comp["season_id"],
    )

    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        partidas = sb.matches(
            competition_id=comp["competition_id"],
            season_id=comp["season_id"],
        )

    logger.info("Total de partidas encontradas: %d", len(partidas))
    rows: list[dict[str, Any]] = []

    for _, partida in tqdm(partidas.iterrows(), total=len(partidas), desc=competition_key):
        match_id = partida["match_id"]
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                eventos = sb.events(match_id=match_id)

            pares = [
                (partida["home_team"], partida["away_team"],
                 partida["home_score"], partida["away_score"]),
                (partida["away_team"], partida["home_team"],
                 partida["away_score"], partida["home_score"]),
            ]
            for team, opponent, goals_f, goals_a in pares:
                metricas = _extrair_metricas_eventos(eventos, team)
                rows.append({
                    "match_id": str(match_id),
                    "team": team,
                    "opponent": opponent,
                    "date": pd.Timestamp(partida["match_date"]).strftime("%Y-%m-%d"),
                    "competition": comp_type,
                    "venue": "neutral",
                    "goals_scored": int(goals_f),
                    "goals_conceded": int(goals_a),
                    **metricas,
                    "elo_team": None,
                    "elo_opponent": None,
                    "source": "statsbomb",
                    "data_quality": "high",
                })

        except Exception as e:
            logger.error("Falha na coleta para match_id=%s: %s", match_id, str(e))
            continue

    df = pd.DataFrame(rows, columns=SCHEMA_COLS)
    logger.info("Coletadas %d linhas para %s", len(df), competition_key)
    return df


def save_competition(df: pd.DataFrame, competition_key: str) -> None:
    """
    Salva DataFrame de uma competicao em data/raw/statsbomb/.

    Args:
        df: DataFrame no schema universal.
        competition_key: Chave da competicao (define o nome do arquivo parquet).
    """
    out_dir = DATA_RAW / "statsbomb"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{competition_key}.parquet"
    df.to_parquet(out_path, index=False)
    logger.info("Salvo: %s (%d linhas)", out_path, len(df))


def collect_all() -> None:
    """Coleta e salva todas as competicoes StatsBomb configuradas."""
    for competition_key in STATSBOMB_COMPETITIONS:
        logger.info("=== Processando: %s ===", competition_key)
        try:
            df = collect_competition(competition_key)
            if not df.empty:
                save_competition(df, competition_key)
        except Exception as e:
            logger.error("Erro inesperado para %s: %s", competition_key, str(e))
            raise


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    collect_all()
