# Copa 2026 — Modelo Preditivo de xG

## Objetivo
Modelo estatístico para prever xG de cada seleção em confrontos da Copa do Mundo 2026,
gerando distribuição de placares via simulação de Poisson (Dixon-Coles).

## Stack
- Python 3.11+ | pandas | numpy | scipy | statsbombpy | soccerdata | penaltyblog
- Dados: StatsBomb Open Data, SofaScore, eloratings.net, football-data.org

## Arquitetura do modelo
1. Coleta de dados brutos (3 anos: 2023-2026)
2. Feature engineering com pesos de competicao e decaimento temporal
3. Ponderacao por Elo do adversario
4. Modelo assimetrico: xG_A = f(ataque_A, defesa_B)
5. Camada simetrica de ajuste de estilos
6. Simulacao Dixon-Coles -> Poisson -> distribuicao de placares

## Decisoes fixadas (nao renegociar)
- Pesos de competicao: Copa Continental 1.2x | Eliminatorias 1.0x | Amistosos 0.8x
- Decaimento temporal: meia-vida de 24 meses (730 dias)
- Elo historico: usar o Elo da data da partida, nunca o atual
- Metricas universais (todas as 48 selecoes): gols, chutes, chutes no alvo, escanteios
- StatsBomb como validador de qualidade; SofaScore para cobertura de qualificatorias
- Elo ponderado na feature engineering, NUNCA na coleta bruta

## Estrutura de pastas
- src/collection/    coleta e padronizacao por fonte
- src/engineering/   pesos, decaimento, Elo, metricas derivadas
- src/model/         Dixon-Coles, Poisson, matchup
- src/utils/         helpers e validacao
- data/raw/          dados originais intocaveis
- data/processed/    apos feature engineering
- outputs/           perfis e previsoes finais

## Regras obrigatorias
- Leia .claude/rules/ antes de qualquer tarefa especifica
- Dados em data/raw/ sao SOMENTE LEITURA - nunca modificar
- Todo script deve ter logging configurado
- Toda funcao deve ter docstring e type hints
- Rodar pytest tests/ antes de qualquer commit

## Ritual de transicao entre fases (OBRIGATORIO ao iniciar qualquer fase X.Y)
1. Criar docs/fase_X_nome.md documentando o que foi feito na fase anterior:
   - O que foi implementado e por que cada decisao foi tomada
   - Problemas encontrados e como foram resolvidos
   - Decisoes tecnicas relevantes para estudo futuro
   - Resultados e metricas de cobertura alcancados
   - Convencao de nome: docs/fase_0_setup.md, docs/fase_1_coleta.md, etc.
2. Commit da fase anterior: git add + git commit com mensagem "feat: fase X completa - <resumo>"
3. Push para o repositorio remoto: git push
4. So entao iniciar o trabalho da nova fase
