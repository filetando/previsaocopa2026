"""
Normaliza metricas de perfil para indices taticos 0-10 por selecao.

Usa percentis reais das 48 selecoes como benchmarks — evita escala absoluta
que dependeria de suposicoes sobre valores "maximos" historicos.
"""
import json
import logging
from pathlib import Path

import numpy as np
import pandas as pd

from src.utils.config import DATA_PROCESSED, ROOT_DIR

logger = logging.getLogger(__name__)

OUTPUT_DIR = ROOT_DIR / "outputs" / "team_profiles"

# Dimensoes taticas com suas metricas de entrada e direcao
# "higher_is_better": True  => maior valor = maior indice
# "higher_is_better": False => menor valor = maior indice (ex: gols sofridos)
DIMENSIONS: list[dict] = [
    {
        "name": "forca_ofensiva",
        "label": "Força Ofensiva",
        "metric": "gols_marcados_adj",
        "higher_is_better": True,
        "description": "Gols marcados por partida ajustados pelo Elo do adversario",
    },
    {
        "name": "solidez_defensiva",
        "label": "Solidez Defensiva",
        "metric": "gols_sofridos_adj",
        "higher_is_better": False,
        "description": "Gols sofridos por partida ajustados pelo Elo do adversario (menor = melhor)",
    },
    {
        "name": "qualidade_finalizacao",
        "label": "Qualidade de Finalização",
        "metric": "xg_for_adj",
        "higher_is_better": True,
        "description": "xG gerado por partida ajustado pelo Elo do adversario",
    },
    {
        "name": "dominio_territorial",
        "label": "Domínio Territorial",
        "metric": "razao_dominio",
        "higher_is_better": True,
        "description": "Fracao de chutes totais que sao a favor",
    },
    {
        "name": "eficiencia_finalizacao",
        "label": "Eficiência de Finalização",
        "metric": "precisao_finalizacao",
        "higher_is_better": True,
        "description": "Chutes no alvo / chutes totais",
    },
    {
        "name": "volume_ataque",
        "label": "Volume de Ataque",
        "metric": "chutes_for_adj",
        "higher_is_better": True,
        "description": "Chutes por partida ajustados pelo Elo do adversario",
    },
    {
        "name": "solidez_xg",
        "label": "Solidez Defensiva (xG)",
        "metric": "xg_against_adj",
        "higher_is_better": False,
        "description": "xG concedido por partida ajustado pelo Elo do adversario (menor = melhor)",
    },
]


def _normalize_to_index(
    series: pd.Series,
    higher_is_better: bool = True,
) -> pd.Series:
    """
    Normaliza uma serie para escala 0-10 usando percentis.

    Usa rank percentil para ser robusto a outliers. O time com maior
    valor recebe 10 (se higher_is_better=True) e o menor recebe 0.
    Times sem dados (NaN) recebem NaN no indice — nao sao pontuados.

    Args:
        series: Serie com valores das 48 selecoes.
        higher_is_better: Se True, maior valor = maior indice.

    Returns:
        Serie normalizada para [0, 10], com NaN onde nao ha dados.
    """
    # na_option='keep': NaN permanece NaN (nao distorce o ranking)
    percentile = series.rank(pct=True, na_option="keep")
    if not higher_is_better:
        percentile = 1 - percentile
    return (percentile * 10).clip(0, 10)


def build_indices(df_profiles: pd.DataFrame) -> pd.DataFrame:
    """
    Calcula indices taticos 0-10 para todas as selecoes.

    Args:
        df_profiles: DataFrame com perfis (index=team), saida de profiles.py.

    Returns:
        DataFrame com colunas de indice para cada dimensao (index=team).
    """
    df = df_profiles.copy()
    result = pd.DataFrame(index=df.index)

    for dim in DIMENSIONS:
        col = dim["metric"]
        name = dim["name"]
        if col not in df.columns:
            logger.warning("Metrica ausente para dimensao '%s': %s", name, col)
            result[name] = float("nan")
            continue

        result[name] = _normalize_to_index(df[col], higher_is_better=dim["higher_is_better"])
        logger.debug(
            "Dimensao '%s': min=%.2f, max=%.2f, media=%.2f",
            name,
            result[name].min(),
            result[name].max(),
            result[name].mean(),
        )

    # Indice geral: media das dimensoes primarias (ataque + defesa + xG)
    primary_dims = ["forca_ofensiva", "solidez_defensiva", "qualidade_finalizacao"]
    result["indice_geral"] = result[primary_dims].mean(axis=1)

    return result


def save_team_json(
    team: str,
    profile_row: pd.Series,
    index_row: pd.Series,
    output_dir: Path = OUTPUT_DIR,
) -> None:
    """
    Salva o perfil completo de uma selecao como JSON.

    Args:
        team: Nome da selecao.
        profile_row: Linha do DataFrame de perfis (metricas brutas).
        index_row: Linha do DataFrame de indices (valores 0-10).
        output_dir: Diretorio de saida.
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    indices: dict = {}
    for dim in DIMENSIONS:
        name = dim["name"]
        indices[name] = {
            "label": dim["label"],
            "value": round(float(index_row.get(name, float("nan"))), 2),
            "description": dim["description"],
        }
    indices["indice_geral"] = {
        "label": "Índice Geral",
        "value": round(float(index_row.get("indice_geral", float("nan"))), 2),
        "description": "Media dos indices primarios (ataque, defesa, xG)",
    }

    raw: dict = {}
    for col in profile_row.index:
        v = profile_row[col]
        raw[col] = None if pd.isna(v) else round(float(v), 4)

    data = {
        "team": team,
        "indices": indices,
        "raw_profile": raw,
    }

    fname = team.replace(" ", "_").replace("/", "-") + ".json"
    path = output_dir / fname
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def generate_comparison_report(
    df_profiles: pd.DataFrame,
    df_indices: pd.DataFrame,
    output_path: Path,
) -> None:
    """
    Gera relatorio comparativo das 48 selecoes em Markdown.

    Args:
        df_profiles: DataFrame de metricas brutas (index=team).
        df_indices: DataFrame de indices 0-10 (index=team).
        output_path: Caminho do arquivo Markdown.
    """
    lines = [
        "# Perfis Táticos — Copa 2026",
        "",
        "Índices normalizados 0-10 para cada seleção. "
        "Base: percentis reais das 48 seleções classificadas.",
        "",
        "| Seleção | Índice Geral | Força Ofensiva | Solidez Def. | Qualidade xG | Domínio | Eficiência |",
        "|---|---|---|---|---|---|---|",
    ]

    df_sorted = df_indices.sort_values("indice_geral", ascending=False)

    for team in df_sorted.index:
        r = df_sorted.loc[team]
        lines.append(
            f"| {team} | {r.get('indice_geral', float('nan')):.1f} "
            f"| {r.get('forca_ofensiva', float('nan')):.1f} "
            f"| {r.get('solidez_defensiva', float('nan')):.1f} "
            f"| {r.get('qualidade_finalizacao', float('nan')):.1f} "
            f"| {r.get('dominio_territorial', float('nan')):.1f} "
            f"| {r.get('eficiencia_finalizacao', float('nan')):.1f} |"
        )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines), encoding="utf-8")
    logger.info("Relatorio comparativo salvo: %s", output_path)


if __name__ == "__main__":
    import logging as _logging
    _logging.basicConfig(level=_logging.INFO, format="%(levelname)s %(message)s")

    df_profiles = pd.read_parquet(DATA_PROCESSED / "team_profiles" / "perfis_v1.parquet")
    df_indices = build_indices(df_profiles)

    # Salva JSON por selecao
    for team in df_profiles.index:
        save_team_json(team, df_profiles.loc[team], df_indices.loc[team])
        _logging.getLogger(__name__).info("JSON salvo: %s", team)

    # Relatorio comparativo
    report_path = ROOT_DIR / "outputs" / "team_comparison_report.md"
    generate_comparison_report(df_profiles, df_indices, report_path)

    # Salva indices como parquet
    out_path = DATA_PROCESSED / "team_profiles" / "indices_v1.parquet"
    df_indices.to_parquet(out_path)
    _logging.getLogger(__name__).info("Indices salvos: %s", out_path)
