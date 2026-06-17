# Fase 2 — Feature Engineering

**Status:** Concluída
**Data:** 2026-06-17

---

## Objetivo

Transformar as 2.152 partidas brutas em features ponderadas prontas para o modelo Dixon-Coles.
Cada seleção recebe um vetor de métricas ofensivas e defensivas ajustadas por:
1. Peso de competição (continental 1.2x, qualifier 1.0x, friendly 0.8x)
2. Decaimento temporal (meia-vida 730 dias)
3. Ponderação por Elo do adversário (aplicada por métrica individual)

---

## O que será implementado

### 2.1 — `src/engineering/weights.py`

Funções de cálculo de pesos:
- `calcular_peso_competicao(tipo)` → 1.2 | 1.0 | 0.8
- `calcular_peso_temporal(data_partida, data_referencia, meia_vida=730)` → [0, 1]
- `calcular_peso_final(peso_competicao, peso_temporal)` → produto dos dois

### 2.2 — `src/engineering/features.py`

Funções de ponderação por Elo e features derivadas:
- `ponderar_por_elo(metrica, elo_adversario, elo_media=1500)` → métrica ajustada
- `calcular_precisao_chutes(shots_on_target, shots_total)` → float
- `calcular_razao_dominio(shots_for, shots_against)` → float

### 2.3 — `src/engineering/profiles.py`

Agregação ponderada por seleção:
- Perfil ofensivo: gols, chutes, xG, precisão de finalização
- Perfil defensivo: gols sofridos, chutes concedidos
- Perfil de estilo: razão de domínio, escanteios
- Output: `data/processed/team_profiles/perfis_v1.parquet`

---

## O que foi implementado

### `src/engineering/weights.py`
- `calcular_peso_competicao(tipo)` → pesos fixados (1.2/1.0/0.8)
- `calcular_peso_temporal(data_partida, data_referencia, meia_vida=730)` → decaimento exponencial
- `calcular_peso_final(peso_competicao, peso_temporal)` → produto simples; Elo NOT aplicado aqui

### `src/engineering/features.py`
- `ponderar_por_elo(metrica, elo_adversario)` → fator = elo_media / elo_adversario
- `calcular_precisao_chutes(shots_on_target, shots_total)` → ratio [0,1]
- `calcular_razao_dominio(shots_for, shots_against)` → ratio [0,1]
- `add_weights(df)` → adiciona colunas peso_competicao, peso_temporal, peso_final
- `add_elo_adjusted_metrics(df)` → adiciona colunas *_adj para gols/xG/chutes
- `build_feature_matrix(df)` → pipeline completo

### `src/engineering/profiles.py`
- `build_team_profile(team_df)` → médias ponderadas por peso_final
- `build_all_profiles(df_features)` → itera 48 seleções
- Output: `data/processed/features/features_v1.parquet` + `data/processed/team_profiles/perfis_v1.parquet`

### `tests/test_engineering.py`
- 26 testes cobrindo todos os módulos (pesos, features, profiles)
- **Resultado:** 48/48 no total (22 anteriores + 26 novos)

---

## Decisões técnicas

**Por que `fator_ofensivo = elo_media / elo_adversario` e não o inverso?**

Para métricas *ofensivas* (gols marcados, xG for): marcar contra adversário forte (Elo alto) deve
ter mais peso. Fator < 1 quando adversário > média global. Isso equivale a "normalizar" o ataque
pela dificuldade enfrentada — um time que marca muito contra adversários de Elo 1800 tem ataque
mais forte do que um que marca a mesma quantidade contra adversários de Elo 1200.

Para métricas *defensivas* (gols sofridos, xG against): sofrer gol de adversário forte é menos
penalizado. Fator = elo_adversario / elo_media; quando adversário > média, fator > 1, fazendo
com que os gols sofridos pesem mais na contagem mas o *ajuste comparativo* seja menor.

**Por que precisão de chutes e razão de domínio NÃO são ajustadas por Elo?**

Essas métricas já são ratios intrinsecamente normalizados (valor entre 0 e 1). Aplicar fator
de Elo criaria distorções — um time que tem 60% de domínio contra adversário fraco ficaria
com "domínio ajustado" > 1.0, perdendo interpretabilidade.
