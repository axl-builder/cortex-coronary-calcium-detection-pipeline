import re

from .normalize import normalizar_texto


def es_tc(valor) -> bool:
    return normalizar_texto(valor) == "tc"


def menciona_torax(texto) -> bool:
    t = normalizar_texto(texto)
    if not t:
        return False
    tokens = re.findall(r"[a-z0-9]+", t)
    return any(tok in ("torax", "tx") for tok in tokens)


def evaluar_contraste(valor, sin: set, con: set) -> str:
    v = str(valor).strip().upper()
    if v in sin:
        return "sin_contraste"
    if v in con:
        return "con_contraste"
    return "desconocido"