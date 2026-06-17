# Fase 5 — Validação e Calibração

**Status:** Concluída — APROVADA
**Data:** 2026-06-17

---

## Objetivo

Validar o modelo com backtest nos torneios StatsBomb (dados reais conhecidos)
e calcular métricas de qualidade preditiva.

---

## O que será implementado

### Backtest
- Treinar com dados excluindo Copa América 2024 e Euro 2024
- Prever todos os jogos desses torneios
- Comparar probabilidades previstas com resultados reais

### Métricas
- **Brier Score**: média de (prob_prevista - resultado_real)² por partida
- **MAE do xG**: erro médio absoluto entre xG previsto e gols reais
- **Acurácia de placar**: % de partidas com placar mais provável correto

---

## Resultados

| Métrica | Valor | Threshold | Status |
|---|---|---|---|
| Brier Score | **0.1995** | < 0.25 | **APROVADO** |
| MAE xG | 0.839 | — | — |
| Acurácia de Resultado | 53.7% | — | — |
| Partidas de teste | 54 | — | — |

Referência: Brier Score aleatório ≈ 0.333. O modelo atingiu 0.1995 (~40% melhor que aleatório).

**Partidas excluídas do teste**: 29 de 83 envolviam seleções fora das 48 classificadas (Albânia, Geórgia, Bolívia, Jamaica etc.) — esperado, pois o modelo só conhece times com dados de treino.

## O que foi implementado

### `src/model/validation.py`
- `run_backtest()`: treina com dados até Mai/2024, testa em Jun-Jul/2024
- `brier_score()`: métrica de calibração probabilística (0=perfeito, 0.333=aleatório)
- `compute_metrics()`: Brier, MAE xG e acurácia de resultado
- `generate_validation_report()`: `outputs/validation_report.md`

### `tests/test_validation.py`
- 12 testes cobrindo Brier Score, labels de resultado e métricas
- **Total:** 90/90 passando

## Decisões técnicas

**Por que backtest temporal e não k-fold?**
K-fold misturaria dados futuros com passado no treino, criando vazamento. O backtest temporal
(treino antes de Jun/2024, teste em Jun-Jul/2024) simula exatamente o uso real do modelo.

**Por que 54 e não 83 partidas de teste?**
29 partidas envolviam times não classificados para a Copa 2026 (Albânia, Geórgia, Croácia,
Sérvia, Eslováquia, etc.). O modelo só pode prever times que apareçam no treino. Isso é
comportamento correto — na Copa 2026 só preveremos confrontos entre as 48 classificadas.

**Acurácia de 53.7%:**
Acima do baseline de 33.3% (aleatório). Para previsão de futebol, acurácia de 50-55% é
considerada competitiva — a imprevisibilidade inerente do esporte mantém qualquer modelo
abaixo de 60% em dados fora do treino.
