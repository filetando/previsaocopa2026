# SKILL: Extracao de Dados StatsBomb

## Quando usar
Use para coletar dados do StatsBomb Open Data e derivar metricas agregadas por partida.

## Competicoes internacionais masculinas disponíveis
copa_america_2024:  competition_id=223, season_id=282
euro_2024:          competition_id=55,  season_id=282
afcon_2023:         competition_id=1267, season_id=107
world_cup_2022:     competition_id=43,  season_id=106
world_cup_2018:     competition_id=43,  season_id=3
euro_2020:          competition_id=55,  season_id=43

## Fluxo basico
```python
from statsbombpy import sb

competicoes = sb.competitions()
partidas = sb.matches(competition_id=223, season_id=282)
eventos = sb.events(match_id=partida_id)

# xG: somar shot_statsbomb_xg de todos os chutes (excluir penalties)
chutes = eventos[eventos["type"] == "Shot"]
xg = chutes[chutes["shot_type"] != "Penalty"]["shot_statsbomb_xg"].sum()

# Chutes no alvo: outcome == "Saved" ou "Goal"
no_alvo = chutes[chutes["shot_outcome"].isin(["Saved", "Goal"])]
```

## Metricas derivaveis
- xg_for / xg_against
- shots_for / shots_against
- shots_on_target_for / shots_on_target_against
- corners_for / corners_against (eventos de tipo Corner Awarded)
- ppda (passes permitidos por acao defensiva no campo de ataque)

## Output
Salvar em data/raw/statsbomb/{competicao}.parquet com schema universal.
data_quality = "high" para todos os dados StatsBomb.
