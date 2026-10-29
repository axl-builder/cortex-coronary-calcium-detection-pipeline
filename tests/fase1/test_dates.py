from datetime import date
from src.fase1_ingesta.cleaning.dates import (
    candidatos_dia_mes, parsear_secuencia, auditar_secuencia,
)


def test_candidatos_3105():
    assert candidatos_dia_mes("3105") == [(31, 5)]


def test_candidatos_205():
    assert (20, 5) in candidatos_dia_mes("205")


def test_secuencia_cruza_anio():
    nombres = ["3105", "0101", "3112"]
    fechas = parsear_secuencia(nombres, anio_inicial=2026, orden="desc")
    assert fechas[0] == date(2026, 5, 31)
    assert fechas[1] == date(2026, 1, 1)
    assert fechas[2] == date(2025, 12, 31)


def test_auditoria_detecta_hueco():
    fechas = [date(2026, 5, 31), date(2026, 5, 20)]
    problemas = auditar_secuencia(["3105", "2005"], fechas, max_hueco_esperado=1)
    assert len(problemas["huecos"]) == 1


    

# Faltaría: test de fechas_manuales inyectadas, y test de la política orden='asc'