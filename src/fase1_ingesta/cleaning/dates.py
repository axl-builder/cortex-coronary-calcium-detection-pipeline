import re
from datetime import date


# ──────────────────────────────────────────────────────────────────────
# Parsing utilities
# ──────────────────────────────────────────────────────────────────────

def candidatos_dia_mes(nombre: str) -> list[tuple[int, int]]:
    """
    Given a numeric tab name, return the valid (day, month) interpretations.

    Canonical case: if the name has exactly 4 digits, it is interpreted as
    DDMM (two digits for day + two for month). This removes the ambiguity of
    '0305' → [(3, 5)] instead of [(30, 5), (3, 5)].

    For names of other lengths (3 digits: '205', 2 digits: '31'), all valid
    partitions are generated. The rest of the heuristic (sequence continuity)
    resolves the ambiguity.
    """
    nombre = nombre.strip()
    if not nombre.isdigit():
        return []

    # ── Canonical DDMM case: exactly 4 digits ──
    if len(nombre) == 4:
        dia, mes = int(nombre[:2]), int(nombre[2:])
        if 1 <= dia <= 31 and 1 <= mes <= 12:
            return [(dia, mes)]
        return []  # 4 digits but invalid combination (e.g. '0000', '3213')

    # ── Fallback: 1-3 digits → all valid partitions ──
    cands = set()
    for k in range(1, len(nombre)):
        try:
            dia, mes = int(nombre[:k]), int(nombre[k:])
            if 1 <= dia <= 31 and 1 <= mes <= 12:
                cands.add((dia, mes))
        except ValueError:
            pass
    return sorted(cands, key=lambda x: (-x[0], x[1]))


def _fecha_para_candidato(dia: int, mes: int, anio: int,
                          fecha_prev: date | None, orden: str) -> date | None:
    """
    Build the candidate date, adjusting the year if the sequence crosses
    the year boundary (e.g. desc: January → December of the previous year).
    Return None if the day/month/year combination is invalid.
    """
    anio_tent = anio
    if fecha_prev is not None:
        if orden == "desc" and mes > fecha_prev.month:
            anio_tent -= 1
        elif orden == "asc" and mes < fecha_prev.month:
            anio_tent += 1
    try:
        return date(anio_tent, mes, dia)
    except ValueError:
        return None


def _fallback_candidato(cands: list[tuple[int, int]],
                        fecha_prev: date | None,
                        anio: int,
                        orden: str) -> date | None:
    """
    If no candidate satisfies the expected continuity (delta <= max_delta_dias),
    pick the candidate whose date is closest to fecha_prev (minimum absolute
    delta). If there is no fecha_prev, fall back to the first candidate
    (largest day).
    """
    if fecha_prev is None:
        for dia, mes in cands:
            f = _fecha_para_candidato(dia, mes, anio, None, orden)
            if f is not None:
                return f
        return None

    mejor, mejor_delta = None, float("inf")
    for dia, mes in cands:
        f = _fecha_para_candidato(dia, mes, anio, fecha_prev, orden)
        if f is None:
            continue
        delta = abs((f - fecha_prev).days)
        if delta < mejor_delta:
            mejor_delta, mejor = delta, f
    return mejor


# ──────────────────────────────────────────────────────────────────────
# Sequence parsing
# ──────────────────────────────────────────────────────────────────────

def parsear_secuencia(nombres: list[str],
                      anio_inicial: int,
                      orden: str = "desc",
                      fechas_manuales: dict | None = None,
                      max_delta_dias: int = 10) -> list[date | None]:
    """
    Assign a date to each tab name, resolving DDMM ambiguity via sequence
    continuity.

    Rules:
      1. If the name is in `fechas_manuales`, use that date.
      2. If it has 4 digits → canonical DDMM interpretation (no ambiguity).
      3. If it has fewer digits → try all partitions; the candidate that
         produces a small `delta` in days relative to the previous date
         (daily sequence) wins.
      4. If no candidate satisfies continuity, pick the closest in date
         (minimum absolute delta).

    Returns a list aligned with `nombres` (None where parsing failed).
    """
    fechas_manuales = fechas_manuales or {}
    fechas: list[date | None] = []
    anio = anio_inicial
    fecha_prev: date | None = None

    for nombre in nombres:
        # ── Case 1: manual date injected from config ──
        if nombre in fechas_manuales:
            f = fechas_manuales[nombre]
            fechas.append(f)
            fecha_prev = f
            anio = f.year
            continue

        # ── Case 2: try to parse ──
        cands = candidatos_dia_mes(nombre)
        if not cands:
            fechas.append(None)
            continue

        # No previous date: no context for tie-breaking.
        # If there is a single candidate (canonical DDMM), take it.
        # If there are several, take the first (largest day) and report via
        # the audit.
        if fecha_prev is None:
            f = _fallback_candidato(cands, None, anio, orden)
            fechas.append(f)
            fecha_prev = f
            if f is not None:
                anio = f.year
            continue

        # ── With a previous date: find the candidate with small delta ──
        mejor_f, mejor_delta = None, None
        for dia, mes in cands:
            f = _fecha_para_candidato(dia, mes, anio, fecha_prev, orden)
            if f is None:
                continue
            # positive and small delta = good continuity (daily sequence)
            if orden == "desc":
                delta = (fecha_prev - f).days
            else:
                delta = (f - fecha_prev).days
            # discard deltas <= 0 (out of order) or too large (gap)
            if delta <= 0 or delta > max_delta_dias:
                continue
            # smaller delta = better; tie-break by smaller day (more conservative)
            if mejor_delta is None or delta < mejor_delta:
                mejor_delta, mejor_f = delta, f

        # ── Fallback: no candidate satisfies continuity ──
        if mejor_f is None:
            mejor_f = _fallback_candidato(cands, fecha_prev, anio, orden)
            if mejor_f is None:
                fechas.append(None)
                continue

        fechas.append(mejor_f)
        fecha_prev = mejor_f
        anio = mejor_f.year

    return fechas


# ──────────────────────────────────────────────────────────────────────
# Audit
# ──────────────────────────────────────────────────────────────────────

def auditar_secuencia(nombres: list[str],
                     fechas: list[date | None],
                     orden: str = "desc",
                     max_hueco_esperado: int = 1) -> dict:
    """
    Report problems in the date sequence:
      - sin_fecha: tabs that could not be parsed.
      - desorden: consecutive pairs that break the expected order.
      - huecos: differences > max_hueco_esperado between consecutive tabs.
      - ambiguos: tabs whose name admitted more than one interpretation.
    """
    problemas = {
        "sin_fecha": [],
        "desorden": [],
        "huecos": [],
        "ambiguos": [],
    }

    # Detect ambiguous names (more than one valid candidate)
    for n in nombres:
        cands = candidatos_dia_mes(n)
        if len(cands) > 1:
            problemas["ambiguos"].append((n, cands))

    # Detect missing dates
    for n, f in zip(nombres, fechas):
        if f is None:
            problemas["sin_fecha"].append(n)

    # Detect out-of-order and gaps
    pares = [(n, f) for n, f in zip(nombres, fechas) if f is not None]
    for i in range(1, len(pares)):
        n_prev, f_prev = pares[i - 1]
        n_curr, f_curr = pares[i]
        if orden == "desc" and f_curr > f_prev:
            problemas["desorden"].append((n_prev, f_prev, n_curr, f_curr))
        elif orden == "asc" and f_curr < f_prev:
            problemas["desorden"].append((n_prev, f_prev, n_curr, f_curr))
        delta = abs((f_curr - f_prev).days)
        if delta > max_hueco_esperado:
            problemas["huecos"].append((n_prev, f_prev, n_curr, f_curr, delta))

    return problemas