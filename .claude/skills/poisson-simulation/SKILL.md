# SKILL: Simulacao de Poisson - Distribuicao de Placares

## Quando usar
Use apos o Dixon-Coles gerar lambda_A e lambda_B para converter xG esperado
em distribuicao completa de placares provaveis.

## Implementacao
```python
import numpy as np
import pandas as pd

def simular_placares(
    lambda_a: float,
    lambda_b: float,
    n_simulacoes: int = 100_000
) -> pd.DataFrame:
    gols_a = np.random.poisson(lambda_a, n_simulacoes)
    gols_b = np.random.poisson(lambda_b, n_simulacoes)

    df = pd.DataFrame({"gols_a": gols_a, "gols_b": gols_b})
    dist = df.groupby(["gols_a", "gols_b"]).size().reset_index(name="contagem")
    dist["probabilidade"] = dist["contagem"] / n_simulacoes
    dist["resultado"] = dist.apply(
        lambda r: "vitoria_a" if r.gols_a > r.gols_b
                  else ("vitoria_b" if r.gols_b > r.gols_a else "empate"),
        axis=1
    )
    return dist.sort_values("probabilidade", ascending=False)
```

## Output JSON por confronto
{
    "team_a": "Brazil",
    "team_b": "France",
    "lambda_a": 1.74,
    "lambda_b": 1.21,
    "probabilidades": {
        "vitoria_a": 0.48,
        "empate": 0.24,
        "vitoria_b": 0.28
    },
    "placar_mais_provavel": {"gols_a": 2, "gols_b": 1},
    "top_5_placares": [...],
    "metadata": {
        "n_simulacoes": 100000,
        "model_version": "v1.0",
        "generated_at": "2026-06-16"
    }
}

## Salvar em
outputs/predictions/{team_a}_vs_{team_b}_v1.json
