# Fase 1 — Coleta de Dados Brutos

**Status:** Parcialmente concluída (1A e 1B completas; 1C, 1D e 1E pendentes)
**Data:** 2026-06-17

---

## O que foi implementado

### 1A — StatsBomb Open Data (`src/collection/statsbomb_collector.py`)

Coleta eventos de competições internacionais disponíveis gratuitamente via `statsbombpy`.

**Competições coletadas:**
| Competição | Partidas | Linhas (2 por partida) |
|---|---|---|
| Copa América 2024 | 32 | 64 |
| Euro 2024 | 51 | 102 |
| AFCON 2023 | 52 | 104 |
| World Cup 2022 | 64 | 128 |
| Euro 2020 | 51 | 102 |

**Métricas extraídas por partida e por time:**
- `xg_for` / `xg_against` — soma de `shot_statsbomb_xg`, excluindo pênaltis
- `shots_for` / `shots_against` — contagem de eventos do tipo "Shot"
- `shots_on_target_for` / `shots_on_target_against` — chutes com outcome "Saved" ou "Goal"
- `corners_for` / `corners_against` — passes com `pass_type == "Corner"`
- `goals_scored` / `goals_conceded` — do placar oficial da partida

**Decisões técnicas:**
- `venue = "neutral"` para todos os dados StatsBomb: torneios continentais não têm mando de campo real.
- `elo_team` e `elo_opponent` ficam `None` no coletor bruto e são preenchidos pelo standardizer (Fase 1E), evitando que o dado histórico vaze para a coleta.
- `data_quality = "high"` para todos os dados StatsBomb (fonte gold standard com xG confiável).
- World Cup 2022 incluída mesmo fora da janela de 3 anos: o decaimento temporal (`meia-vida=730 dias`) desconta naturalmente partidas mais antigas, então não há motivo para descartar dados adicionais na coleta.
- Warnings do `statsbombpy` ("No auth") suprimidos pois o projeto usa apenas Open Data.

**Problema encontrado:** O `soccerdata.ClubElo()` referenciado na SKILL original é para **clubes**, não seleções. Corrigido na SKILL.md para usar `eloratings.net`.

---

### 1B — Elo Histórico (`src/collection/elo_collector.py`)

Coleta o histórico de ratings Elo de todas as 48 seleções classificadas para a Copa 2026 diretamente do `eloratings.net`.

**Resultado:** 48/48 seleções cobertas | 34.158 registros | `data/raw/elo/elo_historico.parquet`

**Formato do TSV do eloratings.net (16 colunas sem cabeçalho):**
```
[year, month, day, team1_code, team2_code, goals1, goals2, comp,
 ?, elo_change_t1, elo_after_t1, elo_after_t2, ...]
```
- `elo_after_t1` (col 10): Elo do Team1 após a partida
- `elo_after_t2` (col 11): Elo do Team2 após a partida
- O código do time do arquivo é detectado automaticamente via `_detectar_codigo_time()` (o código que aparece em todas as linhas)

**Decisões técnicas:**

*Por que eloratings.net e não soccerdata.ClubElo?*
- `clubelo.com` é para clubes; `eloratings.net` é a fonte canônica para **seleções nacionais**.
- `api.clubelo.com` estava inacessível durante o desenvolvimento.
- `eloratings.net` retornou 200 com dados históricos completos via requests padrão.

*Por que histórico por time e não apenas rating atual?*
- A regra fundamental do projeto: usar sempre o Elo **na data da partida**, nunca o atual.
- O arquivo `{team}.tsv` do eloratings.net contém o Elo após cada partida ao longo de décadas.
- A função `get_elo_on_date()` busca o registro mais recente **antes ou igual** à data da partida.

*United States sem TSV dedicado:*
- `eloratings.net` não disponibiliza arquivo `United-States.tsv` (várias variações testadas retornaram 404).
- Solução: `_extract_from_opponents()` — extrai o Elo dos EUA a partir dos arquivos do México e Canadá, onde a coluna `elo_after_t2` contém o Elo dos EUA quando eles aparecem como "visitante".
- Bug corrigido: a versão inicial não adicionava o campo `team` ao DataFrame extraído via adversários, gerando um registro com `team=NaN` no parquet.

**Slugs descobertos para times com nomes compostos:**
- `South Korea` → `South_Korea` (underscore, não hífen)
- `DR Congo` → `DR_Congo`
- `Ivory Coast` → `Ivory_Coast`
- `Bosnia and Herzegovina` → `Bosnia_and_Herzegovina`
- `Saudi Arabia` → `Saudi_Arabia`
- `Cape Verde` → `Cape_Verde`
- `South Africa` → `South_Africa`

---

### Lista de Seleções (`src/collection/teams.py`)

**Problema:** A lista inicial continha vários países errados (Venezuela, Sérvia, Dinamarca, Camarões, Nigéria, Honduras, etc.). A lista correta das 48 classificadas foi confirmada via documento oficial.

**Mudanças da lista inicial para a final:**
- **Removidos:** Venezuela, Sérvia, Dinamarca, Eslovênia, Eslováquia, Nigéria, Camarões, Honduras, Costa Rica, Mali
- **Adicionados:** Paraguai, Bélgica, Bósnia e Herzegovina, Noruega, Suécia, Catar, África do Sul, Cabo Verde, Curaçao, Haiti, República Tcheca (como "Czechia" no sistema)

**Estrutura do arquivo:**
- `ELO_URL_SLUG`: mapeia nome do time → slug da URL do eloratings.net (`None` para USA)
- `COPA_2026_TEAMS`: lista derivada das chaves do dicionário acima
- `STATSBOMB_NAME_MAP`: mapeia nomes StatsBomb → nome padrão do projeto (ex: "Côte d'Ivoire" → "Ivory Coast")

---

## Pendente (1C, 1D, 1E)

| Tarefa | Descrição |
|---|---|
| 1C | SofaScore — qualificatórias e amistosos (cobertura das seleções sem dados StatsBomb) |
| 1D | football-data.org — fallback para times sem cobertura SofaScore |
| 1E | Standardizer — unifica todas as fontes, adiciona `elo_team`/`elo_opponent` por partida, gera `coverage_report.md` |

---

## Testes implementados

- `tests/test_statsbomb_collector.py` — 7 testes cobrindo extração de xG, chutes, escanteios, pênaltis e eventos vazios
- `tests/test_elo_collector.py` — 6 testes cobrindo detecção de código, parsing histórico, ordenação por data e lookup por data
- **Resultado:** 13/13 passando
