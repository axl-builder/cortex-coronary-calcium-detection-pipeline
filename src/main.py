import argparse
import sys


def main():
    parser = argparse.ArgumentParser(prog="cortex")
    parser.add_argument("comando", choices=["fase1", "fase2", "fase3", "all"])
    parser.add_argument(
        "--no-upload",
        action="store_true",
        help="Phase 1: do not upload the CSV to Drive",  # TODO: layer 2
    )
    parser.add_argument(
        "--mock",
        action="store_true",
        help="Use synthetic data instead of Google Sheets",  # TODO: layer 2
    )
    parser.add_argument(
        "--mock-profile",
        default="realista",
        choices=["minimo", "realista", "caotico"],
        help="Mock profile (default: realista)",  # TODO: layer 2
    )
    parser.add_argument(
        "--mock-seed",
        type=int,
        default=42,
        help="Mock seed (default: 42)",  # TODO: layer 2
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
        print("Fase 2 pendiente", file=sys.stderr)  # TODO: layer 2

    if args.comando in ("fase3", "all"):
        print("Fase 3 pendiente", file=sys.stderr)  # TODO: layer 2


if __name__ == "__main__":
    main()