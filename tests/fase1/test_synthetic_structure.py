"""
Tests de estructura del mock: verifica que cada pestaña de guardia
tiene la estructura REAL de la planilla (no la versión limpia con pandas).

Referencia: la pestaña `modelo` de la planilla real (que es la plantilla
operativa vacía que los médicos copian para cada guardia).

Estructura esperada por pestaña:
  fila 0:   [título operativo, "PLANILLA GUARDIA", "", ...]
  fila 1:   ["CHECKLIST", "", ...]
  fila 2:   ["", "PACIENTE", "SECTOR", "HAB", "ESTUDIO", ...]  ← header
  fila 3..: datos de pacientes + residuales
  ...:      bloque de resumen (TC/RMN GUARDIA/INTERNADOS)
  ...:      checklist operativo (CARRO DE PARO, BRIEF, ...)
"""

import pytest

from tests.fixtures.synthetic import FIXTURE_REALISTA, fixture_pestania


# ──────────────────────────────────────────────────────────────────────
# Constantes de la estructura real (extraídas del modelo)
# ──────────────────────────────────────────────────────────────────────

TITULO_OPERATIVO = "HACER CONTEO DE PACIENTES Y REGIONES + MIRAR MAILS"
N_COLUMNAS = 21

# Header real (fila 2), columnas A..U
HEADER_ESPERADO = [
    "",
    "PACIENTE",
    "SECTOR",
    "HAB",
    "ESTUDIO",
    "REGION",
    "CONTRASTE ",          # ojo: espacio al final (como en el real)
    "MOTIVO",
    '"HORA\nPEDIDO"',      # con comillas literales
    "HS LLAMADO CAMILLERO",
    '"REALIZADO\n"',       # con comillas literales
    "COMENTARIO",
    "HECHO",
    "PREINFORME",
    "CANCELADO",
    "RMN GUARDIA",
    "RMN INTERNADO",
    "TC GUARDIA ",         # ojo: espacio al final
    "TC INTERNADOS ",      # ojo: espacio al final
    "DEMORA CAMILLERO",
    "DEMORA PEDIDO",
]

# Etiquetas del checklist operativo (fila X+.., al final)
ETIQUETAS_CHECKLIST = {
    "NOMBRE", "CARRO DE PARO", "BRIEF ", "ARCHIVOS DIGITALIZADOS",
    "MAIL GENERAL", "MAIL ESTUDIOS PREVIOS",
    "CONSENTIMIENTOS Y PLANILLAS TC", "CONSENTIMIENTOS Y PLANILLAS RM",
    "ORDENES TC", "ORDENES RM", "CONTEO TC ", "CONTEO RM",
    "RECONSTRUCCIONES", "PLANILLA ACV",
}

# Etiquetas del bloque de resumen
ETIQUETAS_RESUMEN = {"GUARDIA", "INTERNADOS", "AMBULATORIOS"}

ESTUDIOS_VALIDOS = {"TC", "RMN", "RX", "ECO"}


# ──────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────

def _pad(fila, n=N_COLUMNAS):
    """Normaliza una fila a exactamente n columnas (padding/truncado)."""
    return (list(fila) + [""] * n)[:n]


# ──────────────────────────────────────────────────────────────────────
# Tests de estructura fija (filas 0-2)
# ──────────────────────────────────────────────────────────────────────

def test_fila_0_titulo_operativo():
    vr = fixture_pestania("3105")
    fila = _pad(vr["values"][0])
    assert fila[0] == TITULO_OPERATIVO
    assert fila[1] == "PLANILLA GUARDIA"
    # resto vacío
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
        f"Header no coincide.\n"
        f"  Esperado: {HEADER_ESPERADO}\n"
        f"  Obtenido: {fila}"
    )


# ──────────────────────────────────────────────────────────────────────
# Tests de columnas
# ──────────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("nombre", ["3105", "3005", "2905"])
def test_todas_las_filas_tienen_21_columnas(nombre):
    vr = fixture_pestania(nombre)
    for i, fila in enumerate(vr["values"]):
        assert len(fila) <= N_COLUMNAS, (
            f"Fila {i} de {nombre!r} tiene {len(fila)} columnas > {N_COLUMNAS}"
        )


# ──────────────────────────────────────────────────────────────────────
# Tests del invariante "estudio → paciente"
# ──────────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("nombre", ["3105", "3005", "2905"])
def test_estudio_implica_paciente(nombre):
    """
    Invariante: si una fila tiene ESTUDIO válido, debe tener PACIENTE.
    El recíproco NO se cumple (residuales tienen paciente sin estudio).
    """
    vr = fixture_pestania(nombre)
    for i, fila_raw in enumerate(vr["values"]):
        if i < 3:
            continue  # filas 0-2 son fijas
        fila = _pad(fila_raw)
        estudio = str(fila[4]).strip() if fila[4] is not None else ""
        paciente = str(fila[1]).strip() if fila[1] is not None else ""
        if estudio in ESTUDIOS_VALIDOS:
            assert paciente, (
                f"Fila {i} de {nombre!r}: estudio={estudio!r} pero sin paciente. "
                f"Fila completa: {fila}"
            )


# ──────────────────────────────────────────────────────────────────────
# Tests de bloques especiales
# ──────────────────────────────────────────────────────────────────────

def test_bloque_resumen_presente():
    vr = fixture_pestania("3105")
    etiquetas = {
        str(_pad(f)[1]).strip()
        for f in vr["values"][3:]
        if _pad(f)[1]
    }
    assert "GUARDIA" in etiquetas, (
        f"Falta 'GUARDIA' en el bloque de resumen. Etiquetas: {etiquetas}"
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
    # al menos 5 etiquetas del checklist deben estar
    encontradas = etiquetas & ETIQUETAS_CHECKLIST
    assert len(encontradas) >= 5, (
        f"Faltan etiquetas del checklist. "
        f"Encontradas: {encontradas}, esperadas al menos 5 de {ETIQUETAS_CHECKLIST}"
    )
    # las más importantes
    assert "CARRO DE PARO" in etiquetas
    assert "PLANILLA ACV" in etiquetas


def test_residuales_tienen_estructura_correcta():
    """
    Las residuales del modelo son filas vacías con FALSE x4 y 0:00:00 / -.
    No deben tener conteos aleatorios.
    """
    vr = fixture_pestania("3105")
    residuales = []
    for i, fila_raw in enumerate(vr["values"]):
        if i < 3:
            continue
        fila = _pad(fila_raw)
        # residual: paciente vacío O paciente con FALSE/FALSE en cols 2-3
        # y sin estudio
        if not fila[1] and any(fila[11:15]):
            residuales.append(fila)

    # al menos una residual en la pestaña (perfil realista)
    assert len(residuales) > 0, "No se encontraron residuales en 3105"

    for fila in residuales[:3]:  # chequear las primeras 3
        # cols L-O = FALSE/FALSE/FALSE/FALSE
        assert fila[11:15] == ["FALSE", "FALSE", "FALSE", "FALSE"], (
            f"Residual con estructura incorrecta en cols L-O: {fila[11:15]}"
        )
        # cols T-U = 0:00:00 / -
        assert fila[19] == "0:00:00", f"Col T (DEMORA CAMILLERO): {fila[19]!r}"
        assert fila[20] == "-", f"Col U (DEMORA PEDIDO): {fila[20]!r}"


# ──────────────────────────────────────────────────────────────────────
# Tests de tipos de pestaña
# ──────────────────────────────────────────────────────────────────────

def test_hay_pestanias_no_guardia():
    result, nombres_guardia = FIXTURE_REALISTA
    n_total = len(result["valueRanges"])
    n_guardia = len(nombres_guardia)
    n_no_guardia = n_total - n_guardia
    assert n_no_guardia > 0, "El fixture realista no tiene pestañas no-guardia"
    # los nombres de no-guardia NO están en nombres_guardia
    nombres_no_guardia = {
        vr["range"].split("!")[0].strip("'")
        for vr in result["valueRanges"]
    } - set(nombres_guardia)
    assert nombres_no_guardia, "No hay nombres no-guardia"


# ──────────────────────────────────────────────────────────────────────
# Test de determinismo
# ──────────────────────────────────────────────────────────────────────

def test_fixture_es_determinista():
    """Mismo seed → mismo output. Sin esto, los fixtures no sirven para CI."""
    from src.synthetic import generar_para_fase1
    r1, n1 = generar_para_fase1(profile="realista", seed=42)
    r2, n2 = generar_para_fase1(profile="realista", seed=42)
    assert n1 == n2
    assert len(r1["valueRanges"]) == len(r2["valueRanges"])
    for vr1, vr2 in zip(r1["valueRanges"], r2["valueRanges"]):
        assert vr1["range"] == vr2["range"]
        assert vr1["values"] == vr2["values"]