import csv
import json
from pathlib import Path


def write_csv(path: Path, header: list, rows: list):
    """Write a CSV file with the given header and rows (UTF-8, no BOM)."""
    with open(path, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(rows)


def write_json(path: Path, data: dict):
    """Write a JSON file with UTF-8 encoding and 2-space indentation."""
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)