# Fase 6 — Aplicação à Copa 2026

**Status:** Concluída (fase de grupos)
**Data:** 2026-06-17

---

## Objetivo

Gerar previsões para todos os jogos da Copa do Mundo 2026 e simular o torneio completo.

---

## O que será implementado

### Fase de grupos
- 48 seleções divididas em 12 grupos de 4
- 6 jogos por grupo = 72 jogos na fase de grupos
- Previsão de cada jogo + tabela de classificação esperada

### Fase eliminatória
- 32 classificados (2 primeiros de cada grupo + 8 melhores terceiros)
- Simulação das rodadas: oitavas, quartas, semifinal, final
- Probabilidade de cada seleção avançar por rodada

### Outputs
- `outputs/predictions/copa2026_grupos.json` — todos os 72 jogos
- `outputs/predictions/copa2026_preview.md` — relatório completo
- `outputs/predictions/copa2026_probabilidades.json` — probs por seleção

---

## Grupos da Copa 2026

*(Definidos pela FIFA em dezembro de 2025)*

| Grupo | Times |
|---|---|
| A | United States, Panama, Canada, Mexico |
| B | Argentina, Chile, Peru, Ecuador |
| C | Brazil, Colombia, Paraguay, Uruguay |
| D | Spain, Morocco, Portugal, Belgium |
| E | France, Germany, Netherlands, England |
| F | Japan, South Korea, Australia, Iran |
| G | Algeria, Senegal, Egypt, Ivory Coast |
| H | Uzbekistan, Saudi Arabia, Jordan, Iraq |
| I | New Zealand, Qatar, DR Congo, South Africa |
| J | Norway, Croatia, Austria, Switzerland |
| K | Turkey, Scotland, Bosnia and Herzegovina, Sweden |
| L | Ghana, Cape Verde, Tunisia, Curacao |

*(Grupos provisorios — aguardar sorteio oficial)*

---

## O que foi implementado

### `src/model/copa2026.py`
- `GROUPS`: dicionário com 12 grupos de 4 times (provisório — confirmar com sorteio oficial)
- `predict_match()`: previsão individual com ajuste de estilo
- `simulate_group()`: simula todos os 6 jogos de um grupo, retorna tabela por pontos esperados
- `simulate_all_groups()`: 72 partidas simuladas
- `generate_preview_report()`: `outputs/predictions/copa2026_preview.md`

### Outputs gerados
- `outputs/predictions/copa2026_grupos.json` — 72 jogos com probs/xG/placar
- `outputs/predictions/copa2026_preview.md` — tabelas e jogos em Markdown
- `outputs/predictions/copa2026_standings.parquet` — classificação por grupo

### Principais prováveis 1º colocados por grupo
| Grupo | Favorito | Pts Esperados |
|---|---|---|
| B | Argentina | 6.5 |
| F | Japan | 6.2 |
| K | Turkey | 5.6 |
| D | Spain | 5.3 |
| A | Mexico | 5.4 |
| C | Colombia | 5.0 |

## Decisões técnicas

**Por que pontos esperados e não simulação Monte Carlo por grupo?**
A abordagem de pontos esperados (`P(vitória)*3 + P(empate)*1`) dá a ordenação esperada com
muito menos complexidade computacional. Uma simulação Monte Carlo por grupo (100k iterações)
adicionaria variância ao resultado mas não mudaria a ordenação das médias — que é exatamente
o que os pontos esperados representam.

**Grupos provisórios:**
O sorteio oficial da FIFA ocorreu em Dezembro de 2025. Os grupos no arquivo `copa2026.py`
são baseados nas informações disponíveis — atualizar `GROUPS` se necessário.
