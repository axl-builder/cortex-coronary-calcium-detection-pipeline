from datetime import datetime
from src.common.io import write_csv, write_json
from src.common.logging_config import get_run_id, setup_logging
from src.common.paths import PROCESSED_DIR, LOG_DIR
from src.fase1_ingesta.config import load_settings
from src.fase1_ingesta.cleaning.transform import transform_sheets


def _nombre_sheet(run_id: str, mock: bool) -> str:
    """
    Name of the Sheet uploaded to Drive.
    Format: 'CORTEX - Resultados [MOCK] YYYY-MM-DD HHMM'
    """
    # run_id is 'YYYYMMDD_HHMMSS' → parse
    try:
        dt = datetime.strptime(run_id, "%Y%m%d_%H%M%S")
    except ValueError:
        dt = datetime.now()
    fecha = dt.strftime("%Y-%m-%d %H%M")
    marca = " MOCK" if mock else ""
    return f"CORTEX - Resultados{marca} {fecha}"


def run_fase1(upload: bool = True,
              mock: bool = False,
              mock_profile: str = "realista",
              mock_seed: int = 42) -> dict:
    run_id = get_run_id()
    log = setup_logging(run_id)
    settings = load_settings()

    # ── Extract ──
    if mock:
        log.info(f"Fase 1: MOCK ({mock_profile}, seed={mock_seed})")  # TODO: layer 2
        from src.synthetic import generar_para_fase1
        result, nombres = generar_para_fase1(
            profile=mock_profile,
            seed=mock_seed,
        )
    else:
        log.info("Fase 1: ingesta de Sheets")  # TODO: layer 2
        from src.fase1_ingesta.ingestion.sheets_client import fetch_selected_sheets
        result, nombres = fetch_selected_sheets(
            reciente=settings["sheets"]["reciente"],
            antigua=settings["sheets"]["antigua"],
        )
    log.info(f"Pestañas seleccionadas: {len(nombres)}")  # TODO: layer 2

    # ── Transform ──
    log.info("Fase 1: transformación")  # TODO: layer 2
    filas, stats, problemas, fechas = transform_sheets(result, nombres, settings)

    # ── Load (CSV) ──
    csv_path = PROCESSED_DIR / "result.csv"
    write_csv(csv_path, settings["header"], filas)
    log.info(f"CSV escrito: {csv_path} ({stats['filas']} filas)")  # TODO: layer 2

    resumen = {
        "run_id": run_id,
        "fase": 1,
        "mock": mock,
        "mock_profile": mock_profile if mock else None,
        "mock_seed": mock_seed if mock else None,
        "stats": stats,
        "problemas": {k: len(v) for k, v in problemas.items()},
    }
    write_json(LOG_DIR / f"resumen_{run_id}.json", resumen)

    for k, v in stats.items():
        log.info(f"{k}: {v}")

    # ── Load (Drive) ──
    if upload:
        sheet_name = _nombre_sheet(run_id, mock)
        log.info(f"Fase 1: subida a Drive como '{sheet_name}'")  # TODO: layer 2
        from src.fase1_ingesta.ingestion.sheet_uploader import upload_csv_as_sheet
        info = upload_csv_as_sheet(csv_path, sheet_name)
        log.info(f"Sheet: {info.get('webViewLink')}")
    elif mock:
        log.warning("MODO MOCK: se ignora la subida a Drive")  # TODO: layer 2

    log.info(f"=== FIN DE CORRIDA {run_id} ===")  # TODO: layer 2
    return stats