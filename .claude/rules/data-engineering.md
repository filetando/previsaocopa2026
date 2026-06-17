# Regras de Engenharia de Dados - Copa 2026

## Hierarquia de fontes por confiabilidade
1. StatsBomb Open Data  - gold standard, event-level
2. eloratings.net       - fonte canonica para Elo historico
3. SofaScore            - cobertura de qualificatorias, xG proprio
4. football-data.org    - fallback para resultados e stats basicas

## Schema universal (toda partida coletada deve seguir este formato)
{
    "match_id": str,
    "team": str,
    "opponent": str,
    "date": "YYYY-MM-DD",
    "competition": str,        # "continental" | "qualifier" | "friendly"
    "venue": str,              # "home" | "away" | "neutral"
    "goals_scored": int,
    "goals_conceded": int,
    "shots_for": int,
    "shots_against": int,
    "shots_on_target_for": int,
    "shots_on_target_against": int,
    "corners_for": int,
    "corners_against": int,
    "xg_for": float | None,
    "xg_against": float | None,
    "elo_team": float,
    "elo_opponent": float,
    "source": str,             # "statsbomb" | "sofascore" | "football_data"
    "data_quality": str        # "high" | "medium" | "low"
}

## Qualidade de dados
- high:   fonte StatsBomb (xG confiavel)
- medium: fonte SofaScore (xG proprio, cobertura boa)
- low:    apenas resultados sem xG

## Pesos de competicao (FIXADOS)
COMPETITION_WEIGHTS = {
    "continental": 1.2,
    "qualifier":   1.0,
    "friendly":    0.8,
}

## Decaimento temporal (FIXADO)
HALF_LIFE_DAYS = 730  # 24 meses
peso = exp(-ln(2) / 730 * dias_desde_partida)

## Peso final por partida
peso_final = peso_competicao * peso_temporal
# NAO aplicar Elo aqui - Elo e aplicado na feature engineering por metrica

## Convencao de nomes de arquivos
data/raw/statsbomb/copa_america_2024.parquet
data/raw/sofascore/conmebol_qualifiers_2023_2025.parquet
data/raw/elo/elo_historico.parquet
data/processed/matches/partidas_padronizadas_v1.parquet
data/processed/team_profiles/perfis_v1.parquet

## Validacao obrigatoria entre Fase 1 e Fase 2
- Minimo 15 partidas por selecao na janela de 3 anos
- Pelo menos 1 competicao oficial (nao apenas amistosos)
- Elo disponivel para todas as datas
- Documentar times abaixo do threshold em outputs/coverage_report.md
