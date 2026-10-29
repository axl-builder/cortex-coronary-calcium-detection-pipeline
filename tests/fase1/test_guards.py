from src.fase1_ingesta.cleaning.guards import clasificar_fila


def test_clasificar_corta():
    assert clasificar_fila([], [1, 4, 5, 6], 14) == "corta"
    assert clasificar_fila(["a"] * 10, [1, 4, 5, 6], 14) == "corta"


def test_clasificar_vacia():
    fila = [""] * 20
    assert clasificar_fila(fila, [1, 4, 5, 6], 14) == "vacia"


def test_clasificar_ok():
    fila = [""] * 20
    fila[1] = "Paciente"
    assert clasificar_fila(fila, [1, 4, 5, 6], 14) == "ok"