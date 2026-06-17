# ROADMAP - Copa 2026 Predictive Model

## Visao geral
FASE 0: Setup          -> 2-3 dias
FASE 1: Coleta         -> 5-7 dias
FASE 2: Feature Eng.   -> 3-4 dias
FASE 3: Perfis         -> 2-3 dias
FASE 4: Modelo         -> 3-4 dias
FASE 5: Validacao      -> 3-4 dias
FASE 6: Copa 2026      -> continuo

---

## FASE 0 - Setup do Ambiente
Objetivo: ambiente funcional com Claude Code e dependencias instaladas.

- [ ] 0.1  Instalar Node.js 18+ e npm
- [ ] 0.2  Instalar Claude Code: npm install -g @anthropic-ai/claude-code
- [ ] 0.3  Autenticar: claude -> OAuth
- [ ] 0.4  Instalar extensao Claude Code no VSCode
- [ ] 0.5  Criar ambiente virtual: python -m venv .venv && source .venv/bin/activate
- [ ] 0.6  Instalar dependencias: pip install -r requirements.txt
- [ ] 0.7  Copiar .env.example -> .env e preencher variaveis
- [ ] 0.8  Testar StatsBomb: from statsbombpy import sb; print(sb.competitions().head())
- [ ] 0.9  Testar soccerdata: import soccerdata as sd; sd.ClubElo().read_by_team("Brazil")
- [ ] 0.10 Inicializar git: git init + primeiro commit

Criterio de conclusao: python -c "import statsbombpy, soccerdata, penaltyblog" sem erros.

---

## FASE 1 - Coleta de Dados
Objetivo: base de dados bruta para todas as 48 selecoes, janela 2023-2026.

### 1A - StatsBomb Open Data
- [ ] 1.1  Criar src/collection/statsbomb_collector.py
- [ ] 1.2  Coletar Copa America 2024 (competition_id=223, season_id=282)
- [ ] 1.3  Coletar Euro 2024 (competition_id=55, season_id=282)
- [ ] 1.4  Coletar AFCON 2023 (competition_id=1267, season_id=107)
- [ ] 1.5  Para cada partida: extrair xG, chutes, chutes no alvo, escanteios, PPDA
- [ ] 1.6  Salvar em data/raw/statsbomb/{competicao}.parquet

### 1B - Elo Historico
- [ ] 1.7  Criar src/collection/elo_collector.py
- [ ] 1.8  Baixar historico Elo das 48 selecoes via soccerdata
- [ ] 1.9  Criar get_elo_on_date(team, date) com interpolacao
- [ ] 1.10 Salvar em data/raw/elo/elo_historico.parquet

### 1C - SofaScore (Qualificatorias e Amistosos)
- [ ] 1.11 Criar src/collection/sofascore_collector.py
- [ ] 1.12 Coletar Eliminatorias UEFA 2024-2026
- [ ] 1.13 Coletar Eliminatorias CONMEBOL 2023-2025
- [ ] 1.14 Coletar Eliminatorias AFC 2023-2025
- [ ] 1.15 Coletar Eliminatorias CONCACAF 2023-2025
- [ ] 1.16 Coletar Eliminatorias CAF 2023-2025
- [ ] 1.17 Coletar Nations League UEFA 2024-2025
- [ ] 1.18 Coletar amistosos com elenco titular
- [ ] 1.19 Salvar em data/raw/sofascore/{competicao}.parquet

### 1D - football-data.org (Fallback)
- [ ] 1.20 Criar src/collection/football_data_collector.py
- [ ] 1.21 Coletar resultados para times sem cobertura SofaScore
- [ ] 1.22 Salvar em data/raw/football_data/resultados_fallback.parquet

### 1E - Padronizacao e Qualidade
- [ ] 1.23 Criar src/collection/standardizer.py
- [ ] 1.24 Unificar todas as fontes no schema universal
- [ ] 1.25 Adicionar campo data_quality: "high" | "medium" | "low"
- [ ] 1.26 Padronizar nomes de selecoes (dicionario de mapeamento)
- [ ] 1.27 Adicionar Elo historico (team e opponent) por partida
- [ ] 1.28 Gerar outputs/coverage_report.md:
          - Total de partidas por selecao
          - Times com menos de 15 partidas
          - Qualidade de dados por time (% high/medium/low)

Criterio de conclusao: 40+ das 48 selecoes com 15+ partidas e 1+ competicao oficial.

---

## FASE 2 - Feature Engineering
Objetivo: features ponderadas prontas para o modelo.

- [ ] 2.1  Criar src/engineering/weights.py
          - calcular_peso_competicao(tipo) -> 1.2 | 1.0 | 0.8
          - calcular_peso_temporal(data, referencia, meia_vida=730)
          - calcular_peso_final(peso_competicao, peso_temporal)

- [ ] 2.2  Criar src/engineering/features.py
          - ponderar_por_elo(metrica, elo_adversario, elo_media=1500)
          - calcular_precisao_chutes(shots_on_target, shots_total)
          - calcular_razao_dominio(shots_for, shots_against)

- [ ] 2.3  Criar src/engineering/profiles.py
          - Agregar metricas por selecao com pesos finais
          - Calcular perfil ofensivo: gols, chutes, xG, precisao
          - Calcular perfil defensivo: gols sofridos, chutes concedidos
          - Calcular perfil de estilo: dominio, escanteios
          - Classificar estilo: "high_press"|"possession"|"direct"|"low_block"

- [ ] 2.4  Salvar data/processed/features/features_v1.parquet
- [ ] 2.5  Salvar data/processed/team_profiles/perfis_v1.parquet
- [ ] 2.6  Escrever tests/test_engineering.py

Criterio de conclusao: 48 selecoes com perfil completo e features sem NaN criticos.

---

## FASE 3 - Perfis Taticos por Selecao
Objetivo: indice 0-10 por dimensao tatica para cada selecao.

- [ ] 3.1  Criar src/model/team_indexer.py
          - Normalizar cada dimensao para 0-10 com benchmarks reais
          - Forca ofensiva, solidez defensiva, qualidade de finalizacao
          - Intensidade de pressao (PPDA onde disponivel)
          - Dominio territorial

- [ ] 3.2  Gerar 48 arquivos JSON em outputs/team_profiles/
- [ ] 3.3  Gerar relatorio comparativo das 48 selecoes

Criterio de conclusao: 48 arquivos JSON de perfil gerados e validados.

---

## FASE 4 - Modelo de xG e Simulacao
Objetivo: modelo gerando distribuicao de placares para qualquer confronto.

- [ ] 4.1  Criar src/model/dixon_coles.py
          - Treinar com penaltyblog usando peso_final
          - prever_xg(team_a, team_b) -> (lambda_a, lambda_b)

- [ ] 4.2  Criar src/model/matchup.py
          - Camada simetrica de ajuste de estilo
          - Classificar confronto e aplicar multiplicador

- [ ] 4.3  Criar src/model/poisson.py
          - simular_placares(lambda_a, lambda_b, n=100_000)
          - resumir_probabilidades(distribuicao)

- [ ] 4.4  Criar src/model/pipeline.py
          - Orquestrar: team_a + team_b -> JSON de previsao
          - Salvar em outputs/predictions/{team_a}_vs_{team_b}_v1.json

- [ ] 4.5  Escrever tests/test_model.py

Criterio de conclusao: prever_confronto("Brazil", "France") retorna JSON valido.

---

## FASE 5 - Validacao e Calibracao
Objetivo: confirmar precisao antes de aplicar a Copa 2026.

- [ ] 5.1  Backtest na Copa America 2024 (treinar com dados ate 2023)
- [ ] 5.2  Backtest no Euro 2024 (mesmo metodo)
- [ ] 5.3  Calcular metricas:
          - Brier Score para probabilidades de resultado
          - MAE para xG previsto vs real
          - % de jogos com placar mais provavel correto

- [ ] 5.4  Calibrar parametros se necessario
- [ ] 5.5  Gerar outputs/validation_report.md

Criterio de conclusao: Brier Score < 0.25 (referencia: aleatorio aprox 0.33).

---

## FASE 6 - Aplicacao a Copa 2026
Objetivo: previsoes para todos os jogos da Copa.

- [ ] 6.1  Atualizar dados com partidas mais recentes pre-torneio
- [ ] 6.2  Gerar perfil atualizado das 48 selecoes
- [ ] 6.3  Simular todos os jogos da fase de grupos
- [ ] 6.4  Construir simulador de fase eliminatoria
- [ ] 6.5  Gerar probabilidades de avanco por rodada
- [ ] 6.6  Documentar previsoes em outputs/predictions/copa2026_preview.md

---

## Convencoes de commit
feat: adiciona coletor StatsBomb Copa America 2024
fix: corrige calculo de peso temporal para campo neutro
docs: atualiza ROADMAP com criterios da Fase 1
test: adiciona testes para calcular_peso_temporal
refactor: separa logica de Elo em modulo proprio

## Comandos uteis
pytest tests/ -v --cov=src
python src/collection/standardizer.py --report
python src/model/team_indexer.py --team "Brazil"
python src/model/pipeline.py --team-a "Brazil" --team-b "France"
