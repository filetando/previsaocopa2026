"""
Extrai dados de partidas do eloratings.net para as 48 selecoes da Copa 2026.

Fonte: arquivos TSV individuais por selecao (mesma fonte do elo_collector).
Cobertura: todos os jogos internacionais de cada selecao desde 1872.
Qualidade: data_quality='low' (gols + tipo de competicao, sem xG/chutes).
Uso: complementa StatsBomb para times sem torneios continentais recentes.
"""
import io
import logging
import random
import time
from typing import Optional

import pandas as pd
import requests

from src.collection.elo_collector import _detectar_codigo_time
from src.collection.teams import COPA_2026_TEAMS, ELO_URL_SLUG
from src.utils.config import DATA_RAW, REFERENCE_DATE_STR, WINDOW_YEARS

logger = logging.getLogger(__name__)

BASE_URL = "https://www.eloratings.net"

# Mapeamento de codigos de competicao do eloratings.net -> schema universal
COMP_TYPE_MAP: dict[str, str] = {
    # Torneios continentais e Copa do Mundo
    "WC": "continental",
    "CA": "continental",   # Copa América / AFCON / AFC Asian Cup
    "CC": "continental",   # CONCACAF Gold Cup / similares
    "OCC": "continental",
    "CCH": "continental",
    "OHC": "continental",
    "CON": "continental",
    "AGC": "continental",
    "MND": "continental",
    "USC": "continental",
    "ATL": "continental",
    "NLC": "continental",
    # Eliminatorias Copa do Mundo
    "WQ": "qualifier",
    "ROC": "qualifier",
    "RBC": "qualifier",
    "PAC": "qualifier",
    "BRI": "qualifier",
    "SAC": "qualifier",
    # Amistosos (tudo que nao se encaixa acima)
    "F": "friendly",
    "FT": "friendly",
    "FRC": "friendly",
}

# Colunas do TSV do eloratings.net (sem cabecalho)
_COL_YEAR = 0
_COL_MONTH = 1
_COL_DAY = 2
_COL_TEAM1 = 3
_COL_TEAM2 = 4
_COL_GOALS1 = 5
_COL_GOALS2 = 6
_COL_COMP = 7


def _build_code_map(
    teams: list[str],
    delay_min: float = 0.3,
    delay_max: float = 0.8,
) -> dict[str, str]:
    """
    Constroi mapeamento {codigo_elo: nome_time} para todas as selecoes.

    Necessario para identificar o adversario pelo codigo de 2 letras
    que aparece nas colunas team1/team2 dos TSVs.

    Args:
        teams: Lista de nomes de times.
        delay_min: Delay minimo entre requests.
        delay_max: Delay maximo entre requests.

    Returns:
        Dicionario {codigo: nome} para cada time com TSV disponivel.
    """
    code_map: dict[str, str] = {"US": "United States"}  # USA sem TSV dedicado

    for team in teams:
        slug = ELO_URL_SLUG.get(team)
        if slug is None:
            continue
        url = f"{BASE_URL}/{slug}.tsv"
        try:
            r = requests.get(url, timeout=20)
            r.raise_for_status()
            df_raw = pd.read_csv(
                io.StringIO(r.content.decode("utf-8", errors="replace")),
                sep="\t", header=None, dtype=str,
            )
            codigo = _detectar_codigo_time(df_raw)
            code_map[codigo] = team
        except Exception as e:
            logger.warning("Falha ao mapear codigo de %s: %s", team, str(e))
        time.sleep(random.uniform(delay_min, delay_max))

    logger.info("Codigos mapeados: %d times", len(code_map))
    return code_map


def _extract_matches(
    df_raw: pd.DataFrame,
    team_name: str,
    team_code: str,
    code_map: dict[str, str],
    date_start: pd.Timestamp,
    date_end: pd.Timestamp,
) -> list[dict]:
    """
    Extrai partidas de um TSV do eloratings.net no periodo especificado.

    Args:
        df_raw: DataFrame bruto do TSV (16 colunas sem cabecalho).
        team_name: Nome padrao do time dono do arquivo.
        team_code: Codigo de 2 letras do time (ex: 'BR').
        code_map: Mapeamento {codigo: nome} para resolver adversarios.
        date_start: Data inicial do filtro.
        date_end: Data final do filtro.

    Returns:
        Lista de dicionarios no schema universal (sem elo_team/elo_opponent).
    """
    rows: list[dict] = []

    for _, row in df_raw.iterrows():
        try:
            date = pd.Timestamp(
                year=int(row[_COL_YEAR]),
                month=int(row[_COL_MONTH]),
                day=int(row[_COL_DAY]),
            )
        except (ValueError, TypeError):
            continue

        if not (date_start <= date <= date_end):
            continue

        team1_code = str(row[_COL_TEAM1])
        team2_code = str(row[_COL_TEAM2])
        comp_code = str(row[_COL_COMP]).strip()

        # Determina gols e venue
        try:
            goals1 = int(row[_COL_GOALS1])
            goals2 = int(row[_COL_GOALS2])
        except (ValueError, TypeError):
            continue

        comp_type = COMP_TYPE_MAP.get(comp_code, "friendly")

        if team1_code == team_code:
            goals_f, goals_a = goals1, goals2
            opp_code = team2_code
            venue = "home" if comp_type == "qualifier" else "neutral"
        elif team2_code == team_code:
            goals_f, goals_a = goals2, goals1
            opp_code = team1_code
            venue = "away" if comp_type == "qualifier" else "neutral"
        else:
            continue

        opponent = code_map.get(opp_code, opp_code)
        match_id = f"elo_{team_code}_{date.strftime('%Y%m%d')}_{opp_code}"

        rows.append({
            "match_id": match_id,
            "team": team_name,
            "opponent": opponent,
            "date": date.strftime("%Y-%m-%d"),
            "competition": comp_type,
            "venue": venue,
            "goals_scored": goals_f,
            "goals_conceded": goals_a,
            "shots_for": None,
            "shots_against": None,
            "shots_on_target_for": None,
            "shots_on_target_against": None,
            "corners_for": None,
            "corners_against": None,
            "xg_for": None,
            "xg_against": None,
            "elo_team": None,
            "elo_opponent": None,
            "source": "eloratings",
            "data_quality": "low",
        })

    return rows


def _collect_usa_matches(
    code_map: dict[str, str],
    date_start: pd.Timestamp,
    date_end: pd.Timestamp,
    opponent_slugs: Optional[list[str]] = None,
    delay_min: float = 0.5,
    delay_max: float = 1.2,
) -> list[dict]:
    """
    Coleta partidas dos EUA a partir dos TSVs de adversarios frequentes.

    Os EUA nao tem TSV dedicado no eloratings.net. As partidas aparecem
    nos arquivos de Mexico, Canada e Panama como adversarios.

    Args:
        code_map: Mapeamento {codigo: nome} para resolver adversarios.
        date_start: Data inicial do filtro.
        date_end: Data final do filtro.
        opponent_slugs: Slugs dos adversarios a consultar.
        delay_min: Delay minimo entre requests.
        delay_max: Delay maximo entre requests.

    Returns:
        Lista de dicionarios no schema universal para os EUA.
    """
    opponent_slugs = opponent_slugs or ["Mexico", "Canada", "Panama"]
    team_code = "US"
    team_name = "United States"
    seen_match_ids: set[str] = set()
    rows: list[dict] = []

    for slug in opponent_slugs:
        url = f"{BASE_URL}/{slug}.tsv"
        try:
            r = requests.get(url, timeout=20)
            r.raise_for_status()
            df_raw = pd.read_csv(
                io.StringIO(r.content.decode("utf-8", errors="replace")),
                sep="\t", header=None, dtype=str,
            )
        except Exception as e:
            logger.warning("Falha ao baixar TSV de %s para extracao dos EUA: %s", slug, str(e))
            time.sleep(random.uniform(delay_min, delay_max))
            continue

        for match in _extract_matches(df_raw, team_name, team_code, code_map, date_start, date_end):
            if match["match_id"] not in seen_match_ids:
                seen_match_ids.add(match["match_id"])
                rows.append(match)

        time.sleep(random.uniform(delay_min, delay_max))

    logger.info("United States (US): %d partidas no periodo (via adversarios)", len(rows))
    return rows


def collect_all(
    teams: Optional[list[str]] = None,
    delay_min: float = 0.5,
    delay_max: float = 1.2,
) -> pd.DataFrame:
    """
    Coleta partidas do eloratings.net para todas as selecoes no periodo do modelo.

    Args:
        teams: Lista de times. Usa COPA_2026_TEAMS se None.
        delay_min: Delay minimo entre downloads.
        delay_max: Delay maximo entre downloads.

    Returns:
        DataFrame no schema universal com data_quality='low'.
    """
    teams = teams or COPA_2026_TEAMS
    ref_date = pd.Timestamp(REFERENCE_DATE_STR)
    date_start = ref_date - pd.DateOffset(years=WINDOW_YEARS)
    date_end = ref_date

    logger.info(
        "Coletando partidas eloratings.net | janela: %s a %s",
        date_start.date(), date_end.date(),
    )

    logger.info("Construindo mapeamento de codigos...")
    code_map = _build_code_map(teams, delay_min, delay_max)

    all_rows: list[dict] = []

    for team in teams:
        slug = ELO_URL_SLUG.get(team)
        if slug is None:
            # USA: extrair partidas a partir dos TSVs de adversarios
            usa_rows = _collect_usa_matches(code_map, date_start, date_end, delay_min=delay_min, delay_max=delay_max)
            all_rows.extend(usa_rows)
            continue

        url = f"{BASE_URL}/{slug}.tsv"
        try:
            r = requests.get(url, timeout=20)
            r.raise_for_status()
            df_raw = pd.read_csv(
                io.StringIO(r.content.decode("utf-8", errors="replace")),
                sep="\t", header=None, dtype=str,
            )
        except Exception as e:
            logger.error("Falha ao baixar TSV para %s: %s", team, str(e))
            time.sleep(random.uniform(delay_min, delay_max))
            continue

        team_code = _detectar_codigo_time(df_raw)
        rows = _extract_matches(df_raw, team, team_code, code_map, date_start, date_end)
        logger.info("%s (%s): %d partidas no periodo", team, team_code, len(rows))
        all_rows.extend(rows)
        time.sleep(random.uniform(delay_min, delay_max))

    df = pd.DataFrame(all_rows)
    logger.info("Total coletado: %d linhas para %d times", len(df), df["team"].nunique() if not df.empty else 0)
    return df


def save(df: pd.DataFrame) -> None:
    """
    Salva dados de partidas do eloratings.net em data/raw/.

    Args:
        df: DataFrame no schema universal.
    """
    out_dir = DATA_RAW / "eloratings"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "partidas_eloratings.parquet"
    df.to_parquet(out_path, index=False)
    logger.info("Salvo: %s (%d linhas)", out_path, len(df))


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    df = collect_all()
    save(df)
