# Copa 2026 - Modelo Preditivo de xG

Modelo estatístico para prever xG e distribuicao de placares em confrontos
da Copa do Mundo 2026, usando matchup tatico com Dixon-Coles + Poisson.

## Pipeline
Dados brutos (3 anos)
  -> Pesos: competicao x temporal x Elo adversario
  -> Perfil tatico por selecao (48 times)
  -> Matchup: ataque_A x defesa_B + ajuste de estilo
  -> Dixon-Coles -> lambda_A e lambda_B
  -> Simulacao Poisson (100k) -> distribuicao de placares

## Fontes de dados
- StatsBomb Open Data : Torneios continentais + Copas (alta qualidade)
- eloratings.net      : Elo historico de todas as selecoes
- SofaScore           : Qualificatorias e amistosos
- football-data.org   : Fallback para times sem cobertura

## Setup rapido
```bash
npm install -g @anthropic-ai/claude-code
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
code .
claude
```

## Uso
```bash
python src/model/pipeline.py --team-a "Brazil" --team-b "France"
python src/model/team_indexer.py --team "Brazil"
pytest tests/ -v
```

## Documentacao
- ROADMAP.md         : Todas as fases e tarefas com criterios de conclusao
- CLAUDE.md          : Instrucoes para o Claude Code
- AGENTS.md          : Definicao de papel e limites do agente
- .claude/rules/     : Padroes de codigo, dados e seguranca
- .claude/skills/    : Implementacoes de referencia por modulo
