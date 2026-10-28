import yaml
from pathlib import Path
from src.common.paths import CONFIG_DIR


def load_settings(path: Path | None = None) -> dict:
    path = path or (CONFIG_DIR / "settings.yaml")
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)