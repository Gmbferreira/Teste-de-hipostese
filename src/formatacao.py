"""Formatação de números no padrão brasileiro para textos, tabelas e gráficos."""

from __future__ import annotations


def numero(valor: float, casas: int = 2) -> str:
    """Número com vírgula decimal e ponto de milhar: 1234.5 -> '1.234,50'."""
    texto = f"{valor:,.{casas}f}"
    texto = texto.replace(",", "X").replace(".", ",").replace("X", ".")
    if texto.startswith("-"):
        sem_sinal = texto[1:]
        # Evita "−0,00" quando o valor arredondado é zero.
        texto = sem_sinal if set(sem_sinal) <= {"0", ",", "."} else "−" + sem_sinal
    return texto


def p_valor(p: float) -> str:
    """P-valor com três casas, ou '< 0,001' quando é muito pequeno."""
    if p < 0.001:
        return "< 0,001"
    return numero(p, 3)


def porcentagem(fracao: float, casas: int = 1) -> str:
    """Fração como porcentagem: 0.0493 -> '4,9%'."""
    return f"{numero(100 * fracao, casas)}%"
