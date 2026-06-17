# SKILL: Ponderacao por Elo do Adversario

## Quando usar
Use na feature engineering para ponderar metricas brutas pelo nivel do adversario.
SEMPRE usar Elo historico (data da partida), NUNCA o Elo atual.

## Fonte canonica: eloratings.net
# ATENCAO: soccerdata.ClubElo() e para clubes, NAO para selecoes nacionais.
# Usar eloratings.net diretamente via src/collection/elo_collector.py.

## Como carregar Elo historico
```python
import pandas as pd
from datetime import datetime
from src.utils.config import DATA_RAW

def obter_elo_na_data(team: str, date: datetime) -> float:
    """Retorna o Elo da selecao na data da partida (ou mais proximo anterior)."""
    historico = pd.read_parquet(DATA_RAW / "elo" / "elo_historico.parquet")
    team_df = historico[historico["team"] == team].copy()
    team_df = team_df[team_df["date"] <= pd.Timestamp(date)]
    return float(team_df.sort_values("date").iloc[-1]["elo"])
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
