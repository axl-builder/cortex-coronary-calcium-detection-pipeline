import argparse
import sys


import argparse
import sys


def main():
    parser = argparse.ArgumentParser(prog="cortex")
    parser.add_argument("comando", choices=["fase1", "fase2", "fase3", "all"])
    parser.add_argument(
        "--no-upload",
        action="store_true",
        help="Fase 1: no subir el CSV a Drive",
    )
    parser.add_argument(
        "--mock",
        action="store_true",
        help="Usar datos sintéticos en vez de Google Sheets",
    )
    parser.add_argument(
        "--mock-profile",
        default="realista",
        choices=["minimo", "realista", "caotico"],
        help="Perfil del mock (default: realista)",
    )
    parser.add_argument(
        "--mock-seed",
        type=int,
        default=42,
        help="Semilla del mock (default: 42)",
    )
    args = parser.parse_args()

    if args.comando in ("fase1", "all"):
        from src.fase1_ingesta.pipeline import run_fase1
        run_fase1(
            upload=not args.no_upload,
            mock=args.mock,
            mock_profile=args.mock_profile,
            mock_seed=args.mock_seed,
        )

    if args.comando in ("fase2", "all"):
        print("Fase 2 pendiente", file=sys.stderr)

    if args.comando in ("fase3", "all"):
        print("Fase 3 pendiente", file=sys.stderr)


if __name__ == "__main__":
    main()