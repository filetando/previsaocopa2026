# Regras Python - Copa 2026

## Estrutura obrigatoria de funcoes
Toda funcao deve ter type hints e docstring:

```python
def calcular_peso_temporal(
    data_partida: datetime,
    data_referencia: datetime,
    meia_vida_dias: int = 730
) -> float:
    """
    Calcula o peso temporal via decaimento exponencial.

    Args:
        data_partida: Data em que a partida foi disputada.
        data_referencia: Data base para o calculo.
        meia_vida_dias: Dias para o peso cair a metade (padrao: 730 = 24 meses).

    Returns:
        Peso entre 0 e 1.
    """
    delta = (data_referencia - data_partida).days
    lambda_ = math.log(2) / meia_vida_dias
    return math.exp(-lambda_ * delta)
```

## Logging obrigatorio
```python
import logging
logger = logging.getLogger(__name__)

logger.info("Iniciando coleta: competition_id=%s", competition_id)
logger.warning("Cobertura incompleta para %s: %d jogos", team, n)
logger.error("Falha na coleta para %s: %s", team, str(e))
```

## Tratamento de erros
```python
try:
    dados = coletar_dados(team)
except DataNotFoundError:
    logger.warning("Dados nao encontrados para %s - usando fallback", team)
    dados = None
except Exception as e:
    logger.error("Erro inesperado para %s: %s", team, str(e))
    raise
```

## Regras gerais
- Nunca hardcodar caminhos - usar src/utils/config.py
- Usar python-dotenv para variaveis de ambiente
- Black para formatacao (88 chars por linha)
- isort para organizacao de imports
- Um arquivo de teste por modulo: tests/test_{modulo}.py
- Cobertura minima de testes: 80% nas funcoes de model e engineering
