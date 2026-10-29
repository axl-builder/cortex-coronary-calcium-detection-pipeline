from src.fase1_ingesta.cleaning.filters import (
    es_tc, menciona_torax, evaluar_contraste,
)


def test_es_tc():
    assert es_tc("TC")
    assert es_tc(" tc ")
    assert not es_tc("RMN")


def test_menciona_torax():
    assert menciona_torax("tórax")
    assert menciona_torax("TX abd y pelvis")
    assert menciona_torax("tórax s/c")
    assert not menciona_torax("contexto")
    assert not menciona_torax("cerebro")


def test_contraste():
    sin = {"NO", "SEDACION"}
    con = {"SI", "DOBLE", "EVENTUAL", "ORAL"}
    assert evaluar_contraste("NO", sin, con) == "sin_contraste"
    assert evaluar_contraste("SEDACION", sin, con) == "sin_contraste"
    assert evaluar_contraste("SI", sin, con) == "con_contraste"
    assert evaluar_contraste("", sin, con) == "desconocido"


def test_evaluar_contraste_devuelve_nombres_esperados():
    """
    Contract: the strings returned by evaluar_contraste must match the
    config vocabulary (`contraste.incluir`).
    """
    sin = {"NO", "SEDACION"}
    con = {"SI", "DOBLE", "EVENTUAL", "ORAL"}
    validos = {"sin_contraste", "con_contraste", "desconocido"}

    assert evaluar_contraste("NO", sin, con) == "sin_contraste"
    assert evaluar_contraste("SI", sin, con) == "con_contraste"
    assert evaluar_contraste("", sin, con) == "desconocido"

    for v in ("NO", "SEDACION"):
        assert evaluar_contraste(v, sin, con) in validos
    for v in ("SI", "DOBLE", "EVENTUAL", "ORAL"):
        assert evaluar_contraste(v, sin, con) in validos