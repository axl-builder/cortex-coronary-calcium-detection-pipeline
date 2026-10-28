"""
Exportadores del mock a distintos formatos.

- exportar_csv: un CSV por pestaña (debug, diff con git)
- exportar_xlsx: un .xlsx con N hojas (replica la planilla real)
- exportar_json: un .json con el dict {'valueRanges': [...]} (para el pipeline)
"""

import csv
import json
from pathlib import Path


def exportar_csv(result: dict, out_dir: Path) -> list[Path]:
    """Un CSV por pestaña. Útil para inspección y diff con git."""
    out_dir.mkdir(parents=True, exist_ok=True)
    paths = []
    for vr in result["valueRanges"]:
        nombre = vr["range"].split("!")[0].strip("'")
        safe = "".join(c if c.isalnum() or c in " _-" else "_" for c in nombre)
        path = out_dir / f"{safe}.csv"
        with open(path, "w", encoding="utf-8", newline="") as f:
            w = csv.writer(f)
            w.writerows(vr["values"])
        paths.append(path)
    return paths


def exportar_xlsx(result: dict, out_path: Path, sheet_name_max: int = 31) -> Path:
    """
    Un solo .xlsx con N hojas, una por pestaña. Replica la planilla real.

    Requiere openpyxl (ya viene con pandas normalmente, si no:
    `uv add openpyxl` o `pip install openpyxl`).

    Nota: Excel limita los nombres de hoja a 31 caracteres y prohíbe
    ciertos caracteres (: \\ / ? * [ ]). Los sanitizamos.
    """
    from openpyxl import Workbook

    out_path.parent.mkdir(parents=True, exist_ok=True)
    wb = Workbook()
    # openpyxl crea una hoja "Sheet" por defecto: la usamos para la primera
    # pestaña o la eliminamos si no hay datos.
    first = True
    for vr in result["valueRanges"]:
        nombre = vr["range"].split("!")[0].strip("'")
        # sanitizar nombre de hoja
        safe = "".join(c if c.isalnum() or c in " _-" else "_" for c in nombre)
        safe = safe[:sheet_name_max] or f"hoja_{len(wb.sheetnames)}"
        # evitar duplicados
        base = safe
        i = 1
        while safe in wb.sheetnames:
            suffix = f"_{i}"
            safe = (base[: sheet_name_max - len(suffix)]) + suffix
            i += 1

        if first:
            ws = wb.active
            ws.title = safe
            first = False
        else:
            ws = wb.create_sheet(title=safe)

        for row in vr["values"]:
            ws.append(row)

    if first:
        # no había datos: dejar la hoja vacía
        wb.active.title = "vacio"

    wb.save(out_path)
    return out_path


def exportar_json(result: dict, out_path: Path) -> Path:
    """
    Un .json con el dict {'valueRanges': [...]}. Es el formato que consume
    el pipeline (mismo shape que `fetch_selected_sheets`). Ideal para
    fixtures de tests y para evitar re-generar con random.
    """
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    return out_path


def exportar_todo(result: dict, nombres: list[str], out_dir: Path) -> dict:
    """
    Exporta en los tres formatos a la vez. Devuelve un dict con los paths.
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    csv_paths = exportar_csv(result, out_dir / "csv")
    xlsx_path = exportar_xlsx(result, out_dir / "planilla_sintetica.xlsx")
    json_path = exportar_json(result, out_dir / "planilla_sintetica.json")
    return {
        "csv_dir": out_dir / "csv",
        "csv_files": csv_paths,
        "xlsx": xlsx_path,
        "json": json_path,
    }