"""Configuracao central do projeto Copa 2026."""
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

ROOT_DIR = Path(__file__).parent.parent.parent
DATA_RAW = ROOT_DIR / os.getenv("DATA_RAW_PATH", "data/raw")
DATA_PROCESSED = ROOT_DIR / os.getenv("DATA_PROCESSED_PATH", "data/processed")
OUTPUT_DIR = ROOT_DIR / os.getenv("OUTPUT_PATH", "outputs")

# Parametros do modelo (FIXADOS)
HALF_LIFE_DAYS: int = int(os.getenv("HALF_LIFE_DAYS", 730))
ELO_MEDIA_GLOBAL: float = float(os.getenv("ELO_MEDIA_GLOBAL", 1500))
MAX_GOLS_SIMULACAO: int = int(os.getenv("MAX_GOLS_SIMULACAO", 8))
N_SIMULACOES: int = int(os.getenv("N_SIMULACOES", 100_000))

# Pesos de competicao (FIXADOS)
COMPETITION_WEIGHTS: dict = {
    "continental": 1.2,
    "qualifier": 1.0,
    "friendly": 0.8,
}

# Configuracoes de coleta
SOFASCORE_DELAY_MIN: float = float(os.getenv("SOFASCORE_DELAY_MIN", 1.0))
SOFASCORE_DELAY_MAX: float = float(os.getenv("SOFASCORE_DELAY_MAX", 2.5))
FOOTBALL_DATA_API_KEY: str = os.getenv("FOOTBALL_DATA_API_KEY", "")

# Competicoes StatsBomb disponíveis
STATSBOMB_COMPETITIONS: dict = {
    "copa_america_2024": {"competition_id": 223, "season_id": 282},
    "euro_2024":         {"competition_id": 55,  "season_id": 282},
    "afcon_2023":        {"competition_id": 1267, "season_id": 107},
    "world_cup_2022":    {"competition_id": 43,  "season_id": 106},
    "euro_2020":         {"competition_id": 55,  "season_id": 43},
}

WINDOW_YEARS: int = 3
REFERENCE_DATE_STR: str = "2026-06-11"
LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
