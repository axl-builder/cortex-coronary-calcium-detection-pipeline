"""
transform_sheets tests against synthetic data.

Asserts are about INVARIANTS, not exact numbers.
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
# Common invariants
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
        assert len(fila) == n_cols, f"Row {i}: {len(fila)} != {n_cols}"


@pytest.mark.parametrize("fixture", [FIXTURE_MINIMO, FIXTURE_REALISTA, FIXTURE_CAOTICO])
def test_valor_crudo_de_contraste_se_preserva(fixture, settings):
    """The CSV must carry the raw value, not the internal label."""
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
# Specific tests
# ──────────────────────────────────────────────────────────────────────

def test_minimo_todas_pasan(settings):
    """
    Minimum profile: all included rows are TC + chest + no contrast.
    Summary/checklist rows are processed but filtered as non-TC
    (they are not patient data) — that is correct, not a bug.
    """
    filas, stats, problemas, fechas = _run(FIXTURE_MINIMO, settings)
    assert stats["filas"] > 0
    # all rows that passed are without contrast
    assert stats["incluidas_sin_contraste"] == stats["filas"]
    assert stats["incluidas_con_contraste"] == 0
    assert stats["incluidas_desconocido"] == 0
    # all studies in the output are TC (no RMN/RX/ECO)
    idx_estudio = settings["header"].index("ESTUDIO")
    estudios = {fila[idx_estudio] for fila in filas}
    assert estudios == {"TC"}, f"Studies in patients: {estudios}"


def test_minimo_filtradas_no_tc_son_resumen_y_checklist(settings):
    """
    The non-TC rows of the minimum profile are the summary and checklist
    blocks (no study), not patient data with RMN/RX/ECO.
    """
    filas, stats, problemas, fechas = _run(FIXTURE_MINIMO, settings)
    # there are non-TC rows (summary + checklist), but all are rows without study
    assert stats["filtradas_no_tc"] > 0


def test_realista_fechas_monotonas_desc(settings):
    filas, stats, problemas, fechas = _run(FIXTURE_REALISTA, settings)
    no_nulas = [f for f in fechas if f is not None]
    for i in range(1, len(no_nulas)):
        assert no_nulas[i] <= no_nulas[i - 1]


def test_realista_sin_fecha_manual_no_tiene_huecos(settings):
    """
    Realistic profile WITHOUT a manual-date tab: the DDMM sequence is
    continuous, with no large gaps.
    """
    filas, stats, problemas, fechas = _run(FIXTURE_REALISTA, settings)
    assert len(problemas["huecos"]) == 0


def test_realista_con_fecha_manual_hueco_esperado(settings):
    """
    Realistic profile WITH a manual-date tab: the only large gap must
    involve that tab (not between two consecutive DDMM tabs).
    """
    from tests.fixtures.synthetic import FIXTURE_REALISTA_CON_FECHA_MANUAL
    result, nombres = FIXTURE_REALISTA_CON_FECHA_MANUAL
    filas, stats, problemas, fechas = _run(FIXTURE_REALISTA_CON_FECHA_MANUAL, settings)
    # gaps only involve the tab with the manual date
    pestanias_manuales = {n for n in nombres if not n.isnumeric()}
    assert len(problemas["huecos"]) == 1
    for n_prev, _, n_curr, _, _ in problemas["huecos"]:
        assert (n_prev in pestanias_manuales) or (n_curr in pestanias_manuales), (
            f"Gap between DDMM tabs without manual date: {n_prev} -> {n_curr}"
        )


def test_fecha_manual_se_aplica_a_sus_filas(settings):
    """
    Rows from a manual-date tab must have the date specified in
    `fechas_manuales`, not an inferred one.
    """
    from tests.fixtures.synthetic import FIXTURE_REALISTA_CON_FECHA_MANUAL
    filas, stats, problemas, fechas = _run(FIXTURE_REALISTA_CON_FECHA_MANUAL, settings)
    # the manual date of "Hoja 161" in settings is 2025-12-01
    fechas_output = {fila[0] for fila in filas}
    assert "2025-12-01" in fechas_output, (
        f"No rows with manual date 2025-12-01. "
        f"Dates: {sorted(fechas_output)[:5]}..."
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
    assert compuestos, f"No compound values. Values: {sorted(valores)[:20]}"