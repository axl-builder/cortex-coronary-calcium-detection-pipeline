from datetime import date
import logging

from .dates import parsear_secuencia, auditar_secuencia
from .filters import es_tc, menciona_torax, evaluar_contraste
from .guards import pestaña_tiene_datos, clasificar_fila
from .normalize import parsear_bool_mayus, formatear_bool, limpiar_celda

log = logging.getLogger("cortex")


def transform_sheets(result: dict, nombres: list[str], settings: dict):
    """
    Recorre `result` aplicando guardias y filtros.
    Devuelve (filas, stats, problemas, fechas).
    Cada fila es una lista lista para escribir al CSV (incluye fecha al inicio).
    """
    dates_cfg = settings["dates"]
    cols_cfg = settings["columns"]
    filt_cfg = settings["contraste"]
    filas_a_saltear = settings["sheets"]["filas_a_saltear"]

    fechas_manuales = {
        k: date.fromisoformat(v)
        for k, v in dates_cfg.get("fechas_manuales", {}).items()
    }

    fechas = parsear_secuencia(
        nombres,
        anio_inicial=dates_cfg["anio_inicial"],
        orden=dates_cfg["orden"],
        fechas_manuales=fechas_manuales,
    )
    problemas = auditar_secuencia(
        nombres, fechas, orden=dates_cfg["orden"],
        max_hueco_esperado=dates_cfg["max_hueco_esperado"],
    )

    columnas = [
        cols_cfg["paciente"], cols_cfg["estudio"],
        cols_cfg["region"], cols_cfg["contraste"],
    ]
    max_col = cols_cfg["max_col"]
    sin_set = set(filt_cfg["sin"])
    con_set = set(filt_cfg["con"])
    incluir = frozenset(filt_cfg.get("incluir", ["sin_contraste"]))
    politica = dates_cfg.get("politica_sin_fecha", "sin_fecha")

    # Validación fail-fast: si `incluir` tiene valores fuera del vocabulario
    # de `evaluar_contraste`, el pipeline no arranca.
    _VALIDOS = {"sin_contraste", "con_contraste", "desconocido"}
    _invalidos = set(incluir) - _VALIDOS
    if _invalidos:
        raise SystemExit(
            f"config/settings.yaml: 'contraste.incluir' has invalid values: "
            f"{sorted(_invalidos)}. Valid: {sorted(_VALIDOS)}"
        )

    log.info(f"[config efectiva] incluir={set(incluir)} sin={sin_set} con={con_set}")

    # stats: contrato con Fase 3 (PRISMA flowchart).
    # Solo números agregados, NO estado de debugging.
    stats = {
        "ok": 0, "sin_datos": 0, "sin_fecha_omitida": 0, "sin_fecha_incluida": 0,
        "filas": 0, "filas_vacias": 0, "filas_cortas": 0,
        "estados_desconocidos": 0, "inconsistencias_estado": 0,
        "filtradas_no_tc": 0, "filtradas_sin_torax": 0,
        "incluidas_sin_contraste": 0,
        "incluidas_con_contraste": 0,
        "incluidas_desconocido": 0,
        "descartadas_sin_contraste": 0,
        "descartadas_con_contraste": 0,
        "descartadas_desconocido": 0,
    }

    filas_salida = []
    diag_count = 0  # variable local, NO en stats

    for attributes, nombre, fecha in zip(result.get("valueRanges", []), nombres, fechas):
        if not pestaña_tiene_datos(attributes, filas_a_saltear):
            stats["sin_datos"] += 1
            continue

        if fecha is None:
            if politica == "omitir":
                stats["sin_fecha_omitida"] += 1
                continue
            elif politica == "nombre":
                fecha_str = nombre
            else:
                fecha_str = ""
            stats["sin_fecha_incluida"] += 1
        else:
            fecha_str = fecha.isoformat()
            stats["ok"] += 1

        for fila in attributes.get("values", [])[filas_a_saltear:]:
            motivo = clasificar_fila(fila, columnas, max_col)
            if motivo == "corta":
                stats["filas_cortas"] += 1
                continue
            if motivo == "vacia":
                stats["filas_vacias"] += 1
                continue

            v_estudio = fila[cols_cfg["estudio"]] if cols_cfg["estudio"] < len(fila) else ""
            if not es_tc(v_estudio):
                stats["filtradas_no_tc"] += 1
                continue

            v_region = fila[cols_cfg["region"]] if cols_cfg["region"] < len(fila) else ""
            if not menciona_torax(v_region):
                stats["filtradas_sin_torax"] += 1
                continue

            v_contraste_crudo = (
                limpiar_celda(fila[cols_cfg["contraste"]])
                if cols_cfg["contraste"] < len(fila) else ""
            )
            est = evaluar_contraste(v_contraste_crudo, sin_set, con_set)

            # diagnóstico: primeras 20 filas (variable local, no en stats)
            if diag_count < 20:
                log.info(
                    f"[diag] crudo={v_contraste_crudo!r} est={est!r} "
                    f"in={est in incluir} -> "
                    f"{'INCLUIDA' if est in incluir else 'DESCARTADA'}"
                )
                diag_count += 1

            if est not in incluir:
                stats[f"descartadas_{est}"] += 1
                continue
            stats[f"incluidas_{est}"] += 1

            fila_sel = [limpiar_celda(fila[i]) if i < len(fila) else "" for i in columnas]

            hecho_raw = fila[cols_cfg["hecho"]] if cols_cfg["hecho"] < len(fila) else ""
            preinforme = fila[cols_cfg["preinforme"]] if cols_cfg["preinforme"] < len(fila) else ""
            cancelado_raw = fila[cols_cfg["cancelado"]] if cols_cfg["cancelado"] < len(fila) else ""

            hecho = parsear_bool_mayus(hecho_raw)
            cancelado = parsear_bool_mayus(cancelado_raw)

            if hecho is None and str(hecho_raw).strip() != "":
                stats["estados_desconocidos"] += 1
            if cancelado is None and str(cancelado_raw).strip() != "":
                stats["estados_desconocidos"] += 1

            if hecho is True and cancelado is True:
                stats["inconsistencias_estado"] += 1

            filas_salida.append(
                [fecha_str] + fila_sel
                + [formatear_bool(hecho), limpiar_celda(preinforme), formatear_bool(cancelado)]
            )
            stats["filas"] += 1

    return filas_salida, stats, problemas, fechas