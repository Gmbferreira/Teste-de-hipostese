"""Roda o dashboard sem navegador e confere a seção 3 (issue #13)."""

from __future__ import annotations

from pathlib import Path

from streamlit.testing.v1 import AppTest

from src.exemplo import gerar_exemplo
from src.formatacao import p_valor

APP = Path(__file__).resolve().parents[1] / "dashboard" / "app.py"

SECOES = [
    "1. Cenário",
    "2. Os dados",
    "3. Como os testes funcionam",
    "4. Erro tipo I",
    "5. Poder",
    "6. Dados reais",
    "7. Conclusão",
]


def _rodar() -> AppTest:
    app = AppTest.from_file(str(APP), default_timeout=60)
    app.run()
    return app


def test_dashboard_roda_sem_erros_e_mantem_as_secoes_na_ordem() -> None:
    app = _rodar()
    assert not app.exception
    assert [h.value for h in app.header] == SECOES


def test_secao_3_tem_texto_tabela_e_interpretacao() -> None:
    app = _rodar()
    exemplo = gerar_exemplo()
    textos = " ".join(m.value for m in app.markdown)

    assert "t de Welch" in textos and "Mann-Whitney" in textos
    assert f"p = {p_valor(exemplo.mann_whitney.p_valor)}" in textos
    assert f"p = {p_valor(exemplo.welch.p_valor)}" in textos
    assert len(app.dataframe) >= 1
    assert any(e.label == "Interpretação completa do exemplo" for e in app.expander)
