"""Cores e padrões visuais compartilhados pelos gráficos.

Manter as cores em um único lugar garante a consistência exigida no
laboratório: a mesma cor para cada grupo e para cada teste em todos os
gráficos do dashboard.
"""

CORES_GRUPO = {
    "com_bot": "#1f77b4",  # azul
    "sem_bot": "#d62728",  # vermelho
}

CORES_TESTE = {
    "welch": "#1f77b4",  # azul
    "mann_whitney": "#ff7f0e",  # laranja
}

ROTULOS_GRUPO = {
    "com_bot": "Com bot",
    "sem_bot": "Sem bot",
}

ROTULOS_TESTE = {
    "welch": "t de Welch",
    "mann_whitney": "Mann-Whitney",
}
