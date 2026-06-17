"""Coleta historico de Elo de selecoes nacionais do eloratings.net."""
import io
import logging
import random
import time
from collections import Counter
from datetime import datetime
from typing import Optional

import pandas as pd
import requests

from src.collection.teams import COPA_2026_TEAMS, ELO_URL_SLUG
from src.utils.config import DATA_RAW

logger = logging.getLogger(__name__)

BASE_URL = "https://www.eloratings.net"

# Indices das colunas no TSV do eloratings.net (sem cabecalho)
# [year, month, day, team1_code, team2_code, goals1, goals2, comp,
#  ?, elo_change_t1, elo_after_t1, elo_after_t2, ...]
_COL_YEAR = 0
_COL_MONTH = 1
_COL_DAY = 2
_COL_TEAM1 = 3
_COL_TEAM2 = 4
_COL_ELO_AFTER_T1 = 10
_COL_ELO_AFTER_T2 = 11


def _detectar_codigo_time(df: pd.DataFrame) -> str:
    """
    Identifica o codigo de 2 letras do time dono do arquivo TSV.

    O time do arquivo aparece em todos os jogos (col3 OU col4). O codigo
    com frequencia igual ao numero de partidas e o time do arquivo.

    Para arquivos que contem selecoes renomeadas (ex: Tchecoslováquia/CS
    -> Republica Tcheca/CZ), o codigo unico nao existe. Nesse caso usa
    as ultimas 100 linhas (mais recentes, pois o TSV e cronologico).

    Args:
        df: DataFrame bruto lido do TSV do eloratings.net.

    Returns:
        Codigo de 2 letras (ex: 'BR', 'FR', 'CZ').
    """
    n = len(df)
    contagem = Counter(df[_COL_TEAM1].tolist() + df[_COL_TEAM2].tolist())
    for codigo, freq in contagem.most_common():
        if freq == n:
            return str(codigo)
    # Nenhum codigo aparece em 100% das linhas: selecao mudou de codigo
    # historicamente (ex: CS->CZ). Usa as ultimas 100 linhas (mais recentes).
    tail = df.tail(min(100, n))
    recentes = Counter(tail[_COL_TEAM1].tolist() + tail[_COL_TEAM2].tolist())
    return str(recentes.most_common(1)[0][0])


def _parse_historico(df: pd.DataFrame, codigo: str) -> pd.DataFrame:
    """
    Converte o DataFrame bruto do eloratings.net em serie temporal de Elo.

    Args:
        df: DataFrame bruto (16 colunas sem cabecalho).
        codigo: Codigo de 2 letras do time (ex: 'BR').

    Returns:
        DataFrame com colunas [date, elo] ordenado por data.
    """
    registros: list[dict] = []

    for _, row in df.iterrows():
        try:
            date = pd.Timestamp(
                year=int(row[_COL_YEAR]),
                month=int(row[_COL_MONTH]),
                day=int(row[_COL_DAY]),
            )
        except (ValueError, TypeError):
            continue

        if str(row[_COL_TEAM1]) == codigo:
            elo_raw = row[_COL_ELO_AFTER_T1]
        elif str(row[_COL_TEAM2]) == codigo:
            elo_raw = row[_COL_ELO_AFTER_T2]
        else:
            continue

        try:
            elo = float(elo_raw)
        except (ValueError, TypeError):
            continue

        registros.append({"date": date, "elo": elo})

    return pd.DataFrame(registros).sort_values("date").reset_index(drop=True)


def _extract_from_opponents(
    team_name: str,
    opponent_slugs: Optional[list[str]] = None,
) -> Optional[pd.DataFrame]:
    """
    Extrai historico de Elo de um time a partir dos TSVs de adversarios.

    Usado para times sem TSV dedicado (ex: United States, codigo 'US').
    O Elo do time aparece como elo_after_t2 nos arquivos dos adversarios.

    Args:
        team_name: Nome padrao do time.
        opponent_slugs: Slugs dos adversarios a consultar. Padrao: Mexico e Canada.

    Returns:
        DataFrame com colunas [date, elo] ou None se nenhum dado encontrado.
    """
    # Mapeamento de nomes sem TSV para seus codigos de 2 letras
    TEAM_CODES: dict[str, str] = {"United States": "US"}
    team_code = TEAM_CODES.get(team_name)

    if team_code is None:
        logger.warning("Codigo desconhecido para extracao via adversarios: %s", team_name)
        return None

    opponent_slugs = opponent_slugs or ["Mexico", "Canada"]
    frames: list[pd.DataFrame] = []

    for slug in opponent_slugs:
        url = f"{BASE_URL}/{slug}.tsv"
        try:
            r = requests.get(url, timeout=30)
            r.raise_for_status()
            df_raw = pd.read_csv(
                io.StringIO(r.content.decode("utf-8", errors="replace")),
                sep="\t", header=None, dtype=str,
            )
        except Exception as e:
            logger.warning("Falha ao baixar TSV de adversario %s: %s", slug, str(e))
            continue

        # Filtra apenas partidas onde o time de interesse aparece
        team_as_t2 = df_raw[df_raw[_COL_TEAM2] == team_code]
        team_as_t1 = df_raw[df_raw[_COL_TEAM1] == team_code]

        for _, row in team_as_t2.iterrows():
            try:
                date = pd.Timestamp(int(row[_COL_YEAR]), int(row[_COL_MONTH]), int(row[_COL_DAY]))
                elo = float(row[_COL_ELO_AFTER_T2])
                frames.append(pd.DataFrame([{"date": date, "elo": elo}]))
            except (ValueError, TypeError):
                continue

        for _, row in team_as_t1.iterrows():
            try:
                date = pd.Timestamp(int(row[_COL_YEAR]), int(row[_COL_MONTH]), int(row[_COL_DAY]))
                elo = float(row[_COL_ELO_AFTER_T1])
                frames.append(pd.DataFrame([{"date": date, "elo": elo}]))
            except (ValueError, TypeError):
                continue

        time.sleep(random.uniform(0.3, 0.8))

    if not frames:
        return None

    df = (
        pd.concat(frames, ignore_index=True)
        .drop_duplicates(subset=["date"])
        .sort_values("date")
        .reset_index(drop=True)
    )
    logger.info("Extraido via adversarios — %s: %d registros", team_name, len(df))
    return df


def fetch_team_history(team_name: str) -> Optional[pd.DataFrame]:
    """
    Baixa e parseia o historico de Elo de uma selecao do eloratings.net.

    Para times sem TSV dedicado (slug=None no ELO_URL_SLUG), tenta extrair
    o historico a partir dos arquivos de adversarios frequentes.

    Args:
        team_name: Nome padrao do time (ex: 'Brazil', 'South Korea').

    Returns:
        DataFrame com colunas [date, elo] ou None se falhar.
    """
    slug = ELO_URL_SLUG.get(team_name)

    if slug is None:
        historico = _extract_from_opponents(team_name)
        if historico is not None:
            historico.insert(0, "team", team_name)
        return historico

    url = f"{BASE_URL}/{slug}.tsv"

    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()
    except requests.RequestException as e:
        logger.warning("Falha ao baixar Elo para %s (%s): %s", team_name, url, str(e))
        return None

    try:
        df_raw = pd.read_csv(
            io.StringIO(response.content.decode("utf-8", errors="replace")),
            sep="\t",
            header=None,
            dtype=str,
        )
    except Exception as e:
        logger.error("Erro ao parsear TSV de %s: %s", team_name, str(e))
        return None

    if df_raw.empty or len(df_raw.columns) < 12:
        logger.warning("TSV vazio ou formato inesperado para %s", team_name)
        return None

    codigo = _detectar_codigo_time(df_raw)
    logger.info("Time: %s | Codigo: %s | Partidas: %d", team_name, codigo, len(df_raw))

    historico = _parse_historico(df_raw, codigo)
    historico.insert(0, "team", team_name)
    return historico


def build_historical_elo(
    teams: Optional[list[str]] = None,
    delay_min: float = 0.5,
    delay_max: float = 1.5,
) -> pd.DataFrame:
    """
    Baixa e consolida o historico de Elo para todas as selecoes.

    Args:
        teams: Lista de nomes de times. Usa COPA_2026_TEAMS se None.
        delay_min: Delay minimo entre requests (segundos).
        delay_max: Delay maximo entre requests (segundos).

    Returns:
        DataFrame com colunas [team, date, elo] para todas as selecoes.
    """
    teams = teams or COPA_2026_TEAMS
    frames: list[pd.DataFrame] = []
    falhas: list[str] = []

    for team in teams:
        logger.info("Coletando Elo: %s", team)
        historico = fetch_team_history(team)

        if historico is not None and not historico.empty:
            frames.append(historico)
        else:
            logger.warning("Cobertura incompleta para %s: sem dados", team)
            falhas.append(team)

        time.sleep(random.uniform(delay_min, delay_max))

    if falhas:
        logger.warning("Times sem dados de Elo (%d): %s", len(falhas), falhas)

    if not frames:
        raise RuntimeError("Nenhum dado de Elo coletado.")

    df = pd.concat(frames, ignore_index=True)
    df["date"] = pd.to_datetime(df["date"])
    df["elo"] = pd.to_numeric(df["elo"], errors="coerce")
    df = df.dropna(subset=["elo"]).sort_values(["team", "date"]).reset_index(drop=True)

    logger.info(
        "Historico consolidado: %d times, %d registros",
        df["team"].nunique(), len(df),
    )
    return df


def get_elo_on_date(
    historico: pd.DataFrame,
    team: str,
    date: datetime,
) -> float:
    """
    Retorna o Elo da selecao na data da partida (ou o mais recente anterior).

    Args:
        historico: DataFrame com colunas [team, date, elo].
        team: Nome padrao do time.
        date: Data da partida.

    Returns:
        Valor de Elo. Retorna ELO_MEDIA_GLOBAL (1500) se nao encontrado.
    """
    from src.utils.config import ELO_MEDIA_GLOBAL

    team_df = historico[historico["team"] == team]
    if team_df.empty:
        logger.warning("Time nao encontrado no historico de Elo: %s", team)
        return ELO_MEDIA_GLOBAL

    anteriores = team_df[team_df["date"] <= pd.Timestamp(date)]
    if anteriores.empty:
        logger.warning("Sem Elo anterior a %s para %s — usando o mais antigo disponivel", date, team)
        return float(team_df.sort_values("date").iloc[0]["elo"])

    return float(anteriores.sort_values("date").iloc[-1]["elo"])


def save_elo_historico(df: pd.DataFrame) -> None:
    """
    Salva o historico de Elo consolidado em data/raw/elo/.

    Args:
        df: DataFrame com colunas [team, date, elo].
    """
    out_dir = DATA_RAW / "elo"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "elo_historico.parquet"
    df.to_parquet(out_path, index=False)
    logger.info("Salvo: %s (%d registros, %d times)", out_path, len(df), df["team"].nunique())


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    df = build_historical_elo()
    save_elo_historico(df)
