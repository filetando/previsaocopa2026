# Regras de Seguranca - Copa 2026

## Credenciais
- NUNCA commitar .env, chaves de API ou tokens
- Usar .env para todas as credenciais (ja no .gitignore)
- Usar .env.example como template publico sem valores reais
- Carregar com python-dotenv: from dotenv import load_dotenv

## Scraping responsavel
- Respeitar rate limits de cada fonte
- SofaScore: maximo 1 request por segundo com delays aleatorios
- Salvar dados brutos em data/raw/ para evitar re-scraping desnecessario

```python
import time, random
time.sleep(random.uniform(1.0, 2.5))  # Entre requests ao SofaScore
```

## Protecao dos dados brutos
- data/raw/ e SOMENTE LEITURA apos a coleta
- Nunca referenciar data/raw/ com operacoes de escrita fora de src/collection/
- Fazer backup antes de qualquer re-coleta

## Git
- .gitignore deve incluir: .env, data/, outputs/
- Commitar apenas codigo e documentacao - nunca dados
- Mensagens de commit: feat: | fix: | docs: | test: | refactor:

## Variaveis de ambiente necessarias (ver .env.example)
- FOOTBALL_DATA_API_KEY
- SOFASCORE_DELAY_MIN e MAX
- HALF_LIFE_DAYS, ELO_MEDIA_GLOBAL, N_SIMULACOES
- LOG_LEVEL
