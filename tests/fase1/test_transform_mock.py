"""
Tests de transform_sheets contra datos sintéticos.

Los asserts son sobre INVARIANTES, no sobre números exactos.
"""

import pytest

from tests.fixtures.synthetic import (
    FIXTURE_MINIMO, FIXTURE_REALISTA, FIXTURE_CAOTICO,
)
from src.fase1_ingesta.config import load_settings
from src.fase1_ingesta.cleaning.transform import transform_sheets


@pytest.fixture(scope="module")
def settings():
    return load_settings()


def _run(fixture, settings):
    result, nombres = fixture
    return transform_sheets(result, nombres, settings)


# ──────────────────────────────────────────────────────────────────────
# Invariantes comunes
# ──────────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("fixture", [FIXTURE_MINIMO, FIXTURE_REALISTA, FIXTURE_CAOTICO])
def test_stats_filas_coincide_con_filas_emitidas(fixture, settings):
    filas, stats, problemas, fechas = _run(fixture, settings)
    assert stats["filas"] == len(filas)


@pytest.mark.parametrize("fixture", [FIXTURE_MINIMO, FIXTURE_REALISTA, FIXTURE_CAOTICO])
def test_fechas_alineadas_con_nombres(fixture, settings):
    result, nombres = fixture
    filas, stats, problemas, fechas = _run(fixture, settings)
    assert len(fechas) == len(nombres)


@pytest.mark.parametrize("fixture", [FIXTURE_MINIMO, FIXTURE_REALISTA, FIXTURE_CAOTICO])
def test_filas_tienen_columnas_del_header(fixture, settings):
    filas, stats, problemas, fechas = _run(fixture, settings)
    n_cols = len(settings["header"])
    for i, fila in enumerate(filas):
        assert len(fila) == n_cols, f"Fila {i}: {len(fila)} != {n_cols}"


@pytest.mark.parametrize("fixture", [FIXTURE_MINIMO, FIXTURE_REALISTA, FIXTURE_CAOTICO])
def test_valor_crudo_de_contraste_se_preserva(fixture, settings):
    """El CSV debe llevar el crudo, no la etiqueta interna."""
    filas, stats, problemas, fechas = _run(fixture, settings)
    idx_contraste = settings["header"].index("CONTRASTE")
    valores = {fila[idx_contraste] for fila in filas}
    etiquetas_internas = {"sin_contraste", "con_contraste"}
    assert not (valores & etiquetas_internas)


@pytest.mark.parametrize("fixture", [FIXTURE_MINIMO, FIXTURE_REALISTA, FIXTURE_CAOTICO])
def test_conteo_inclusion_exclusion_cierra(fixture, settings):
    filas, stats, problemas, fechas = _run(fixture, settings)
    incluidas = sum(stats[k] for k in stats if k.startswith("incluidas_"))
    assert incluidas == stats["filas"]


# ──────────────────────────────────────────────────────────────────────
# Tests específicos
# ──────────────────────────────────────────────────────────────────────

def test_minimo_todas_pasan(settings):
    """
    Perfil mínimo: todas las filas incluidas son TC + tórax + sin contraste.
    Las filas de resumen/checklist se procesan pero se filtran como no-TC
    (no son datos de paciente) — eso es correcto, no es un bug.
    """
    filas, stats, problemas, fechas = _run(FIXTURE_MINIMO, settings)
    assert stats["filas"] > 0
    # todos los que pasaron son sin contraste
    assert stats["incluidas_sin_contraste"] == stats["filas"]
    assert stats["incluidas_con_contraste"] == 0
    assert stats["incluidas_desconocido"] == 0
    # todos los estudios en el output son TC (no hay RMN/RX/ECO)
    idx_estudio = settings["header"].index("ESTUDIO")
    estudios = {fila[idx_estudio] for fila in filas}
    assert estudios == {"TC"}, f"Estudios en pacientes: {estudios}"


def test_minimo_filtradas_no_tc_son_resumen_y_checklist(settings):
    """
    Las filas no-TC del perfil mínimo son las del bloque resumen y checklist
    (no tienen estudio), no datos de paciente con RMN/RX/ECO.
    """
    filas, stats, problemas, fechas = _run(FIXTURE_MINIMO, settings)
    # hay no-TC (resumen + checklist), pero todas son filas sin estudio
    assert stats["filtradas_no_tc"] > 0


def test_realista_fechas_monotonas_desc(settings):
    filas, stats, problemas, fechas = _run(FIXTURE_REALISTA, settings)
    no_nulas = [f for f in fechas if f is not None]
    for i in range(1, len(no_nulas)):
        assert no_nulas[i] <= no_nulas[i - 1]


def test_realista_sin_fecha_manual_no_tiene_huecos(settings):
    """
    Perfil realista SIN pestaña con fecha manual: la secuencia DDMM es
    continua, sin huecos grandes.
    """
    filas, stats, problemas, fechas = _run(FIXTURE_REALISTA, settings)
    assert len(problemas["huecos"]) == 0


def test_realista_con_fecha_manual_hueco_esperado(settings):
    """
    Perfil realista CON pestaña de fecha manual: el único hueco grande
    debe involucrar a esa pestaña (no entre dos DDMM consecutivas).
    """
    from tests.fixtures.synthetic import FIXTURE_REALISTA_CON_FECHA_MANUAL
    result, nombres = FIXTURE_REALISTA_CON_FECHA_MANUAL
    filas, stats, problemas, fechas = _run(FIXTURE_REALISTA_CON_FECHA_MANUAL, settings)
    # huecos solo involucran la pestaña con fecha manual
    pestanias_manuales = {n for n in nombres if not n.isnumeric()}
    assert len(problemas["huecos"]) == 1
    for n_prev, _, n_curr, _, _ in problemas["huecos"]:
        assert (n_prev in pestanias_manuales) or (n_curr in pestanias_manuales), (
            f"Hueco entre DDMM sin fecha manual: {n_prev} -> {n_curr}"
        )


def test_fecha_manual_se_aplica_a_sus_filas(settings):
    """
    Las filas de una pestaña con fecha manual deben tener la fecha
    especificada en `fechas_manuales`, no una inferida.
    """
    from tests.fixtures.synthetic import FIXTURE_REALISTA_CON_FECHA_MANUAL
    filas, stats, problemas, fechas = _run(FIXTURE_REALISTA_CON_FECHA_MANUAL, settings)
    # la fecha manual de "Hoja 161" en settings es 2025-12-01
    fechas_output = {fila[0] for fila in filas}
    assert "2025-12-01" in fechas_output, (
        f"No hay filas con fecha manual 2025-12-01. "
        f"Fechas: {sorted(fechas_output)[:5]}..."
    )


def test_caotico_no_explota(settings):
    filas, stats, problemas, fechas = _run(FIXTURE_CAOTICO, settings)
    assert isinstance(filas, list)
    assert stats["filas_cortas"] > 0
    assert stats["filas_vacias"] > 0


def test_caotico_preserva_contrastes_compuestos(settings):
    filas, stats, problemas, fechas = _run(FIXTURE_CAOTICO, settings)
    idx = settings["header"].index("CONTRASTE")
    valores = {fila[idx] for fila in filas}
    compuestos = {v for v in valores if "," in v}
    assert compuestos, f"No hay compuestos. Valores: {sorted(valores)[:20]}"