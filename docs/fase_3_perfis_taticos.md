# Fase 3 — Perfis Táticos por Seleção

**Status:** Concluída
**Data:** 2026-06-17

---

## Objetivo

Transformar as métricas brutas ponderadas (saída da Fase 2) em índices táticos
normalizados de 0 a 10 para cada uma das 48 seleções, facilitando interpretação
e alimentando a camada de ajuste de estilos do modelo (Fase 4).

---

## O que será implementado

### `src/model/team_indexer.py`

Normaliza cada dimensão para escala 0-10 usando percentis reais das 48 seleções:
- **Força ofensiva** — gols_marcados_adj normalizado
- **Solidez defensiva** — inverso de gols_sofridos_adj normalizado
- **Qualidade de finalização** — xg_for_adj normalizado
- **Dominío territorial** — razao_dominio normalizado
- **Eficiência de finalização** — precisao_finalizacao normalizado

### `outputs/team_profiles/{team}.json`

48 arquivos JSON com índices por seleção.

---

## O que foi implementado

### `src/model/team_indexer.py`

7 dimensões táticas normalizadas:
| Dimensão | Métrica base | Direção |
|---|---|---|
| `forca_ofensiva` | gols_marcados_adj | maior = melhor |
| `solidez_defensiva` | gols_sofridos_adj | menor = melhor |
| `qualidade_finalizacao` | xg_for_adj | maior = melhor |
| `dominio_territorial` | razao_dominio | maior = melhor |
| `eficiencia_finalizacao` | precisao_finalizacao | maior = melhor |
| `volume_ataque` | chutes_for_adj | maior = melhor |
| `solidez_xg` | xg_against_adj | menor = melhor |

Outputs:
- `outputs/team_profiles/{team}.json` — 48 arquivos com índices e métricas brutas
- `outputs/team_comparison_report.md` — ranking comparativo das 48 seleções
- `data/processed/team_profiles/indices_v1.parquet`

### `tests/test_team_indexer.py`
- 11 testes cobrindo normalização, tratamento de NaN e ordenação por dimensão
- **Total:** 59/59 passando

---

## Decisões técnicas

**Por que percentis em vez de min-max?**
Min-max é sensível a outliers (um time com desempenho muito superior distorce todos os outros). 
Percentis são robustos: um time "dominante" recebe 10, os demais se distribuem pelos percentis 
reais — a distância relativa entre times adjacentes é preservada.

**Por que `na_option='keep'` em vez de `na_option='bottom'`?**
No pandas, `na_option='bottom'` atribui o MAIOR rank aos NaN (tratado como "pior no ranking" 
mas com o maior número de rank). Resultado: com `pct=True`, NaN ficava com percentil ~1.0, 
recebendo índice ~10 erroneamente. A correção usa `na_option='keep'`, que mantém NaN como NaN 
— times sem dados de xG/chutes não recebem pontuação nessas dimensões.

**`indice_geral` com dados faltantes:**
Calculado como `mean(axis=1)` das 3 dimensões primárias (ataque, defesa, xG). O pandas 
`mean(axis=1)` ignora NaN por padrão (`skipna=True`), então times sem xG recebem índice 
geral baseado apenas em ataque e defesa. Isso é mais justo do que impor um valor neutro.
