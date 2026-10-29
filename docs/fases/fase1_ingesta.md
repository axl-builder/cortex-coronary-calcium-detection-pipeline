# Fase 1 — Ingesta, limpieza y filtrado

## Qué hace

Lee la planilla de Google Sheets (pestañas diarias de guardia), filtra
TC de tórax sin contraste, normaliza y genera `data/processed/result.csv`.
Opcionalmente lo sube a Drive como Google Sheet nativo.

Pipeline: **Extract** (Sheets) → **Transform** (cleaning) → **Load** (CSV + Drive).

## Cómo se corre

### Producción (contra Google Sheets real)

Requiere `keys/` con credenciales de service account y `.env` con
`SPREADSHEET_ID` y `OUTPUT_FOLDER_ID`.

```bash
python -m src.main fase1                 # con upload a Drive
python -m src.main fase1 --no-upload     # sin upload
```

### Desarrollo (con datos sintéticos, sin credenciales)

```bash
python -m src.main fase1 --mock --mock-seed 42 --no-upload
```

Genera una planilla sintética en memoria y la procesa. No toca Google.
No requiere `.env` ni `keys/`. Ideal para CI y para trabajar sin PII.

### Perfiles de mock

```bash
python -m src.main fase1 --mock --mock-profile minimo   --no-upload
python -m src.main fase1 --mock --mock-profile realista --no-upload
python -m src.main fase1 --mock --mock-profile caotico  --no-upload
```

| Perfil     | Uso                                                                                                                                  |
|------------|--------------------------------------------------------------------------------------------------------------------------------------|
| `minimo`   | Happy path: TC + tórax + sin contraste. Smoke test.                                                                                  |
| `realista` | Distribución real: 75% TC, 45% tórax, 75% sin contraste, 10% filas cortas, 5% vacías. Desarrollo.                                    |
| `caotico`  | Todos los defectos: filas vacías, cortas, NaN, Si/No, contrastes compuestos, fechas ambiguas. Fuzzing.                               |

## Generador de datos sintéticos

Ubicado en `src/synthetic/`. CLI:

```bash
# Genera los 3 formatos (xlsx + json + csv por pestaña)
python -m src.synthetic --profile realista --seed 42

# Solo xlsx (para subir a Drive manualmente)
python -m src.synthetic --profile realista --seed 42 --format xlsx

# Solo json (fixture determinista para tests)
python -m src.synthetic --profile realista --seed 42 --format json
```

### Estructura de una pestaña de guardia (mock)

Replica la pestaña modelo de la planilla real:

```text
fila 0:     ["HACER CONTEO...", "PLANILLA GUARDIA", "", ...]  ← título
fila 1:     ["CHECKLIST", "", ...]                            ← fila checklist
fila 2:     ["", "PACIENTE", "SECTOR", "HAB", "ESTUDIO", ...] ← header
fila 3..N:  ["comentario", "Nombre Paciente", "SHOCK", "119", "TC", ...]
fila N+1..: [residuales con FALSE x4 + 0:00:00 + -]
...:        bloque de resumen (TC/RMN GUARDIA/INTERNADOS/AMBULATORIOS)
...:        checklist operativo (CARRO DE PARO, BRIEF, ...)
```

### Pestañas con fecha manual

Algunas pestañas no siguen el patrón DDMM (ej. "Hoja 161") y tienen
fecha fija en `settings.dates.fechas_manuales`. El generador las soporta
con el parámetro `pestanias_con_fecha_manual`:

```python
from src.synthetic import generar_para_fase1

# Sin fecha manual (mock genérico)
result, nombres = generar_para_fase1(profile="realista", seed=42)

# Con fecha manual (replica tu planilla real)
result, nombres = generar_para_fase1(
    profile="realista", seed=42,
    pestanias_con_fecha_manual=["Hoja 161"],
)
```

El generador no hardcodea nombres de pestaña. Si tu planilla real
tiene "Hoja 200" o "Inicio 2024", se los pasás y el mock los usa.

## Estructura del código

```text
src/fase1_ingesta/
├── config.py                     # load_settings()
├── pipeline.py                   # run_fase1() orquestador
├── cleaning/
│   ├── dates.py                  # parsear_secuencia, auditar_secuencia
│   ├── filters.py                # es_tc, menciona_torax, evaluar_contraste
│   ├── guards.py                 # pestaña_tiene_datos, clasificar_fila
│   ├── normalize.py              # normalizar_texto, parsear_bool_mayus, etc.
│   └── transform.py              # transform_sheets orquestador
└── ingestion/
    ├── sheets_client.py          # fetch_selected_sheets (service account)
    └── sheet_uploader.py         # upload_csv_as_sheet (OAuth)
```

## Decisión de diseño: contraste crudo vs etiqueta

El CSV preserva el valor crudo de la columna `CONTRASTE`
("NO", "SEDACION", "NO, EVENTUAL", "SI, NO", etc.).
`evaluar_contraste` clasifica internamente para filtrar
(`sin_contraste` / `con_contraste` / `desconocido`), pero no se escribe
la etiqueta al CSV.

Por qué: preservar el crudo permite re-clasificar sin re-correr el ETL
y mantiene la información que el análisis clínico puede necesitar (ej.
distinguir "SEDACION" de "NO"). La etiqueta es una derivación para el
filtro, no un reemplazo del dato.

## Pregunta abierta: parser de contrastes compuestos

**Estado:** pendiente de decisión clínica.

La columna de contraste tiene valores compuestos ("NO, EVENTUAL",
"NO, SEDACION", "SI, NO", "DOBLE, ORAL"). `evaluar_contraste` hace
match exacto contra el vocabulario (sin / con), así que los valores
compuestos caen en `desconocido`. Eso significa:

- Se incluyen en el CSV (porque `desconocido` está en `incluir`).
- Se preserva el valor crudo.
- No se clasifican en `sin_contraste` ni `con_contraste`.

**Consecuencia:** cuando se quiera analizar por subgrupo (solo con
contraste, solo sin), estos casos no aparecen en ningún grupo.

**Preguntas para el investigador clínico:**

| Valor            | ¿Con o sin?                                          |
|------------------|------------------------------------------------------|
| `"NO, EVENTUAL"` | ¿con? (eventual gana) o ¿sin? (no gana)              |
| `"NO, SEDACION"` | sin (ambos son sin), probable                        |
| `"SI, NO"`       | ¿con? ¿sin? ¿desconocido? (contradicción)            |
| `"DOBLE, ORAL"`  | con (ambos son con), probable                        |

**Implementación pendiente:** parser en `filters.py` que tokenice por
`, ; / Y` y aplique la regla de precedencia. ~30 líneas.

**Bloquea:** análisis de subgrupos por contraste en Fase 3.

## Tests

```bash
pytest tests/fase1 -v
```

Cobertura:

- `test_dates.py`: parsing de fechas, secuencias, auditoría.
- `test_filters.py`: `es_tc`, `menciona_torax`, `evaluar_contraste`.
- `test_guards.py`: `clasificar_fila` (corta, vacía, ok).
- `test_synthetic_structure.py`: estructura del mock fiel al modelo.
- `test_transform_mock.py`: cleaning contra fixtures sintéticos.

Fixtures deterministas en `tests/fixtures/synthetic/`:

- `FIXTURE_MINIMO`, `FIXTURE_REALISTA`, `FIXTURE_CAOTICO`
- `FIXTURE_REALISTA_CON_FECHA_MANUAL` (con "Hoja 161")

## Smoke test end-to-end

Ver `docs/fases/fase1_smoke_test.md` para el procedimiento completo:
generar mock → subir a Drive → correr fase1 → verificar CSV y upload.