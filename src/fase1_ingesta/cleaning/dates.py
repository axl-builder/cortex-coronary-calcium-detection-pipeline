import re
from datetime import date


# ──────────────────────────────────────────────────────────────────────
# Utilidades de parsing
# ──────────────────────────────────────────────────────────────────────

def candidatos_dia_mes(nombre: str) -> list[tuple[int, int]]:
    """
    Dado un nombre de pestaña numérico, devuelve las interpretaciones
    válidas (día, mes) posibles.

    Caso canónico: si el nombre tiene exactamente 4 dígitos, se interpreta
    como DDMM (dos dígitos de día + dos de mes). Esto elimina la ambigüedad
    de '0305' → [(3, 5)] en lugar de [(30, 5), (3, 5)].

    Para nombres de otra longitud (3 dígitos: '205', 2 dígitos: '31'), se
    generan todas las particiones válidas. El resto de la heurística
    (continuidad de secuencia) resuelve la ambigüedad.
    """
    nombre = nombre.strip()
    if not nombre.isdigit():
        return []

    # ── Caso canónico DDMM: exactamente 4 dígitos ──
    if len(nombre) == 4:
        dia, mes = int(nombre[:2]), int(nombre[2:])
        if 1 <= dia <= 31 and 1 <= mes <= 12:
            return [(dia, mes)]
        return []  # 4 dígitos pero combinación inválida (ej. '0000', '3213')

    # ── Fallback: 1-3 dígitos → todas las particiones válidas ──
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
    Construye la fecha del candidato ajustando el año si la secuencia
    cruza el cambio de año (ej. desc: enero → diciembre del año anterior).
    Devuelve None si la combinación día/mes/año es inválida.
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
    Si ningún candidato respeta la continuidad esperada (delta <= max_delta_dias),
    elegimos el candidato cuya fecha esté más cerca de fecha_prev (delta absoluto
    mínimo). Si no hay fecha_prev, caemos al primer candidato (mayor día).
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
# Parsing de la secuencia
# ──────────────────────────────────────────────────────────────────────

def parsear_secuencia(nombres: list[str],
                      anio_inicial: int,
                      orden: str = "desc",
                      fechas_manuales: dict | None = None,
                      max_delta_dias: int = 10) -> list[date | None]:
    """
    Asigna una fecha a cada nombre de pestaña resolviendo la ambigüedad
    DDMM por continuidad de la secuencia.

    Reglas:
      1. Si el nombre está en `fechas_manuales`, se usa esa fecha.
      2. Si tiene 4 dígitos → interpretación DDMM canónica (sin ambigüedad).
      3. Si tiene menos dígitos → se prueban todas las particiones y gana
         el candidato que produce un `delta` de días pequeño respecto a la
         fecha anterior (secuencia diaria).
      4. Si ningún candidato respeta la continuidad, se elige el más cercano
         en fecha (delta absoluto mínimo).

    Devuelve una lista alineada con `nombres` (None donde no se pudo parsear).
    """
    fechas_manuales = fechas_manuales or {}
    fechas: list[date | None] = []
    anio = anio_inicial
    fecha_prev: date | None = None

    for nombre in nombres:
        # ── Caso 1: fecha manual inyectada desde config ──
        if nombre in fechas_manuales:
            f = fechas_manuales[nombre]
            fechas.append(f)
            fecha_prev = f
            anio = f.year
            continue

        # ── Caso 2: intentar parsear ──
        cands = candidatos_dia_mes(nombre)
        if not cands:
            fechas.append(None)
            continue

        # Sin fecha previa: no hay contexto para desempatar.
        # Si hay un solo candidato (caso DDMM canónico), lo tomamos.
        # Si hay varios, tomamos el primero (mayor día) y avisamos vía auditoría.
        if fecha_prev is None:
            f = _fallback_candidato(cands, None, anio, orden)
            fechas.append(f)
            fecha_prev = f
            if f is not None:
                anio = f.year
            continue

        # ── Con fecha previa: buscar el candidato con delta pequeño ──
        mejor_f, mejor_delta = None, None
        for dia, mes in cands:
            f = _fecha_para_candidato(dia, mes, anio, fecha_prev, orden)
            if f is None:
                continue
            # delta positivo y chico = buena continuidad (secuencia diaria)
            if orden == "desc":
                delta = (fecha_prev - f).days
            else:
                delta = (f - fecha_prev).days
            # descartamos deltas <= 0 (desorden) o demasiado grandes (hueco)
            if delta <= 0 or delta > max_delta_dias:
                continue
            # menor delta = mejor; desempate por menor día (más conservador)
            if mejor_delta is None or delta < mejor_delta:
                mejor_delta, mejor_f = delta, f

        # ── Fallback: ningún candidato respeta continuidad ──
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
# Auditoría
# ──────────────────────────────────────────────────────────────────────

def auditar_secuencia(nombres: list[str],
                     fechas: list[date | None],
                     orden: str = "desc",
                     max_hueco_esperado: int = 1) -> dict:
    """
    Reporta problemas de la secuencia de fechas:
      - sin_fecha: pestañas que no se pudieron parsear.
      - desorden: pares consecutivos que rompen el orden esperado.
      - huecos: diferencias > max_hueco_esperado entre consecutivos.
      - ambiguos: pestañas cuyo nombre admitía más de una interpretación.
      - inferidas: pestañas donde el año se ajustó por cruce de año.
    """
    problemas = {
        "sin_fecha": [],
        "desorden": [],
        "huecos": [],
        "ambiguos": [],
    }

    # Detectar nombres ambiguos (más de un candidato válido)
    for n in nombres:
        cands = candidatos_dia_mes(n)
        if len(cands) > 1:
            problemas["ambiguos"].append((n, cands))

    # Detectar sin_fecha
    for n, f in zip(nombres, fechas):
        if f is None:
            problemas["sin_fecha"].append(n)

    # Detectar desorden y huecos
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