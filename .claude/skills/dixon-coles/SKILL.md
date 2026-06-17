# SKILL: Modelo Dixon-Coles

## Quando usar
Use para estimar forca ofensiva e defensiva de cada selecao e gerar
lambda_A e lambda_B (xG esperado por lado) para um confronto.

## Por que Dixon-Coles
Corrige a subestimacao do Poisson simples em placares baixos (0x0, 1x0, 1x1)
usando parametro rho de correlacao. É o padrao em football analytics.

## Implementacao com penaltyblog
```python
import penaltyblog as pb

modelo = pb.models.DixonColesGoalModel(
    goals_home=df["goals_home"],
    goals_away=df["goals_away"],
    teams_home=df["team_home"],
    teams_away=df["team_away"],
    weights=df["peso_final"]   # peso_competicao * peso_temporal
)
modelo.fit()
```

## Camada simetrica de ajuste de estilo
Apos obter lambda_A e lambda_B, aplicar multiplicador de interacao:

MULTIPLICADORES = {
    ("high_press", "high_press"): 1.15,   # dois times de pressao -> xG alto
    ("low_block",  "low_block"):  0.85,   # dois blocos baixos -> xG baixo
    ("possession", "possession"): 0.95,   # posse vs posse -> ritmo lento
    ("high_press", "low_block"):  1.0,    # neutro
}

## Output esperado
{
    "team_a": "Brazil",
    "team_b": "France",
    "lambda_a": 1.74,
    "lambda_b": 1.21,
    "style_multiplier": 1.0,
    "model_version": "v1.0"
}
