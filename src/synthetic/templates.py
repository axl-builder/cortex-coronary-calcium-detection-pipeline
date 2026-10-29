"""
Plantilla `modelo`: estructura fija de una pestaña de guardia vacía.

Es la fuente de verdad de la estructura. Cualquier cambio en la planilla
real (agregar columna, cambiar un header) se refleja acá y el generador
la propaga a todas las pestañas.
"""

from datetime import time

# ── Fila 0: título operativo ──
TITULO_OPERATIVO = "HACER CONTEO DE PACIENTES Y REGIONES + MIRAR MAILS"

# ── Fila 1: "CHECKLIST" (col A), resto vacío ──
FILA_CHECKLIST = ["CHECKLIST"]

# ── Fila 2: header de la tabla de pacientes ──
# Ojo: col A vacía (es checklist), col B en adelante son las columnas de datos.
# Las comillas en "HORA\nPEDIDO" y "REALIZADO\n" son literales del CSV real.
HEADER_PACIENTES = [
    "",                      # col A (checklist operativo)
    "PACIENTE",              # col B
    "SECTOR",
    "HAB",
    "ESTUDIO",
    "REGION",
    "CONTRASTE ",            # ← ojo: espacio al final en el real
    "MOTIVO",
    '"HORA\nPEDIDO"',        # ← con comillas literales
    "HS LLAMADO CAMILLERO",
    '"REALIZADO\n"',         # ← con comillas literales
    "COMENTARIO",
    "HECHO",
    "PREINFORME",
    "CANCELADO",
    "RMN GUARDIA",
    "RMN INTERNADO",
    "TC GUARDIA ",
    "TC INTERNADOS ",
    "DEMORA CAMILLERO",
    "DEMORA PEDIDO",
]

# ── Filas residuales (vacías, con FALSE/FALSE/FALSE/FALSE y 0:00:00) ──
# En el modelo hay ~38 de estas. Son filas preparadas para llenar.
N_RESIDUALES = 38

def fila_residual() -> list[str]:
    """Una fila vacía del modelo, con la estructura de FALSE/FALSE y 0:00:00."""
    return [
        "", "", "", "", "", "", "", "", "", "", "",        # cols A-K vacías
        "FALSE", "FALSE", "FALSE", "FALSE",                 # cols L-O (HECHO..CANCELADO)
        "", "", "", "",                                     # cols P-S vacías
        "0:00:00", "-",                                     # cols T-U (DEMORA)
    ]

# ── Bloque de resumen (después de las residuales) ──
def bloque_resumen(tc_guardia: int = 0, rmn_guardia: int = 0,
                   tc_internados: int = 0, rmn_internados: int = 0) -> list[list[str]]:
    """Bloque de conteos agregados que aparece después de las residuales."""
    return [
        ["", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "0", "0", "0", "0"],
        [""],
        [""],
        ["", "", "TC", "RMN"],
        ["", "GUARDIA", str(tc_guardia), str(rmn_guardia)],
        ["", "INTERNADOS", str(tc_internados), str(rmn_internados)],
        ["", "", "TC", "RMN"],
        ["", "AMBULATORIOS", "0", "0"],
    ]

# ── Bloque de checklist operativo (al final) ──
CHECKLIST_OPERATIVO = [
    ["", "NOMBRE", "MAÑANA", "TARDE"],
    ["", "CARRO DE PARO", "FALSE", "FALSE"],
    ["", "BRIEF ", "FALSE", "FALSE"],
    ["", "ARCHIVOS DIGITALIZADOS", "FALSE", "FALSE"],
    ["", "MAIL GENERAL", "FALSE", "FALSE"],
    ["", "MAIL ESTUDIOS PREVIOS", "FALSE", "FALSE"],
    ["", "CONSENTIMIENTOS Y PLANILLAS TC", "FALSE", "FALSE"],
    ["", "CONSENTIMIENTOS Y PLANILLAS RM", "FALSE", "FALSE"],
    ["", "ORDENES TC", "FALSE", "FALSE"],
    ["", "ORDENES RM", "FALSE", "FALSE"],
    ["", "CONTEO TC ", "FALSE", "FALSE"],
    ["", "CONTEO RM", "FALSE", "FALSE"],
    ["", "RECONSTRUCCIONES", "FALSE", "FALSE"],
    ["", "PLANILLA ACV", "FALSE", "FALSE"],
]


def construir_plantilla_vacia() -> list[list[str]]:
    """Devuelve la plantilla `modelo` completa como lista de filas."""
    filas = []
    # fila 0: título operativo + "PLANILLA GUARDIA" en col B
    fila0 = [TITULO_OPERATIVO, "PLANILLA GUARDIA"] + [""] * 19
    filas.append(fila0)
    # fila 1: "CHECKLIST" en col A
    filas.append(FILA_CHECKLIST + [""] * 20)
    # fila 2: header de pacientes
    filas.append(HEADER_PACIENTES)
    # filas 3..3+N_RESIDUALES: residuales
    for _ in range(N_RESIDUALES):
        filas.append(fila_residual())
    # bloque de resumen
    filas.extend(bloque_resumen())
    # checklist operativo
    filas.extend(CHECKLIST_OPERATIVO)
    return filas