# SKILL: Ponderacao por Elo do Adversario

## Quando usar
Use na feature engineering para ponderar metricas brutas pelo nivel do adversario.
SEMPRE usar Elo historico (data da partida), NUNCA o Elo atual.

## Como carregar Elo historico
```python
import soccerdata as sd
from datetime import datetime

def obter_elo_na_data(team: str, date: datetime) -> float:
    elo = sd.ClubElo()
    historico = elo.read_by_team(team)
    registro = historico[historico.index <= date].iloc[-1]
    return float(registro["elo"])
```

## Formula de ponderacao
ELO_MEDIA_GLOBAL = 1500  # referencia do src/utils/config.py

```python
def ponderar_por_elo(metrica: float, elo_adversario: float) -> float:
    fator = elo_adversario / ELO_MEDIA_GLOBAL
    return metrica * fator
```

## Aplicacao na tabela
```python
for col in ["goals_scored", "shots_for", "shots_on_target_for", "corners_for"]:
    df[f"{col}_elo_weighted"] = df[col] * (df["elo_opponent"] / ELO_MEDIA_GLOBAL)

for col in ["goals_conceded", "shots_against", "shots_on_target_against"]:
    df[f"{col}_elo_weighted"] = df[col] * (df["elo_opponent"] / ELO_MEDIA_GLOBAL)
```

## Importante
- Aplicar DEPOIS de peso_competicao e peso_temporal
- A ponderacao Elo e por metrica, nao por peso da partida
- Documentar distribuicao de Elo dos adversarios por selecao
