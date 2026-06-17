"""
Simulacao da Copa do Mundo 2026.

Grupos oficiais conforme sorteio FIFA (Dezembro 2025).
Sede: EUA, Canada e Mexico | 11 Jun - 19 Jul 2026 | 48 selecoes.
"""
import json
import logging
from itertools import combinations
from pathlib import Path

import pandas as pd

from src.model.dixon_coles import load_model, prever_xg
from src.model.matchup import apply_style_adjustment, classify_style
from src.model.poisson import resumir_probabilidades
from src.utils.config import DATA_PROCESSED, ROOT_DIR

logger = logging.getLogger(__name__)

PREDICTIONS_DIR = ROOT_DIR / "outputs" / "predictions"

# Grupos oficiais da Copa 2026 (sorteio FIFA, Dezembro 2025)
GROUPS: dict[str, list[str]] = {
    "A": ["Mexico", "South Africa", "South Korea", "Czechia"],
    "B": ["Canada", "Qatar", "Switzerland", "Bosnia and Herzegovina"],
    "C": ["Brazil", "Morocco", "Haiti", "Scotland"],
    "D": ["United States", "Paraguay", "Australia", "Turkey"],
    "E": ["Germany", "Curacao", "Ivory Coast", "Ecuador"],
    "F": ["Netherlands", "Japan", "Tunisia", "Sweden"],
    "G": ["Belgium", "Egypt", "Iran", "New Zealand"],
    "H": ["Spain", "Cape Verde", "Saudi Arabia", "Uruguay"],
    "I": ["France", "Senegal", "Norway", "Iraq"],
    "J": ["Argentina", "Algeria", "Austria", "Jordan"],
    "K": ["Portugal", "Uzbekistan", "Colombia", "DR Congo"],
    "L": ["England", "Croatia", "Ghana", "Panama"],
}


def _load_indices() -> pd.DataFrame:
    """Carrega indices taticos para classificacao de estilo."""
    path = DATA_PROCESSED / "team_profiles" / "indices_v1.parquet"
    if not path.exists():
        return pd.DataFrame()
    return pd.read_parquet(path)


def predict_match(
    model,
    team_a: str,
    team_b: str,
    indices: pd.DataFrame,
) -> dict:
    """
    Gera previsao para uma partida em campo neutro.

    Args:
        model: Modelo Dixon-Coles treinado.
        team_a: Nome do time A.
        team_b: Nome do time B.
        indices: DataFrame de indices taticos.

    Returns:
        Dicionario com probabilidades e xG.
    """
    try:
        grid = model.predict(team_a, team_b, neutral_venue=True)
        lambda_a = float(grid.home_goal_expectation)
        lambda_b = float(grid.away_goal_expectation)

        # Ajuste de estilo
        style_a = classify_style(indices.loc[team_a] if team_a in indices.index else None)
        style_b = classify_style(indices.loc[team_b] if team_b in indices.index else None)
        lambda_a_adj, lambda_b_adj = apply_style_adjustment(lambda_a, lambda_b, style_a, style_b)

        resumo = resumir_probabilidades(grid, "a", "b")
        resumo["xg_a"] = round(lambda_a_adj, 3)
        resumo["xg_b"] = round(lambda_b_adj, 3)

        return {
            "team_a": team_a,
            "team_b": team_b,
            "prob_win_a": resumo["prob_vitoria_a"],
            "prob_draw": resumo["prob_empate"],
            "prob_win_b": resumo["prob_vitoria_b"],
            "xg_a": resumo["xg_a"],
            "xg_b": resumo["xg_b"],
            "placar_mais_provavel": resumo["placar_mais_provavel"]["placar"],
            "style_a": style_a,
            "style_b": style_b,
        }
    except Exception as e:
        logger.warning("Falha ao prever %s vs %s: %s", team_a, team_b, str(e))
        return {
            "team_a": team_a, "team_b": team_b,
            "prob_win_a": 1/3, "prob_draw": 1/3, "prob_win_b": 1/3,
            "xg_a": None, "xg_b": None,
            "placar_mais_provavel": "?-?",
            "style_a": "direct", "style_b": "direct",
            "error": str(e),
        }


def simulate_group(
    group_name: str,
    teams: list[str],
    model,
    indices: pd.DataFrame,
) -> tuple[list[dict], pd.DataFrame]:
    """
    Simula todos os jogos de um grupo e retorna a tabela classificatoria.

    Args:
        group_name: Letra do grupo (ex: 'A').
        teams: Lista de 4 times do grupo.
        model: Modelo Dixon-Coles.
        indices: DataFrame de indices taticos.

    Returns:
        Tupla (lista de partidas, DataFrame de classificacao).
    """
    matches = []
    standings = {t: {"pts": 0, "gf": 0.0, "ga": 0.0, "mp": 0} for t in teams}

    for team_a, team_b in combinations(teams, 2):
        result = predict_match(model, team_a, team_b, indices)
        result["group"] = group_name
        matches.append(result)

        # Atualiza tabela com base nas probabilidades esperadas
        # Pontos esperados: P(win)*3 + P(draw)*1
        pts_a = result["prob_win_a"] * 3 + result["prob_draw"] * 1
        pts_b = result["prob_win_b"] * 3 + result["prob_draw"] * 1

        standings[team_a]["pts"] += pts_a
        standings[team_b]["pts"] += pts_b
        standings[team_a]["mp"] += 1
        standings[team_b]["mp"] += 1

        if result["xg_a"] and result["xg_b"]:
            standings[team_a]["gf"] += result["xg_a"]
            standings[team_a]["ga"] += result["xg_b"]
            standings[team_b]["gf"] += result["xg_b"]
            standings[team_b]["ga"] += result["xg_a"]

    df_standings = pd.DataFrame([
        {"team": t, "group": group_name, **v}
        for t, v in standings.items()
    ]).sort_values("pts", ascending=False).reset_index(drop=True)
    df_standings["rank"] = range(1, 5)
    df_standings["gd"] = df_standings["gf"] - df_standings["ga"]

    return matches, df_standings


def simulate_all_groups(model, indices: pd.DataFrame) -> tuple[list[dict], pd.DataFrame]:
    """
    Simula todos os 12 grupos da Copa 2026.

    Returns:
        Tupla (lista com 72 partidas, DataFrame com classificacao de todos os grupos).
    """
    all_matches = []
    all_standings = []

    for group_name, teams in GROUPS.items():
        logger.info("Simulando Grupo %s: %s", group_name, ", ".join(teams))
        matches, standings = simulate_group(group_name, teams, model, indices)
        all_matches.extend(matches)
        all_standings.append(standings)

    df_all_standings = pd.concat(all_standings, ignore_index=True)
    return all_matches, df_all_standings


def generate_preview_report(
    all_matches: list[dict],
    df_standings: pd.DataFrame,
) -> None:
    """Gera relatorio Markdown com previsoes da fase de grupos."""
    lines = [
        "# Previsões Copa do Mundo 2026",
        "",
        f"**Modelo:** Dixon-Coles + Poisson | **Data:** 2026-06-17",
        f"**Dados:** 2.152 partidas | 48 seleções | Brier Score validado: 0.1995",
        "",
        "---",
        "",
        "## Tabelas dos Grupos (Pontos Esperados)",
        "",
    ]

    for group_name in sorted(GROUPS.keys()):
        group_df = df_standings[df_standings["group"] == group_name]
        lines.append(f"### Grupo {group_name}")
        lines.append("")
        lines.append("| Pos | Seleção | Pts | GF | GA | Saldo |")
        lines.append("|---|---|---|---|---|---|")
        for _, row in group_df.iterrows():
            lines.append(
                f"| {int(row['rank'])} | {row['team']} | {row['pts']:.1f} "
                f"| {row['gf']:.1f} | {row['ga']:.1f} | {row['gd']:+.1f} |"
            )
        lines.append("")

    lines += [
        "---",
        "",
        "## Todos os Jogos — Fase de Grupos",
        "",
        "| Grupo | Time A | P(A) | P(X) | P(B) | Time B | xGA | xGB | Placar |",
        "|---|---|---|---|---|---|---|---|---|",
    ]

    for m in sorted(all_matches, key=lambda x: x["group"]):
        xga = f"{m['xg_a']:.2f}" if m.get("xg_a") else "—"
        xgb = f"{m['xg_b']:.2f}" if m.get("xg_b") else "—"
        lines.append(
            f"| {m['group']} | {m['team_a']} | {m['prob_win_a']:.0%} "
            f"| {m['prob_draw']:.0%} | {m['prob_win_b']:.0%} "
            f"| {m['team_b']} | {xga} | {xgb} | {m['placar_mais_provavel']} |"
        )

    PREDICTIONS_DIR.mkdir(parents=True, exist_ok=True)
    out_path = PREDICTIONS_DIR / "copa2026_preview.md"
    out_path.write_text("\n".join(lines), encoding="utf-8")
    logger.info("Preview salvo: %s", out_path)


if __name__ == "__main__":
    import logging as _logging
    _logging.basicConfig(level=_logging.INFO, format="%(levelname)s %(message)s")

    model = load_model()
    indices = _load_indices()

    all_matches, df_standings = simulate_all_groups(model, indices)

    # Salva JSON com partidas
    PREDICTIONS_DIR.mkdir(parents=True, exist_ok=True)
    json_path = PREDICTIONS_DIR / "copa2026_grupos.json"
    json_path.write_text(
        json.dumps(all_matches, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    _logging.getLogger(__name__).info("JSON salvo: %s", json_path)

    # Salva classificacoes
    df_standings.to_parquet(PREDICTIONS_DIR / "copa2026_standings.parquet", index=False)

    # Gera relatorio
    generate_preview_report(all_matches, df_standings)

    # Resumo dos favoritos
    print("\n=== TOP 10 PROVÁVEIS CLASSIFICADOS (1º DO GRUPO) ===")
    top = df_standings[df_standings["rank"] == 1].sort_values("pts", ascending=False)
    for _, r in top.head(10).iterrows():
        print(f"  Grupo {r['group']}: {r['team']} ({r['pts']:.1f} pts esp.)")
