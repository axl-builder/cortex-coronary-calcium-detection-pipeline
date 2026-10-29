"""
Deterministic synthetic data fixtures.

Each fixture is a tuple (result, nombres) where `result` is the dict
{'valueRanges': [...]} consumed by `transform_sheets` and `nombres` are
the tabs that `fetch_selected_sheets` would select.

They are generated at import time with fixed seeds → reproducible. If the
generator changes and breaks a test, the contract changed.
"""

from src.synthetic import generar_para_fase1

# Minimum profile: no manual date, no defects
FIXTURE_MINIMO = generar_para_fase1(profile="minimo", seed=1)

# Realistic profile: no manual date (generic case)
FIXTURE_REALISTA = generar_para_fase1(profile="realista", seed=42)

# Realistic profile WITH manual date (replicates the real sheet with "Hoja 161")
FIXTURE_REALISTA_CON_FECHA_MANUAL = generar_para_fase1(
    profile="realista", seed=42,
    pestanias_con_fecha_manual=["Hoja 161"],
)

# Chaotic profile: no manual date
FIXTURE_CAOTICO = generar_para_fase1(profile="caotico", seed=7)


def fixture_pestania(nombre: str, profile: str = "realista", seed: int = 42) -> dict:
    """Return the valueRange of a specific tab from the fixture."""
    result, _ = generar_para_fase1(profile=profile, seed=seed)
    for vr in result["valueRanges"]:
        if vr["range"].startswith(f"'{nombre}'"):
            return vr
    raise KeyError(f"Tab {nombre!r} not found in the fixture")