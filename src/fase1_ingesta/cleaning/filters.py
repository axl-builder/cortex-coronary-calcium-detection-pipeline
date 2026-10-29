import re

from .normalize import normalizar_texto


def es_tc(valor) -> bool:
    """Return True if the normalized value equals 'tc'."""
    return normalizar_texto(valor) == "tc"


def menciona_torax(texto) -> bool:
    """Return True if the text contains a 'chest' token ('torax' or 'tx').

    Tokens are matched exactly (word boundaries), so 'contexto' and 'cerebro'
    do not match 'tx'.
    """
    t = normalizar_texto(texto)
    if not t:
        return False
    tokens = re.findall(r"[a-z0-9]+", t)
    return any(tok in ("torax", "tx") for tok in tokens)


def evaluar_contraste(valor, sin: set, con: set) -> str:
    """Classify a contrast value into 'sin_contraste', 'con_contraste' or 'desconocido'.

    Uses exact match against the `sin` and `con` vocabularies. Compound values
    (e.g. 'NO, EVENTUAL', 'NO, SEDACION', 'SI, NO') currently fall into
    'desconocido' because the exact-match classifier does not parse them.

    Open question: the precedence rule for compound values is a clinical
    decision pending. The raw value is preserved in the output CSV, so the
    classification can be revisited without re-running the ETL.
    See docs/fases/fase1_ingesta.md.
    """
    v = str(valor).strip().upper()
    if v in sin:
        return "sin_contraste"
    if v in con:
        return "con_contraste"
    return "desconocido"