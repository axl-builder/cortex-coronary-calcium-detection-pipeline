"""CLI for the synthetic data generator.

Usage:
    python -m src.synthetic --profile realista --seed 42
    python -m src.synthetic --profile realista --seed 42 --format xlsx
    python -m src.synthetic --profile caotico --seed 7 --format all
"""

import argparse
from datetime import date, datetime
from pathlib import Path

from .generator import generar_planilla_sintetica
from .exporters import exportar_csv, exportar_xlsx, exportar_json, exportar_todo


def _nombre_base(profile: str, seed: int, fecha: date | None) -> str:
    """Base name for exported files: 'CORTEX - Planilla MOCK {profile} seed{seed} {fecha}'."""
    fecha_str = (fecha or datetime.now().date()).isoformat()
    return f"CORTEX - Planilla MOCK {profile} seed{seed} {fecha_str}"


def main():
    parser = argparse.ArgumentParser(prog="synthetic")
    parser.add_argument("--profile", default="realista",
                        choices=["minimo", "realista", "caotico"])
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--n-pestanias-guardia", type=int, default=None)
    parser.add_argument("--fecha-fin", type=date.fromisoformat, default=None)
    parser.add_argument("--pestanias-fecha-manual", nargs="*", default=None,
                        help="Tab names with a manual date (e.g. 'Hoja 161')")  # TODO: layer 2
    parser.add_argument("--out", type=Path, default=Path("data/synthetic"))
    parser.add_argument("--format", default="all",
                        choices=["csv", "xlsx", "json", "all"])
    args = parser.parse_args()

    result, nombres = generar_planilla_sintetica(
        profile=args.profile,
        seed=args.seed,
        fecha_fin=args.fecha_fin,
        n_pestanias_guardia=args.n_pestanias_guardia,
        pestanias_con_fecha_manual=args.pestanias_fecha_manual,
    )

    n_total = len(result["valueRanges"])
    n_guardia = len(nombres)
    n_no_guardia = n_total - n_guardia

    print(f"Generated {n_total} tabs:")  # TODO: layer 2
    print(f"  - {n_no_guardia} non-on-call (ignored by Phase 1)")  # TODO: layer 2
    print(f"  - {n_guardia} on-call (processed by Phase 1)")  # TODO: layer 2
    print(f"Profile: {args.profile}, seed: {args.seed}")  # TODO: layer 2
    if nombres:
        print(f"First tabs: {nombres[:5]}")  # TODO: layer 2
        print(f"Last tabs:  {nombres[-5:]}")  # TODO: layer 2

    nombre_base = _nombre_base(args.profile, args.seed, args.fecha_fin)

    if args.format == "all":
        args.out.mkdir(parents=True, exist_ok=True)
        csv_paths = exportar_csv(result, args.out / "csv")
        xlsx_path = exportar_xlsx(result, args.out / f"{nombre_base}.xlsx")
        json_path = exportar_json(result, args.out / f"{nombre_base}.json")
        print(f"\nExported:")  # TODO: layer 2
        print(f"  xlsx:  {xlsx_path}")  # TODO: layer 2
        print(f"  json:  {json_path}")  # TODO: layer 2
        print(f"  csv:   {args.out / 'csv'}/ ({len(csv_paths)} files)")  # TODO: layer 2
    elif args.format == "csv":
        paths = exportar_csv(result, args.out / "csv")
        print(f"\nCSV: {args.out / 'csv'}/ ({len(paths)} files)")  # TODO: layer 2
    elif args.format == "xlsx":
        args.out.mkdir(parents=True, exist_ok=True)
        path = exportar_xlsx(result, args.out / f"{nombre_base}.xlsx")
        print(f"\nXLSX: {path}")  # TODO: layer 2
    elif args.format == "json":
        args.out.mkdir(parents=True, exist_ok=True)
        path = exportar_json(result, args.out / f"{nombre_base}.json")
        print(f"\nJSON: {path}")  # TODO: layer 2


if __name__ == "__main__":
    main()