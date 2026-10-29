"""
Mock structure tests: verify that each on-call tab has the REAL structure
of the sheet (not the clean pandas version).

Reference: the `modelo` tab of the real sheet (the empty operational
template that doctors copy for each on-call shift).

Expected structure per tab:
  row 0:   [operational title, "PLANILLA GUARDIA", "", ...]
  row 1:   ["CHECKLIST", "", ...]
  row 2:   ["", "PACIENTE", "SECTOR", "HAB", "ESTUDIO", ...]  ← header
  row 3..: patient rows + residuals
  ...:      summary block (TC/RMN GUARDIA/INTERNADOS)
  ...:      operational checklist (CARRO DE PARO, BRIEF, ...)
"""

import pytest

from tests.fixtures.synthetic import FIXTURE_REALISTA, fixture_pestania


# ──────────────────────────────────────────────────────────────────────
# Real structure constants (extracted from the template)
# ──────────────────────────────────────────────────────────────────────

TITULO_OPERATIVO = "HACER CONTEO DE PACIENTES Y REGIONES + MIRAR MAILS"
N_COLUMNAS = 21

# Real header (row 2), columns A..U
HEADER_ESPERADO = [
    "",
    "PACIENTE",
    "SECTOR",
    "HAB",
    "ESTUDIO",
    "REGION",
    "CONTRASTE ",          # note: trailing space (as in the real sheet)
    "MOTIVO",
    '"HORA\nPEDIDO"',      # with literal quotes
    "HS LLAMADO CAMILLERO",
    '"REALIZADO\n"',       # with literal quotes
    "COMENTARIO",
    "HECHO",
    "PREINFORME",
    "CANCELADO",
    "RMN GUARDIA",
    "RMN INTERNADO",
    "TC GUARDIA ",         # note: trailing space
    "TC INTERNADOS ",      # note: trailing space
    "DEMORA CAMILLERO",
    "DEMORA PEDIDO",
]

# Operational checklist labels (row X+.., at the end)
ETIQUETAS_CHECKLIST = {
    "NOMBRE", "CARRO DE PARO", "BRIEF ", "ARCHIVOS DIGITALIZADOS",
    "MAIL GENERAL", "MAIL ESTUDIOS PREVIOS",
    "CONSENTIMIENTOS Y PLANILLAS TC", "CONSENTIMIENTOS Y PLANILLAS RM",
    "ORDENES TC", "ORDENES RM", "CONTEO TC ", "CONTEO RM",
    "RECONSTRUCCIONES", "PLANILLA ACV",
}

# Summary block labels
ETIQUETAS_RESUMEN = {"GUARDIA", "INTERNADOS", "AMBULATORIOS"}

ESTUDIOS_VALIDOS = {"TC", "RMN", "RX", "ECO"}


# ──────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────

def _pad(fila, n=N_COLUMNAS):
    """Normalize a row to exactly n columns (padding/truncation)."""
    return (list(fila) + [""] * n)[:n]


# ──────────────────────────────────────────────────────────────────────
# Fixed structure tests (rows 0-2)
# ──────────────────────────────────────────────────────────────────────

def test_fila_0_titulo_operativo():
    vr = fixture_pestania("3105")
    fila = _pad(vr["values"][0])
    assert fila[0] == TITULO_OPERATIVO
    assert fila[1] == "PLANILLA GUARDIA"
    # rest empty
    assert all(v == "" for v in fila[2:])


def test_fila_1_checklist():
    vr = fixture_pestania("3105")
    fila = _pad(vr["values"][1])
    assert fila[0] == "CHECKLIST"
    assert all(v == "" for v in fila[1:])


def test_fila_2_header_completo():
    vr = fixture_pestania("3105")
    fila = _pad(vr["values"][2])
    assert fila == HEADER_ESPERADO, (
        f"Header does not match.\n"
        f"  Expected: {HEADER_ESPERADO}\n"
        f"  Got: {fila}"
    )


# ──────────────────────────────────────────────────────────────────────
# Column tests
# ──────────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("nombre", ["3105", "3005", "2905"])
def test_todas_las_filas_tienen_21_columnas(nombre):
    vr = fixture_pestania(nombre)
    for i, fila in enumerate(vr["values"]):
        assert len(fila) <= N_COLUMNAS, (
            f"Row {i} of {nombre!r} has {len(fila)} columns > {N_COLUMNAS}"
        )


# ──────────────────────────────────────────────────────────────────────
# "study → patient" invariant tests
# ──────────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("nombre", ["3105", "3005", "2905"])
def test_estudio_implica_paciente(nombre):
    """
    Invariant: if a row has a valid ESTUDIO, it must have a PACIENTE.
    The converse does NOT hold (residuals have patient without study).
    """
    vr = fixture_pestania(nombre)
    for i, fila_raw in enumerate(vr["values"]):
        if i < 3:
            continue  # rows 0-2 are fixed
        fila = _pad(fila_raw)
        estudio = str(fila[4]).strip() if fila[4] is not None else ""
        paciente = str(fila[1]).strip() if fila[1] is not None else ""
        if estudio in ESTUDIOS_VALIDOS:
            assert paciente, (
                f"Row {i} of {nombre!r}: estudio={estudio!r} but no paciente. "
                f"Full row: {fila}"
            )


# ──────────────────────────────────────────────────────────────────────
# Special block tests
# ──────────────────────────────────────────────────────────────────────

def test_bloque_resumen_presente():
    vr = fixture_pestania("3105")
    etiquetas = {
        str(_pad(f)[1]).strip()
        for f in vr["values"][3:]
        if _pad(f)[1]
    }
    assert "GUARDIA" in etiquetas, (
        f"Missing 'GUARDIA' in summary block. Labels: {etiquetas}"
    )
    assert "INTERNADOS" in etiquetas
    assert "AMBULATORIOS" in etiquetas


def test_checklist_operativo_presente():
    vr = fixture_pestania("3105")
    etiquetas = {
        str(_pad(f)[1]).strip()
        for f in vr["values"][3:]
        if _pad(f)[1]
    }
    # at least 5 checklist labels must be present
    encontradas = etiquetas & ETIQUETAS_CHECKLIST
    assert len(encontradas) >= 5, (
        f"Missing checklist labels. "
        f"Found: {encontradas}, expected at least 5 of {ETIQUETAS_CHECKLIST}"
    )
    # the most important ones
    assert "CARRO DE PARO" in etiquetas
    assert "PLANILLA ACV" in etiquetas


def test_residuales_tienen_estructura_correcta():
    """
    The template residuals are empty rows with FALSE x4 and 0:00:00 / -.
    They must not have random counts.
    """
    vr = fixture_pestania("3105")
    residuales = []
    for i, fila_raw in enumerate(vr["values"]):
        if i < 3:
            continue
        fila = _pad(fila_raw)
        # residual: empty patient OR patient with FALSE/FALSE in cols 2-3
        # and no study
        if not fila[1] and any(fila[11:15]):
            residuales.append(fila)

    # at least one residual in the tab (realistic profile)
    assert len(residuales) > 0, "No residuals found in 3105"

    for fila in residuales[:3]:  # check the first 3
        # cols L-O = FALSE/FALSE/FALSE/FALSE
        assert fila[11:15] == ["FALSE", "FALSE", "FALSE", "FALSE"], (
            f"Residual with wrong structure in cols L-O: {fila[11:15]}"
        )
        # cols T-U = 0:00:00 / -
        assert fila[19] == "0:00:00", f"Col T (DEMORA CAMILLERO): {fila[19]!r}"
        assert fila[20] == "-", f"Col U (DEMORA PEDIDO): {fila[20]!r}"


# ──────────────────────────────────────────────────────────────────────
# Tab type tests
# ──────────────────────────────────────────────────────────────────────

def test_hay_pestanias_no_guardia():
    result, nombres_guardia = FIXTURE_REALISTA
    n_total = len(result["valueRanges"])
    n_guardia = len(nombres_guardia)
    n_no_guardia = n_total - n_guardia
    assert n_no_guardia > 0, "The realistic fixture has no non-on-call tabs"
    # non-on-call names are NOT in nombres_guardia
    nombres_no_guardia = {
        vr["range"].split("!")[0].strip("'")
        for vr in result["valueRanges"]
    } - set(nombres_guardia)
    assert nombres_no_guardia, "No non-on-call names"


# ──────────────────────────────────────────────────────────────────────
# Determinism test
# ──────────────────────────────────────────────────────────────────────

def test_fixture_es_determinista():
    """Same seed → same output. Without this, fixtures are useless for CI."""
    from src.synthetic import generar_para_fase1
    r1, n1 = generar_para_fase1(profile="realista", seed=42)
    r2, n2 = generar_para_fase1(profile="realista", seed=42)
    assert n1 == n2
    assert len(r1["valueRanges"]) == len(r2["valueRanges"])
    for vr1, vr2 in zip(r1["valueRanges"], r2["valueRanges"]):
        assert vr1["range"] == vr2["range"]
        assert vr1["values"] == vr2["values"]