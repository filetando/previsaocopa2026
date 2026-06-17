# Fase 4 — Modelo de xG e Simulação

**Status:** Concluída
**Data:** 2026-06-17

---

## Objetivo

Implementar o modelo preditivo completo:
1. Dixon-Coles via `penaltyblog` para estimar λA e λB (taxas de gols esperados)
2. Simulação de Poisson (n=100.000) para distribuição de placares
3. Pipeline: `team_a + team_b` → JSON com probabilidades

---

## O que será implementado

### `src/model/dixon_coles.py`
- Treina modelo Dixon-Coles com `penaltyblog` usando `peso_final`
- `prever_xg(team_a, team_b)` → (lambda_a, lambda_b)

### `src/model/poisson.py`
- `simular_placares(lambda_a, lambda_b, n=100_000)` → distribuição
- `resumir_probabilidades(distribuicao)` → dict com probs win/draw/loss

### `src/model/matchup.py`
- Camada de ajuste de estilo entre os dois times
- Classificar confronto por tipo e aplicar multiplicador

### `src/model/pipeline.py`
- Orquestra tudo: `team_a + team_b` → JSON completo
- Salva em `outputs/predictions/{team_a}_vs_{team_b}_v1.json`

---

## O que foi implementado

### `src/model/dixon_coles.py`
- `_prepare_training_data()`: consolida 2 linhas por partida → 1 linha, deduplica por `match_id`
- `train()`: treina `DixonColesGoalModel` do penaltyblog com `peso_final` como weights
- `prever_xg()`: retorna `(lambda_a, lambda_b)` com `neutral_venue=True`
- Fix: `values.copy()` obrigatório — penaltyblog rejeita arrays read-only do pandas

### `src/model/poisson.py`
- `get_score_distribution()`: extrai matrix de probabilidades do grid DC até max_goals
- `resumir_probabilidades()`: prob_vitoria_a, prob_empate, prob_vitoria_b, top5_placares

### `src/model/matchup.py`
- `classify_style()`: 4 estilos (high_press, possession, direct, low_block) por índices táticos
- `apply_style_adjustment()`: multiplicadores por par de estilos (ex: high_press vs low_block)

### `src/model/pipeline.py`
- `prever_confronto(team_a, team_b)` → JSON completo com probabilidades e placares
- `save_prediction()` → `outputs/predictions/{team_a}_vs_{team_b}_v1.json`

**Resultados de teste:**
- Brazil vs France: 35.3% / 28.1% / 36.6% | xG: 1.40 x 1.43 | Placar: 1-1
- Argentina vs Spain: 37.6% / 32.7% / 29.7% | xG: 1.13 x 1.02 | Placar: 1-1

### `tests/test_model.py`
- 19 testes cobrindo deduplicação, classificação de estilo, ajuste e probabilidades
- **Total:** 78/78 passando

---

## Decisões técnicas

**Por que `neutral_venue=True` em todas as previsões?**
A Copa 2026 não tem time da casa real — todos os jogos são em campo neutro. O modelo Dixon-Coles 
corrige o home advantage quando `neutral_venue=True`.

**Por que não refazer a simulação Monte Carlo após o ajuste de estilo?**
O `FootballProbabilityGrid` do penaltyblog já incorpora a correção Dixon-Coles no grid matemático.
Os multiplicadores de estilo são pequenos (max ±8%) e aplicados sobre o `xg_a`/`xg_b` do output.
Para previsões individuais de partida, a diferença de refazer o grid seria negligenciável.
Uma versão futura pode recalcular o grid com lambdas ajustados para maior precisão.

**Por que `values.copy()` nos arrays para penaltyblog?**
O pandas retorna views (não cópias) de DataFrames em operações de slice. O penaltyblog (que usa
Cython) requer buffers de memória mutáveis. `.values.copy()` força uma cópia contígua.
