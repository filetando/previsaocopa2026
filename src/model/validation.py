"""
Backtest e validacao do modelo Dixon-Coles.

Estrategia: treina com dados excluindo os torneios de validacao,
preve cada jogo e compara com resultado real.
"""
import logging
from typing import Optional

import numpy as np
import pandas as pd
import penaltyblog

from src.engineering.features import build_feature_matrix
from src.model.dixon_coles import _prepare_training_data, train, prever_xg
from src.model.poisson import resumir_probabilidades
from src.utils.config import DATA_PROCESSED, ROOT_DIR

logger = logging.getLogger(__name__)

# Torneios StatsBomb para backtest (excluidos do treino, usados como teste)
VALIDATION_COMPETITIONS = {
    "copa_america_2024": "Copa America 2024",
    "euro_2024": "Euro 2024",
}

VALIDATION_REPORT_PATH = ROOT_DIR / "outputs" / "validation_report.md"


def _get_result_label(goals_a: int, goals_b: int) -> str:
    """Retorna 'win_a', 'draw' ou 'win_b' baseado no placar."""
    if goals_a > goals_b:
        return "win_a"
    elif goals_a == goals_b:
        return "draw"
    return "win_b"


def brier_score(
    probs: list[tuple[float, float, float]],
    results: list[str],
) -> float:
    """
    Calcula o Brier Score para previsoes de resultado (1X2).

    Args:
        probs: Lista de (prob_win_a, prob_draw, prob_win_b).
        results: Lista de 'win_a' | 'draw' | 'win_b'.

    Returns:
        Brier Score medio (0=perfeito, 1=pessimo, referencia aleatorio~0.33).
    """
    scores = []
    for (pa, pd_, pb), result in zip(probs, results):
        oa = 1.0 if result == "win_a" else 0.0
        od = 1.0 if result == "draw" else 0.0
        ob = 1.0 if result == "win_b" else 0.0
        scores.append(((pa - oa) ** 2 + (pd_ - od) ** 2 + (pb - ob) ** 2) / 3)
    return float(np.mean(scores))


def run_backtest(
    df_all: pd.DataFrame,
    holdout_sources: Optional[list[str]] = None,
    holdout_dates: Optional[tuple[str, str]] = None,
) -> pd.DataFrame:
    """
    Executa backtest treinando sem os dados de validacao.

    Args:
        df_all: DataFrame padronizado completo.
        holdout_sources: Fontes a excluir do treino (ex: ["statsbomb"]).
        holdout_dates: Tupla (data_inicio, data_fim) para definir periodo de teste.

    Returns:
        DataFrame com colunas team_a, team_b, goals_a, goals_b,
        lambda_a, lambda_b, prob_win_a, prob_draw, prob_win_b, result.
    """
    df_all = df_all.copy()
    df_all["date"] = pd.to_datetime(df_all["date"])

    # Define conjunto de treino: exclui partidas dos torneios de validacao
    # Criterio: Copa America 2024 e Euro 2024 (2024-06 a 2024-07)
    if holdout_dates:
        start_str, end_str = holdout_dates
        date_start = pd.Timestamp(start_str)
        date_end = pd.Timestamp(end_str)
        mask_holdout = (
            (df_all["source"] == "statsbomb") &
            (df_all["date"] >= date_start) &
            (df_all["date"] <= date_end)
        )
    else:
        # Padrao: excluir Copa America 2024 e Euro 2024
        mask_holdout = (
            (df_all["source"] == "statsbomb") &
            (df_all["date"] >= pd.Timestamp("2024-06-01")) &
            (df_all["date"] <= pd.Timestamp("2024-07-31"))
        )

    df_train = df_all[~mask_holdout]
    df_test = df_all[mask_holdout]

    logger.info(
        "Backtest: treino=%d partidas | teste=%d partidas",
        len(df_train), len(df_test),
    )

    # Treina modelo sem os dados de validacao
    df_features_train = build_feature_matrix(df_train)
    model = train(df_features_train)

    # Prepara dados de teste (1 linha por partida)
    test_matches = _prepare_training_data(df_test)
    logger.info("Partidas de teste (sem duplicatas): %d", len(test_matches))

    results: list[dict] = []

    for _, row in test_matches.iterrows():
        team_a = str(row["team_home"])
        team_b = str(row["team_away"])
        g_a = int(row["goals_home"])
        g_b = int(row["goals_away"])

        try:
            grid = model.predict(team_a, team_b, neutral_venue=True)
            lambda_a = float(grid.home_goal_expectation)
            lambda_b = float(grid.away_goal_expectation)
            prob_win_a = float(grid.home_win)
            prob_draw = float(grid.draw)
            prob_win_b = float(grid.away_win)
        except Exception as e:
            logger.warning("Falha ao prever %s vs %s: %s", team_a, team_b, str(e))
            continue

        result = _get_result_label(g_a, g_b)
        results.append({
            "team_a": team_a,
            "team_b": team_b,
            "goals_a": g_a,
            "goals_b": g_b,
            "lambda_a": round(lambda_a, 3),
            "lambda_b": round(lambda_b, 3),
            "prob_win_a": round(prob_win_a, 4),
            "prob_draw": round(prob_draw, 4),
            "prob_win_b": round(prob_win_b, 4),
            "result": result,
        })

    return pd.DataFrame(results)


def compute_metrics(df_results: pd.DataFrame) -> dict:
    """
    Calcula metricas de qualidade preditiva.

    Args:
        df_results: DataFrame retornado por run_backtest.

    Returns:
        Dicionario com brier_score, mae_xg, accuracy_best_score.
    """
    probs = list(zip(
        df_results["prob_win_a"],
        df_results["prob_draw"],
        df_results["prob_win_b"],
    ))
    bs = brier_score(probs, df_results["result"].tolist())

    # MAE do xG (lambda vs gols reais)
    mae_a = float(np.mean(np.abs(df_results["lambda_a"] - df_results["goals_a"])))
    mae_b = float(np.mean(np.abs(df_results["lambda_b"] - df_results["goals_b"])))
    mae_xg = (mae_a + mae_b) / 2

    # Acuracia do placar mais provavel
    # Para simplificar: verifica se o resultado mais provavel (win_a/draw/win_b) foi correto
    df = df_results.copy()
    df["predicted_result"] = df.apply(
        lambda r: "win_a" if r["prob_win_a"] >= r["prob_draw"] and r["prob_win_a"] >= r["prob_win_b"]
        else ("draw" if r["prob_draw"] >= r["prob_win_b"] else "win_b"),
        axis=1,
    )
    accuracy = float((df["predicted_result"] == df["result"]).mean())

    logger.info(
        "Metricas: Brier=%.4f (ref_aleatorio=0.333) | MAE_xG=%.3f | Accuracy=%.1f%%",
        bs, mae_xg, 100 * accuracy,
    )
    return {
        "brier_score": round(bs, 4),
        "mae_xg": round(mae_xg, 3),
        "accuracy_result": round(accuracy, 4),
        "n_partidas": len(df_results),
    }


def generate_validation_report(
    df_results: pd.DataFrame,
    metrics: dict,
) -> None:
    """
    Gera relatorio de validacao em Markdown.

    Args:
        df_results: DataFrame com resultados do backtest.
        metrics: Dicionario de metricas calculado por compute_metrics.
    """
    bs = metrics["brier_score"]
    mae = metrics["mae_xg"]
    acc = metrics["accuracy_result"]
    n = metrics["n_partidas"]

    brier_status = "APROVADO" if bs < 0.25 else "REPROVADO"

    lines = [
        "# Relatório de Validação — Modelo xG Copa 2026",
        "",
        "## Metodologia",
        "",
        "Backtest com exclusão temporal: treino com dados até Mai/2024, "
        "validação com Copa América 2024 e Euro 2024 (Jun-Jul 2024).",
        "",
        "## Métricas",
        "",
        f"| Métrica | Valor | Threshold | Status |",
        f"|---|---|---|---|",
        f"| Brier Score | {bs:.4f} | < 0.25 | {brier_status} |",
        f"| MAE xG | {mae:.3f} | — | — |",
        f"| Acurácia de Resultado | {100*acc:.1f}% | — | — |",
        f"| Partidas de teste | {n} | — | — |",
        "",
        "**Referência:** Brier Score aleatório (1/3 para cada resultado) ≈ 0.333",
        "",
        "## Top 10 Partidas por Confiança",
        "",
        "| Time A | Time B | Gols A | Gols B | λA | λB | P(A) | P(X) | P(B) | Resultado |",
        "|---|---|---|---|---|---|---|---|---|---|",
    ]

    # Ordena por maior probabilidade maxima (previsoes mais confiantes)
    df_sorted = df_results.copy()
    df_sorted["max_prob"] = df_sorted[["prob_win_a", "prob_draw", "prob_win_b"]].max(axis=1)
    df_sorted = df_sorted.sort_values("max_prob", ascending=False).head(10)

    for _, r in df_sorted.iterrows():
        lines.append(
            f"| {r['team_a']} | {r['team_b']} | {r['goals_a']} | {r['goals_b']} "
            f"| {r['lambda_a']:.2f} | {r['lambda_b']:.2f} "
            f"| {r['prob_win_a']:.2f} | {r['prob_draw']:.2f} | {r['prob_win_b']:.2f} "
            f"| {r['result']} |"
        )

    VALIDATION_REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    VALIDATION_REPORT_PATH.write_text("\n".join(lines), encoding="utf-8")
    logger.info("Relatorio de validacao salvo: %s", VALIDATION_REPORT_PATH)


if __name__ == "__main__":
    import logging as _logging
    _logging.basicConfig(level=_logging.INFO, format="%(levelname)s %(message)s")

    df_all = pd.read_parquet(DATA_PROCESSED / "matches" / "partidas_padronizadas_v1.parquet")

    df_results = run_backtest(df_all)
    metrics = compute_metrics(df_results)
    generate_validation_report(df_results, metrics)

    print("\n=== RESULTADO DA VALIDAÇÃO ===")
    for k, v in metrics.items():
        print(f"  {k}: {v}")
