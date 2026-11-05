"""Testes do gráfico G1 (issue #5)."""

from __future__ import annotations

import matplotlib.colors as mcolors
import pandas as pd
import pytest

from src.estilo import CORES_GRUPO
from src.grafico_g1 import dados_g1, grafico_g1, salvar_g1

ORIGENS = ("real", "simulado")
GRUPOS = ("com_bot", "sem_bot")


@pytest.fixture(scope="module")
def tabela() -> pd.DataFrame:
    return dados_g1()


def test_dados_tem_os_quatro_conjuntos(tabela: pd.DataFrame) -> None:
    assert set(tabela["origem"]) == set(ORIGENS)
    assert set(tabela["grupo"]) == set(GRUPOS)
    contagens = tabela.groupby(["origem", "grupo"]).size()
    assert (contagens == 35).all()
    assert len(tabela) == 140


def test_dados_sao_reproduziveis() -> None:
    pd.testing.assert_frame_equal(dados_g1(), dados_g1())


def test_g1_tem_titulo_eixos_e_legenda(tabela: pd.DataFrame) -> None:
    fig = grafico_g1(tabela)
    assert len(fig.axes) == 4
    assert "G1" in fig.get_suptitle()
    assert "dados reais" in fig.get_suptitle().lower()
    assert "simulados" in fig.get_suptitle().lower()

    for ax in fig.axes:
        assert ax.get_title(loc="left")
    for ax in fig.axes[2:]:
        assert "Tempo até o merge" in ax.get_xlabel()
        assert "horas" in ax.get_xlabel()
    for ax in (fig.axes[0], fig.axes[2]):
        assert "PRs" in ax.get_ylabel()

    textos = [texto.get_text() for texto in fig.legends[0].get_texts()]
    assert any("Com bot" in texto for texto in textos)
    assert any("Sem bot" in texto for texto in textos)
    assert any("Mediana" in texto for texto in textos)


def test_g1_usa_a_cor_de_cada_grupo(tabela: pd.DataFrame) -> None:
    fig = grafico_g1(tabela)
    # A ordem de fig.axes é: com/real, com/simulado, sem/real, sem/simulado.
    for ax, grupo in zip(
        fig.axes, ("com_bot", "com_bot", "sem_bot", "sem_bot"), strict=True
    ):
        cores = {mcolors.to_hex(patch.get_facecolor()) for patch in ax.patches}
        assert cores == {CORES_GRUPO[grupo]}


def test_g1_histogramas_contam_todos_os_prs(tabela: pd.DataFrame) -> None:
    for ax in grafico_g1(tabela).axes:
        assert sum(patch.get_height() for patch in ax.patches) == pytest.approx(35)


def test_g1_usa_escala_log_e_limites_comuns(tabela: pd.DataFrame) -> None:
    fig = grafico_g1(tabela)
    assert {ax.get_xscale() for ax in fig.axes} == {"log"}
    assert len({ax.get_xlim() for ax in fig.axes}) == 1
    assert len({ax.get_ylim() for ax in fig.axes}) == 1


def test_salvar_g1(tmp_path, tabela: pd.DataFrame) -> None:
    destino = salvar_g1(tmp_path / "g1.png", tabela)
    assert destino.exists()
    assert destino.stat().st_size > 10_000
