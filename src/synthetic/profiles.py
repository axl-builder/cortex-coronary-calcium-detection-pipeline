"""
Perfiles de "suciedad" para el generador de datos sintéticos.

Cada perfil define la distribución de valores y defectos que el generador
usa para producir pestañas que imitan la planilla real de guardia.
"""

PROFILES = {
    "minimo": {
        # Volumen
        "pestanias_guardia": 5,
        "pestanias_no_guardia": 0,
        "filas_por_pestania": (5, 10),
        # Proporciones de tipo de estudio y región
        "prob_estudio_tc": 1.0,
        "prob_region_torax": 1.0,
        "prob_contraste_sin": 1.0,
        # Defectos (todos apagados)
        "prob_fila_vacia": 0.0,
        "prob_fila_corta": 0.0,
        "prob_nan_literal": 0.0,
        "prob_contraste_compuesto": 0.0,
        "prob_bool_raro": 0.0,
        "prob_nombre_pestania_ambiguo": 0.0,
        "prob_fila_residual": 0.0,
        "prob_comentario_checklist": 0.0,
        "n_columnas_conteo": 0,
    },
    "realista": {
        "pestanias_guardia": 30,
        "pestanias_no_guardia": 4,
        "filas_por_pestania": (5, 35),
        "prob_estudio_tc": 0.75,
        "prob_region_torax": 0.45,
        "prob_contraste_sin": 0.75,
        "prob_fila_vacia": 0.05,
        "prob_fila_corta": 0.10,
        "prob_nan_literal": 0.15,
        "prob_contraste_compuesto": 0.08,
        "prob_bool_raro": 0.05,
        "prob_nombre_pestania_ambiguo": 0.20,
        "prob_fila_residual": 0.80,   # casi toda pestaña tiene residuales al final
        "prob_comentario_checklist": 0.30,
        "n_columnas_conteo": 6,
        "prob_residuales_preservadas": 0.0,
    },
    "caotico": {
        "pestanias_guardia": 40,
        "pestanias_no_guardia": 8,
        "filas_por_pestania": (1, 50),
        "prob_estudio_tc": 0.50,
        "prob_region_torax": 0.30,
        "prob_contraste_sin": 0.50,
        "prob_fila_vacia": 0.20,
        "prob_fila_corta": 0.30,
        "prob_nan_literal": 0.40,
        "prob_contraste_compuesto": 0.30,
        "prob_bool_raro": 0.25,
        "prob_nombre_pestania_ambiguo": 0.60,
        "prob_fila_residual": 1.0,
        "prob_comentario_checklist": 0.80,
        "n_columnas_conteo": 8,
        "prob_residuales_preservadas": 0.5,
    },
    
}