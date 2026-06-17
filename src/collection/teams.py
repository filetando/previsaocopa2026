"""Lista das 48 selecoes classificadas para a Copa do Mundo 2026."""

# Nome completo -> slug usado nas URLs do eloratings.net
# Formato: https://www.eloratings.net/{slug}.tsv
ELO_URL_SLUG: dict[str, str] = {
    # Hosts CONCACAF
    "United States": None,          # sem TSV dedicado; extraido via _extract_from_opponents
    "Canada": "Canada",
    "Mexico": "Mexico",
    # CONMEBOL
    "Argentina": "Argentina",
    "Brazil": "Brazil",
    "Uruguay": "Uruguay",
    "Colombia": "Colombia",
    "Ecuador": "Ecuador",
    "Paraguay": "Paraguay",
    # UEFA
    "Spain": "Spain",
    "France": "France",
    "Germany": "Germany",
    "England": "England",
    "Portugal": "Portugal",
    "Netherlands": "Netherlands",
    "Croatia": "Croatia",
    "Austria": "Austria",
    "Switzerland": "Switzerland",
    'Bosnia and Herzegovina': "Bosnia_and_Herzegovina",
    "Czechia": "Czechia",
    "Turkey": "Turkey",
    "Scotland": "Scotland",
    "Belgium": "Belgium",
    "Sweden": "Sweden",
    "Norway": "Norway",
    # CAF
    "Morocco": "Morocco",
    "Cape Verde": "Cape_Verde",
    "Senegal": "Senegal",
    "Egypt": "Egypt",
    "DR Congo": "DR_Congo",
    "South Africa": "South_Africa",
    "Ghana": "Ghana",
    "Tunisia": "Tunisia",
    "Ivory Coast": "Ivory_Coast",
    "Algeria": "Algeria",
    # AFC
    "Japan": "Japan",
    "South Korea": "South_Korea",
    "Iran": "Iran",
    "Australia": "Australia",
    "Saudi Arabia": "Saudi_Arabia",
    "Uzbekistan": "Uzbekistan",
    "Jordan": "Jordan",
    "Iraq": "Iraq",
    "Qatar": "Qatar",
    # OFC
    "New Zealand": "New_Zealand",
    # CONCACAF additional
    "Panama": "Panama",
    "Haiti": "Haiti",
    "Curacao": "Curacao",
}

COPA_2026_TEAMS: list[str] = list(ELO_URL_SLUG.keys())

# Mapeamento de nomes StatsBomb -> nome padrao do projeto
# StatsBomb usa nomes completos; ajustar quando houver divergencia
STATSBOMB_NAME_MAP: dict[str, str] = {
    "United States": "United States",
    "Korea Republic": "South Korea",
    "Republic of Ireland": "Ireland",
    "Côte d'Ivoire": "Ivory Coast",
    "DR Congo": "DR Congo",
    "Czech Republic": "Czechia",
}
