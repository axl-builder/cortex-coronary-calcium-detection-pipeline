import re
import unicodedata


def normalizar_texto(s) -> str:
    """Normalize text: lowercase, strip accents, collapse whitespace."""
    s = str(s).strip().lower()
    s = "".join(
        c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn"
    )
    return " ".join(s.split())


def parsear_bool_mayus(valor):
    """Parse 'TRUE'/'FALSE' (case-insensitive) into bool. Returns None otherwise."""
    v = str(valor).strip().upper()
    if v == "TRUE":
        return True
    if v == "FALSE":
        return False
    return None


def formatear_bool(valor) -> str:
    """Format a bool as 'TRUE'/'FALSE'. Returns '' for non-bool values."""
    if valor is True:
        return "TRUE"
    if valor is False:
        return "FALSE"
    return ""


def limpiar_celda(celda) -> str:
    """Clean a cell value: strip, collapse whitespace, coerce None to ''."""
    if celda is None:
        return ""
    return " ".join(str(celda).strip().split())