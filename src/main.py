import argparse
import sys


def main():
    parser = argparse.ArgumentParser(prog="cortex")
    parser.add_argument("comando", choices=["fase1", "fase2", "fase3", "all"])
    parser.add_argument(
        "--no-upload",
        action="store_true",
        help="Phase 1: do not upload the CSV to Drive",
    )
    parser.add_argument(
        "--mock",
        action="store_true",
        help="Use synthetic data instead of Google Sheets",
    )
    parser.add_argument(
        "--mock-profile",
        default="realista",
        choices=["minimo", "realista", "caotico"],
        help="Mock profile (default: realista)",
    )
    parser.add_argument(
        "--mock-seed",
        type=int,
        default=42,
        help="Mock seed (default: 42)",
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
        print("Phase 2 pending", file=sys.stderr)

    if args.comando in ("fase3", "all"):
        print("Phase 3 pending", file=sys.stderr)


if __name__ == "__main__":
    main()