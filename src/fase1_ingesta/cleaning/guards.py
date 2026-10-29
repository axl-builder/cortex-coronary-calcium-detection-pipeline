def pestaña_tiene_datos(attributes, filas_a_saltear) -> bool:
    filas = attributes.get("values", [])
    if len(filas) <= filas_a_saltear:
        return False
    for fila in filas[filas_a_saltear:]:
        if any(str(c).strip() for c in fila if c is not None):
            return True
    return False


def clasificar_fila(fila, columnas, max_col) -> str:
    if not fila:
        return "corta"
    if len(fila) <= max_col:
        return "corta"
    seleccion = [str(fila[i]).strip() if i < len(fila) else "" for i in columnas]
    if not any(seleccion):
        return "vacia"
    return "ok"