import re
import unicodedata


def normalizar_texto(s) -> str:
    s = str(s).strip().lower()
    s = "".join(
        c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn"
    )
    return " ".join(s.split())


def parsear_bool_mayus(valor):
    v = str(valor).strip().upper()
    if v == "TRUE":
        return True
    if v == "FALSE":
        return False
    return None


def formatear_bool(valor) -> str:
    if valor is True:
        return "TRUE"
    if valor is False:
        return "FALSE"
    return ""


def limpiar_celda(celda) -> str:
    if celda is None:
        return ""
    return " ".join(str(celda).strip().split())