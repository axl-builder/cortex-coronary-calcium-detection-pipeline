"""
Generador de planillas sintéticas que replica la estructura REAL de la
planilla de guardia (no la versión limpia con pandas).

Estructura por pestaña de guardia:
  fila 0:   ["HACER CONTEO...", "PLANILLA GUARDIA", "", ...]  ← título operativo
  fila 1:   ["CHECKLIST", "", ...]                            ← fila checklist
  fila 2:   ["", "PACIENTE", "SECTOR", "HAB", "ESTUDIO", ...] ← header real
  fila 3..N: ["comentario", "Nombre Paciente", "SHOCK", "119", "TC", ...]
  fila N+1..: [residuales con FALSE x4 + 0:00:00 + -]
  ...:      bloque de resumen + checklist operativo

Pestañas no-guardia (portada, conteos) al principio, ignoradas por el pipeline.
Pestañas con fecha manual (ej. "Hoja 161") son opcionales, se pasan por parámetro.
"""

import csv
import random
from datetime import date, timedelta
from pathlib import Path

from .profiles import PROFILES
from .templates import (
    construir_plantilla_vacia,
    fila_residual,
    bloque_resumen,
    CHECKLIST_OPERATIVO,
    N_RESIDUALES,
)


# ──────────────────────────────────────────────────────────────────────
# Vocabularios
# ──────────────────────────────────────────────────────────────────────

_NOMBRES = ["Juan", "María", "Carlos", "Ana", "Luis", "Sofía", "Diego",
            "Laura", "Pedro", "Lucía", "Martín", "Valentina", "Jorge", "Camila"]
_APELLIDOS = ["Gómez", "Rodríguez", "Pérez", "Fernández", "López", "Martínez",
              "Sánchez", "Díaz", "Romero", "Torres", "Álvarez", "Ruiz"]

_SECTORES = ["SHOCK", "PISO", "DEMANDA", "UTI", "GUARDIA"]
_ESTUDIOS = ["TC", "RMN", "RX", "ECO"]
_REGIONES_TC = ["cerebro", "tx", "abd y pelvis", "tórax", "urotc",
                "angiotc tep", "protocolo tep", "caderas", "muñeca izq",
                "rodilla der", "columna lumbar", "cerebro , pelvis mmiis"]
_REGIONES_RMN = ["cerebro", "columna lumbosacra", "angiormn de cerebro",
                 "cerebro con difusión", "rodilla der"]

_CONTRASTES_SIN = ["NO", "SEDACION"]
_CONTRASTES_CON = ["SI", "DOBLE", "EVENTUAL", "ORAL"]
_CONTRASTES_COMPUESTOS = ["NO, EVENTUAL", "NO, SEDACION", "SI, NO",
                          "DOBLE, ORAL", "NO, DOBLE"]

_MOTIVOS = [
    "Caída de propia altura con traumatismo en hemicuerpo",
    "Sospecha de TEP, dímero D elevado",
    "Cuadro de fiebre, tos y disnea de 5 días de evolución",
    "Control de NAC",
    "Sospecha de apendicitis",
    "TEC sin pérdida de conocimiento",
    "Lumbalgia crónica por discopatía",
    "Insuficiencia cardíaca y sospecha de NAC",
    "Sospecha de abdomen agudo",
    "Paciente con disnea y dímero D de 1.86",
]

_COMENTARIOS_CHECKLIST = [
    "CHECKLIST", "PONER TODOS LOS COMENTARIOS",
    "MELI OK 19HS - AYUNO INDICADO Y TODO AVISADO",
    "listo p corregir", "VARIANTE ANATOMICA",
    "revisar con staff", "pendiente informe", "",
]

_BOOLS_VALIDOS = ["TRUE", "FALSE"]
_BOOLS_RAROS = ["True", "False", "Si", "No", "1", "0", ""]

_NOMBRES_PORTADA = ["PORTADA", "INICIO", "CONFIG", "LEEME"]
_NOMBRES_CONTEOS = ["CONTEOS", "RESUMEN", "ESTADISTICAS", "METRICAS"]


# ──────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────

def _nombre_completo(rng):
    return f"{rng.choice(_NOMBRES)} {rng.choice(_APELLIDOS)}"


def _hora(rng, perfil):
    h, m = rng.randint(0, 23), rng.randint(0, 59)
    if rng.random() < perfil["prob_nan_literal"]:
        return "NaN"
    fmt = rng.choice(["HH:MM:SS", "H,MM", "HH:MM"])
    if fmt == "HH:MM:SS":
        return f"{h:02d}:{m:02d}:00"
    if fmt == "H,MM":
        return f"{h},{m:02d}"
    return f"{h:02d}:{m:02d}"


def _bool(rng, perfil):
    if rng.random() < perfil["prob_bool_raro"]:
        return rng.choice(_BOOLS_RAROS)
    return rng.choice(_BOOLS_VALIDOS)


def _contraste(rng, perfil):
    if rng.random() < perfil["prob_contraste_compuesto"]:
        return rng.choice(_CONTRASTES_COMPUESTOS)
    if rng.random() < perfil["prob_contraste_sin"]:
        return rng.choice(_CONTRASTES_SIN)
    return rng.choice(_CONTRASTES_CON)


def _region(rng, estudio, perfil):
    if estudio == "TC" and rng.random() < perfil["prob_region_torax"]:
        return rng.choice(["tx", "tórax", "TX", "torax"])
    if estudio == "TC":
        return rng.choice(_REGIONES_TC)
    if estudio == "RMN":
        return rng.choice(_REGIONES_RMN)
    return rng.choice(_REGIONES_TC + _REGIONES_RMN)


# ──────────────────────────────────────────────────────────────────────
# Generación de filas
# ──────────────────────────────────────────────────────────────────────

def _fila_guardia(rng, perfil, idx):
    if rng.random() < perfil["prob_fila_vacia"]:
        return [""] * 15

    estudio = "TC" if rng.random() < perfil["prob_estudio_tc"] else rng.choice(_ESTUDIOS)
    region = _region(rng, estudio, perfil)
    contraste = _contraste(rng, perfil)

    comentario = ""
    if rng.random() < perfil["prob_comentario_checklist"]:
        comentario = rng.choice(_COMENTARIOS_CHECKLIST)

    fila = [
        comentario, _nombre_completo(rng), rng.choice(_SECTORES),
        f"{rng.randint(1, 500)}", estudio, region, contraste,
        rng.choice(_MOTIVOS), _hora(rng, perfil), _hora(rng, perfil),
        _hora(rng, perfil), _bool(rng, perfil), _bool(rng, perfil),
        _bool(rng, perfil), _bool(rng, perfil),
    ]

    if rng.random() < perfil["prob_fila_corta"]:
        return fila[: rng.randint(1, 10)]
    return fila


def _columnas_conteo(rng, n):
    return [rng.choice(["NaN", str(rng.randint(0, 20)), "-"]) for _ in range(n)]


# ──────────────────────────────────────────────────────────────────────
# Pestaña de guardia (genérica, sirve para DDMM y para fecha manual)
# ──────────────────────────────────────────────────────────────────────

def _pestania_guardia(rng, perfil, nombre):
    n_datos = rng.randint(*perfil["filas_por_pestania"])
    plantilla = construir_plantilla_vacia()

    filas = list(plantilla[:3])

    n_tc = 0
    n_rmn = 0
    for i in range(n_datos):
        fila = _fila_guardia(rng, perfil, i)
        if rng.random() < perfil["prob_fila_corta"]:
            fila = fila[: rng.randint(1, 14)]
        else:
            fila = fila + _columnas_conteo(rng, 6)
            if len(fila) > 4:
                if fila[4] == "TC":
                    n_tc += 1
                elif fila[4] == "RMN":
                    n_rmn += 1
        filas.append(fila)

    if rng.random() < perfil.get("prob_fila_residual", 0.0):
        for _ in range(max(0, N_RESIDUALES - n_datos)):
            filas.append(fila_residual())

    filas.extend(bloque_resumen(tc_guardia=n_tc, rmn_guardia=n_rmn))
    filas.extend(CHECKLIST_OPERATIVO)
    filas = [(f + [""] * 21)[:21] for f in filas]

    return {"range": f"'{nombre}'!A:U", "values": filas}


# ──────────────────────────────────────────────────────────────────────
# Pestañas no-guardia
# ──────────────────────────────────────────────────────────────────────

def _pestania_portada(rng, nombre):
    values = [
        [f"PLANILLA DE GUARDIA - {nombre}"], [""],
        ["Última actualización:", "2026-05-31"],
        ["Responsable:", "Dr. " + _nombre_completo(rng).split()[1]],
        [""], ["INSTRUCCIONES"],
        ["1. Completar una fila por paciente."],
        ["2. No borrar el header."],
        ["3. Consultar dudas al staff."],
    ]
    return {"range": f"'{nombre}'!A:O", "values": values}


def _pestania_conteos(rng, nombre):
    header = ["MES", "TC GUARDIA", "TC INTERNADOS", "RMN GUARDIA",
              "RMN INTERNADOS", "TOTAL"]
    values = [header]
    for mes in ["ENERO", "FEBRERO", "MARZO", "ABRIL", "MAYO"]:
        tcg, tci = rng.randint(50, 200), rng.randint(30, 150)
        rmg, rmi = rng.randint(10, 80), rng.randint(5, 40)
        values.append([mes, str(tcg), str(tci), str(rmg), str(rmi),
                       str(tcg + tci + rmg + rmi)])
    return {"range": f"'{nombre}'!A:O", "values": values}


# ──────────────────────────────────────────────────────────────────────
# Nombres de pestaña
# ──────────────────────────────────────────────────────────────────────

def _nombres_guardia(rng, fecha_fin, n, perfil):
    nombres = []
    fecha = fecha_fin
    for _ in range(n):
        dd, mm = fecha.day, fecha.month
        canonico = f"{dd:02d}{mm:02d}"
        if rng.random() < perfil["prob_nombre_pestania_ambiguo"] and dd < 10:
            nombres.append(f"{dd}{mm:02d}")
        else:
            nombres.append(canonico)
        fecha -= timedelta(days=1)
    return nombres


# ──────────────────────────────────────────────────────────────────────
# API pública
# ──────────────────────────────────────────────────────────────────────

def generar_planilla_sintetica(profile: str = "realista",
                               seed: int = 42,
                               fecha_fin: date | None = None,
                               n_pestanias_guardia: int | None = None,
                               pestanias_con_fecha_manual: list[str] | None = None,
                               ) -> tuple[dict, list[str]]:
    """
    Genera una planilla sintética con la estructura REAL.

    Args:
        pestanias_con_fecha_manual: nombres de pestañas que NO siguen el
            patrón DDMM y tienen fecha fija en `settings.dates.fechas_manuales`
            (ej. `["Hoja 161"]`). Se agregan al principio del bloque de guardia.
            Si es None, no se agrega ninguna.

    Returns:
        (result, nombres_seleccionados) donde `nombres_seleccionados` son
        las pestañas que `fetch_selected_sheets` seleccionaría: las DDMM
        + las de fecha manual, en el orden en que aparecen en el spreadsheet.
    """
    if profile not in PROFILES:
        raise ValueError(f"Perfil desconocido: {profile!r}. "
                         f"Válidos: {sorted(PROFILES)}")
    perfil = PROFILES[profile]
    rng = random.Random(seed)
    fecha_fin = fecha_fin or date(2026, 5, 31)
    n_guardia = n_pestanias_guardia or perfil["pestanias_guardia"]
    n_no_guardia = perfil["pestanias_no_guardia"]
    pestanias_con_fecha_manual = pestanias_con_fecha_manual or []

    value_ranges = []

    # 1. No-guardia al principio
    n_portada = min(2, n_no_guardia)
    n_conteos = max(0, n_no_guardia - n_portada)
    for i in range(n_portada):
        value_ranges.append(_pestania_portada(rng, _NOMBRES_PORTADA[i % len(_NOMBRES_PORTADA)]))
    for i in range(n_conteos):
        value_ranges.append(_pestania_conteos(rng, _NOMBRES_CONTEOS[i % len(_NOMBRES_CONTEOS)]))

    # 2. Pestañas con fecha manual (opcionales, genéricas)
    for nombre in pestanias_con_fecha_manual:
        value_ranges.append(_pestania_guardia(rng, perfil, nombre))

    # 3. Guardias DDMM
    nombres_guardia = _nombres_guardia(rng, fecha_fin, n_guardia, perfil)
    for nombre in nombres_guardia:
        value_ranges.append(_pestania_guardia(rng, perfil, nombre))

    # 4. Selección: DDMM + manuales (en el orden del spreadsheet)
    nombres_seleccionados = list(nombres_guardia) + list(pestanias_con_fecha_manual)

    return {"valueRanges": value_ranges}, nombres_seleccionados


def generar_para_fase1(profile: str = "realista",
                       seed: int = 42,
                       fecha_fin: date | None = None,
                       n_pestanias_guardia: int | None = None,
                       pestanias_con_fecha_manual: list[str] | None = None,
                       ) -> tuple[dict, list[str]]:
    """Alias con nombre explícito del contexto."""
    return generar_planilla_sintetica(
        profile, seed, fecha_fin, n_pestanias_guardia, pestanias_con_fecha_manual,
    )


# ──────────────────────────────────────────────────────────────────────
# Export CSV
# ──────────────────────────────────────────────────────────────────────

def exportar_csv(result: dict, out_dir: Path) -> list[Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    paths = []
    for vr in result["valueRanges"]:
        nombre = vr["range"].split("!")[0].strip("'")
        safe = "".join(c if c.isalnum() or c in " _-" else "_" for c in nombre)
        path = out_dir / f"{safe}.csv"
        with open(path, "w", encoding="utf-8", newline="") as f:
            csv.writer(f).writerows(vr["values"])
        paths.append(path)
    return paths