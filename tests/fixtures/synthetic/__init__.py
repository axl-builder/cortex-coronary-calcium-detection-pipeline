"""
Fixtures deterministas de datos sintéticos.

Cada fixture es una tupla (result, nombres) donde `result` es el dict
{'valueRanges': [...]} que consume `transform_sheets` y `nombres` son
las pestañas que `fetch_selected_sheets` seleccionaría.

Se generan al importar con seeds fijas → reproducibles. Si el generador
cambia y rompe un test, es porque cambió el contrato.
"""

from src.synthetic import generar_para_fase1

# Perfil mínimo: sin fecha manual, sin defectos
FIXTURE_MINIMO = generar_para_fase1(profile="minimo", seed=1)

# Perfil realista: sin fecha manual (caso genérico)
FIXTURE_REALISTA = generar_para_fase1(profile="realista", seed=42)

# Perfil realista CON fecha manual (replica la planilla real con "Hoja 161")
FIXTURE_REALISTA_CON_FECHA_MANUAL = generar_para_fase1(
    profile="realista", seed=42,
    pestanias_con_fecha_manual=["Hoja 161"],
)

# Perfil caótico: sin fecha manual
FIXTURE_CAOTICO = generar_para_fase1(profile="caotico", seed=7)


def fixture_pestania(nombre: str, profile: str = "realista", seed: int = 42) -> dict:
    result, _ = generar_para_fase1(profile=profile, seed=seed)
    for vr in result["valueRanges"]:
        if vr["range"].startswith(f"'{nombre}'"):
            return vr
    raise KeyError(f"Pestaña {nombre!r} no encontrada en el fixture")