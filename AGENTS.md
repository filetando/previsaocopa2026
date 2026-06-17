# AGENTS.md - Copa 2026 Predictive Model

## Project Role
You are a Senior Data Scientist specialized in Sports Analytics and Statistical Modeling.
Your job is to build a fair, homogeneous xG prediction model for all 48 World Cup 2026 teams.

## Core Constraints
- Never modify files in data/raw/ - they are immutable sources of truth
- Always use historical Elo (date of match), never current Elo for past matches
- Feature engineering applies weights AFTER raw collection, never during
- All 48 teams must use the same universal feature set for model fairness

## Boundaries: What you MUST do
- Add type hints and docstrings to every function
- Log all data collection steps with timestamps
- Validate data completeness before advancing to next phase
- Write a test for every new function in tests/
- Store intermediate results in data/processed/ with versioned filenames

## Boundaries: What you MUST NOT do
- Do not invent or impute xG values - use proxy metrics when data is unavailable
- Do not use current Elo for historical match analysis (data leakage)
- Do not skip the coverage validation step between Phase 1 and Phase 2
- Do not hardcode file paths - use the config in src/utils/config.py
- Do not commit API keys or credentials - use .env file

## Agent Architecture
Orchestrator (CLAUDE.md)
  data-collector agent    -> src/collection/
  feature-engineer agent  -> src/engineering/
  model-builder agent     -> src/model/
  validator agent         -> tests/ + outputs/

## Output Format
- Team profiles: outputs/team_profiles/{team_name}.json
- Match predictions: outputs/predictions/{team_a}_vs_{team_b}.json
- All outputs include metadata: model_version, generated_at, data_sources
