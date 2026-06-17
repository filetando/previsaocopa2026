"""
Padronizador de dados brutos da Copa 2026.

Unifica partidas de todas as fontes (StatsBomb, eloratings), preenche
elo_team/elo_opponent por data e gera relatorio de cobertura.
"""
import argparse
import logging
from pathlib import Path

import pandas as pd

from src.collection.elo_collector import get_elo_on_date
from src.collection.teams import COPA_2026_TEAMS
from src.utils.config import DATA_RAW, DATA_PROCESSED, REFERENCE_DATE_STR, WINDOW_YEARS

logger = logging.getLogger(__name__)

SCHEMA_COLS: list[str] = [
    "match_id", "team", "opponent", "date", "competition", "venue",
    "goals_scored", "goals_conceded",
    "shots_for", "shots_against",
    "shots_on_target_for", "shots_on_target_against",
    "corners_for", "corners_against",
    "xg_for", "xg_against",
    "elo_team", "elo_opponent",
    "source", "data_quality",
]


def _load_statsbomb() -> pd.DataFrame:
    """
    Carrega todas as partidas StatsBomb do data/raw/statsbomb/.

    Returns:
        DataFrame concatenado de todas as competicoes StatsBomb.
    """
    sb_dir = DATA_RAW / "statsbomb"
    frames: list[pd.DataFrame] = []

    for parquet in sb_dir.glob("*.parquet"):
        try:
            df = pd.read_parquet(parquet)
            frames.append(df)
            logger.info("StatsBomb carregado: %s (%d linhas)", parquet.name, len(df))
        except Exception as e:
            logger.error("Falha ao carregar %s: %s", parquet, str(e))

    if not frames:
        logger.warning("Nenhum arquivo StatsBomb encontrado em %s", sb_dir)
        return pd.DataFrame(columns=SCHEMA_COLS)

    return pd.concat(frames, ignore_index=True)


def _load_eloratings() -> pd.DataFrame:
    """
    Carrega partidas coletadas do eloratings.net.

    Returns:
        DataFrame de partidas do eloratings.
    """
    path = DATA_RAW / "eloratings" / "partidas_eloratings.parquet"
    if not path.exists():
        logger.warning("Arquivo eloratings nao encontrado: %s", path)
        return pd.DataFrame(columns=SCHEMA_COLS)

    df = pd.read_parquet(path)
    logger.info("eloratings carregado: %d linhas", len(df))
    return df


def _fill_elo(df: pd.DataFrame, historico_elo: pd.DataFrame) -> pd.DataFrame:
    """
    Preenche elo_team e elo_opponent para cada partida usando o historico de Elo.

    Apenas linhas com elo_team=None ou elo_opponent=None sao atualizadas.
    O Elo usado e o mais recente disponivel na data da partida.

    Args:
        df: DataFrame no schema universal (pode ter elo=None).
        historico_elo: DataFrame com [team, date, elo] do elo_collector.

    Returns:
        DataFrame com elo_team e elo_opponent preenchidos.
    """
    df = df.copy()
    df["date"] = pd.to_datetime(df["date"])

    mask = df["elo_team"].isna() | df["elo_opponent"].isna()
    n_fill = mask.sum()
    logger.info("Preenchendo Elo em %d linhas...", n_fill)

    for idx in df[mask].index:
        row = df.loc[idx]
        date = row["date"]
        if pd.isna(row.get("elo_team")):
            df.at[idx, "elo_team"] = get_elo_on_date(historico_elo, row["team"], date)
        if pd.isna(row.get("elo_opponent")):
            df.at[idx, "elo_opponent"] = get_elo_on_date(historico_elo, row["opponent"], date)

    n_remaining = df["elo_team"].isna().sum() + df["elo_opponent"].isna().sum()
    logger.info("Elo preenchido. Colunas ainda vazias: %d", n_remaining)
    return df


def _remove_duplicates(df: pd.DataFrame) -> pd.DataFrame:
    """
    Remove partidas duplicadas priorizando a fonte de maior qualidade.

    Quando a mesma partida aparece em StatsBomb (high) e eloratings (low),
    mantemos apenas o registro StatsBomb.

    Args:
        df: DataFrame concatenado de todas as fontes.

    Returns:
        DataFrame sem duplicatas.
    """
    quality_order = {"high": 0, "medium": 1, "low": 2}
    df = df.copy()
    df["_quality_rank"] = df["data_quality"].map(quality_order).fillna(3)
    df = df.sort_values("_quality_rank")
    df = df.drop_duplicates(subset=["match_id"], keep="first")
    df = df.drop(columns=["_quality_rank"])
    logger.info("Apos remocao de duplicatas: %d linhas", len(df))
    return df


def _filter_window(df: pd.DataFrame) -> pd.DataFrame:
    """
    Filtra partidas para a janela temporal do modelo (WINDOW_YEARS antes de REFERENCE_DATE).

    StatsBomb inclui World Cup 2022 (fora da janela) que e mantida intencionalmente
    para aumentar cobertura; o decaimento temporal desconta partidas antigas.

    Args:
        df: DataFrame com coluna date (datetime).

    Returns:
        DataFrame filtrado para a janela do modelo.
    """
    ref_date = pd.Timestamp(REFERENCE_DATE_STR)
    date_start = ref_date - pd.DateOffset(years=WINDOW_YEARS)

    # StatsBomb: manter mesmo fora da janela (contém torneios continentais valiosos)
    mask_statsbomb = df["source"] == "statsbomb"
    mask_window = df["date"] >= date_start

    df_filtered = df[mask_statsbomb | mask_window].copy()
    n_removed = len(df) - len(df_filtered)
    if n_removed > 0:
        logger.info("Removidas %d partidas fora da janela (nao-StatsBomb)", n_removed)
    return df_filtered


def standardize() -> pd.DataFrame:
    """
    Pipeline completo de padronizacao: carrega, une, deduplica e preenche Elo.

    Returns:
        DataFrame no schema universal com todos os campos preenchidos.
    """
    logger.info("=== Iniciando padronizacao ===")

    df_sb = _load_statsbomb()
    df_elo = _load_eloratings()

    df_all = pd.concat([df_sb, df_elo], ignore_index=True)
    df_all["date"] = pd.to_datetime(df_all["date"])
    logger.info("Total antes de deduplicacao: %d linhas", len(df_all))

    df_all = _filter_window(df_all)
    df_all = _remove_duplicates(df_all)

    logger.info("Carregando historico de Elo...")
    historico_elo = pd.read_parquet(DATA_RAW / "elo" / "elo_historico.parquet")
    historico_elo["date"] = pd.to_datetime(historico_elo["date"])

    df_all = _fill_elo(df_all, historico_elo)
    df_all = df_all[SCHEMA_COLS]
    df_all = df_all.sort_values(["team", "date"]).reset_index(drop=True)

    logger.info("Padronizacao concluida: %d linhas, %d times", len(df_all), df_all["team"].nunique())
    return df_all


def generate_coverage_report(df: pd.DataFrame, output_path: Path) -> None:
    """
    Gera relatorio de cobertura de dados por selecao.

    Valida se cada time tem pelo menos 15 partidas e 1 competicao oficial.
    Times abaixo do threshold sao documentados como alertas.

    Args:
        df: DataFrame padronizado.
        output_path: Caminho do arquivo Markdown de saida.
    """
    ref_date = pd.Timestamp(REFERENCE_DATE_STR)
    date_start = ref_date - pd.DateOffset(years=WINDOW_YEARS)

    lines: list[str] = [
        "# Relatorio de Cobertura de Dados — Copa 2026",
        "",
        f"**Data de referencia:** {REFERENCE_DATE_STR}",
        f"**Janela de coleta:** {date_start.date()} a {REFERENCE_DATE_STR}",
        f"**Total de partidas:** {len(df)}",
        f"**Times cobertos:** {df['team'].nunique()} / 48",
        "",
        "---",
        "",
        "## Cobertura por Selecao",
        "",
        "| Selecao | Partidas | Oficiais | % High | % Medium | % Low | Status |",
        "|---|---|---|---|---|---|---|",
    ]

    alerts: list[str] = []

    for team in sorted(COPA_2026_TEAMS):
        tm = df[df["team"] == team]
        n_total = len(tm)
        n_official = len(tm[tm["competition"].isin(["continental", "qualifier"])])
        n_high = len(tm[tm["data_quality"] == "high"])
        n_med = len(tm[tm["data_quality"] == "medium"])
        n_low = len(tm[tm["data_quality"] == "low"])

        pct_high = f"{100*n_high/n_total:.0f}%" if n_total > 0 else "—"
        pct_med = f"{100*n_med/n_total:.0f}%" if n_total > 0 else "—"
        pct_low = f"{100*n_low/n_total:.0f}%" if n_total > 0 else "—"

        ok_matches = n_total >= 15
        ok_official = n_official >= 1
        status = "OK" if (ok_matches and ok_official) else "ALERTA"
        if status == "ALERTA":
            alerts.append(f"- **{team}**: {n_total} partidas, {n_official} oficiais")

        lines.append(
            f"| {team} | {n_total} | {n_official} | {pct_high} | {pct_med} | {pct_low} | {status} |"
        )

    lines += [
        "",
        "---",
        "",
        "## Alertas (abaixo do threshold)",
        "",
        "Times com menos de 15 partidas ou sem competicoes oficiais:",
        "",
    ]

    if alerts:
        lines.extend(alerts)
    else:
        lines.append("Nenhum time abaixo do threshold.")

    lines += [
        "",
        "---",
        "",
        "## Distribuicao por Fonte",
        "",
        f"- **StatsBomb (high):** {len(df[df['source']=='statsbomb'])} partidas",
        f"- **eloratings (low):** {len(df[df['source']=='eloratings'])} partidas",
        "",
        "## Distribuicao por Tipo de Competicao",
        "",
        f"- **Continental:** {len(df[df['competition']=='continental'])}",
        f"- **Qualifier:** {len(df[df['competition']=='qualifier'])}",
        f"- **Friendly:** {len(df[df['competition']=='friendly'])}",
    ]

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines), encoding="utf-8")
    logger.info("Relatorio salvo: %s", output_path)

    n_ok = sum(1 for t in COPA_2026_TEAMS if len(df[df["team"] == t]) >= 15 and
               len(df[(df["team"] == t) & (df["competition"].isin(["continental", "qualifier"]))]) >= 1)
    logger.info("Times aprovados no threshold: %d / %d", n_ok, len(COPA_2026_TEAMS))
    if alerts:
        logger.warning("Times com alerta: %d", len(alerts))
        for a in alerts:
            logger.warning("  %s", a)


def save(df: pd.DataFrame) -> None:
    """
    Salva o dataset padronizado em data/processed/matches/.

    Args:
        df: DataFrame no schema universal.
    """
    out_dir = DATA_PROCESSED / "matches"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "partidas_padronizadas_v1.parquet"
    df.to_parquet(out_path, index=False)
    logger.info("Salvo: %s (%d linhas)", out_path, len(df))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Padronizador de dados Copa 2026")
    parser.add_argument("--report", action="store_true", help="Gera relatorio de cobertura")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    df = standardize()
    save(df)

    if args.report:
        from src.utils.config import ROOT_DIR
        report_path = ROOT_DIR / "outputs" / "coverage_report.md"
        generate_coverage_report(df, report_path)
