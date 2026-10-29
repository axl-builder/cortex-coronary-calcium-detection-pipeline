# Opportunistic Coronary Calcium Detection Pipeline

A data engineering pipeline to identify patients with undiagnosed coronary artery
disease from routine non-contrast chest CT scans, and to flag those who are not
receiving preventive treatment.

Developed in collaboration with a practicing cardiologist, with the goal of
producing a retrospective cohort suitable for clinical referral and scientific
publication.

**Status:** Phase 1 complete and validated end-to-end against real institutional
data. Phases 2 and 3 are stubs pending clinical data access and ethics approval.

---

## Overview

Many patients undergo non-contrast chest CT for reasons unrelated to the heart
(emergency visits, pneumonia, persistent cough). These scans contain information
about coronary calcification that is rarely used. The coronary artery calcium
score, measured on a non-contrast chest CT, is a validated indicator for
estimating 10-year cardiovascular risk.

This project builds the data infrastructure needed to:

1. Find every eligible chest CT in the institution's historical records.
2. Link each study to the patient's clinical history.
3. Determine whether the patient is on lipid-lowering therapy.
4. Produce a consolidated dataset for retrospective analysis, clinical referral
   and scientific publication.

The main obstacle is not clinical but technical: the required information is
spread across disconnected systems and captured without standardization.

## The problem

| Issue | Description |
|---|---|
| Disconnected data silos | Imaging requests are logged in an Excel sheet. The DICOM images live in a separate PACS/RIS that is not linked or indexed against that sheet. |
| Free-text study names | The sheet mixes every study type with no fixed categories. Entries vary in case, spelling and abbreviations, and include compound studies (for example `TORAX`, `Tórax Abdomen Pelvis`, `Angio TC con contraste`, `TC cerebro`). |
| Unstructured clinical notes | Comorbidities and medications are recorded in informal emergency-room notes and ward handovers, stored as Word or plain text files. |
| Manual process | Clinical staff do not have the time to filter thousands of historical records by hand. |

## Architecture

```text
Imaging request log (Excel / Google Sheets)
        |
        v
[Phase 1] Ingestion, cleaning and filtering        <-- COMPLETE
        --> list of patients with an eligible chest CT
        |
        v
[Intermediate step] PACS linkage                   <-- STUB
        --> access to each study for calcium score measurement
        |
        v
[Phase 2] Clinical data extraction (rules + LLM)   <-- STUB
        --> comorbidities and treatment status per patient
        |
        v
Integration and clinical prioritization            <-- STUB
        --> final dataset, groups A / B / C
        |
        v
Medical audit (sample review)                      <-- STUB
        |
        v
[Phase 3] Visualization and publication outputs    <-- STUB
```

### Phase 1: Request log ingestion and cleaning (COMPLETE)

Reads the imaging request log (Google Sheets or a local CSV export), filters
non-contrast chest CT studies for patients over 40, normalizes text, and
produces a clean CSV of eligible studies. Optionally uploads the result to
Google Drive as a native Sheet.

**Pipeline:** Extract (Sheets) → Transform (cleaning + filtering) → Load
(CSV + optional Drive upload).

**Eligibility rules:**

| Include | Exclude |
|---|---|
| Chest CT (`TC` / `TAC` de tórax), recorded as `tx`, `torax`, `torax s/c` or `tx s/c` | CT angiography and pulmonary embolism (TEP) protocol studies |
| Combined studies that include the chest (e.g. chest + abdomen + pelvis) | Contrast studies in any variant (`contraste`, `cte`), which distort calcium measurement |
| Patients older than 40 | Other anatomical regions (brain, spine, pelvis, limbs) |
| | Other imaging modalities (MRI, ultrasound) |

The abbreviation `s/c` means "sin contraste" (non-contrast). These are the
studies of interest, so they are recognized before the contrast exclusion is
applied.

**Key design decisions:**

- **Raw contrast values are preserved** in the output CSV (`NO`, `SEDACION`,
  `SI`, `DOBLE`, `NO, EVENTUAL`, etc.). The classifier (`sin_contraste` /
  `con_contraste` / `desconocido`) is used internally for filtering but is not
  written to the CSV. This allows reclassification without re-running the ETL
  and preserves clinical granularity.
- **Compound contrast values** (`"NO, EVENTUAL"`, `"NO, SEDACION"`,
  `"SI, NO"`) currently fall into `desconocido` because the exact-match
  classifier does not parse them. They are included in the output and preserved
  raw. **Open question:** the precedence rule (e.g. does `"NO, EVENTUAL"` count
  as with or without contrast?) is a clinical decision pending. See
  `docs/fases/fase1_ingesta.md`.
- **Date-stamped and MOCK-tagged output names:**
  `CORTEX - Resultados [MOCK] YYYY-MM-DD HHMM`. Mock runs are explicit and never
  confused with production.
- **Fail-fast validation:** if `contraste.incluir` in `config/settings.yaml`
  contains a value outside the classifier vocabulary, the pipeline exits with a
  clear error before processing anything.

### Intermediate step: PACS linkage (STUB)

The cleaned list is matched against the patient identifier in the imaging
system so that radiologists can open each study directly and measure the calcium
score. The linkage key must be a stable identifier (national ID, medical record
number or study accession number), never the patient name.

### Phase 2: Clinical data extraction (STUB)

**Inputs.** The filtered list from Phase 1, and Word or text files with
emergency-room notes and ward handovers.

**Target variables**

- Cardiovascular risk factors: hypertension, dyslipidemia, smoking status,
  obesity.
- Lipid-lowering therapy: statins, ezetimibe, bempedoic acid and others.
- Laboratory values (urea, creatinine, total cholesterol), from the laboratory
  system rather than the clinical notes.

**Processing layers**

| Layer | Purpose |
|---|---|
| Document parsing | Convert Word files to plain text (`python-docx`) and assign each text block to a patient identifier. |
| Rules and dictionaries | Regular expressions and clinical term dictionaries, with negation and context handling (e.g. "niega hipertensión", "suspende atorvastatina"). |
| LLM-assisted extraction | A local or privacy-guaranteed API model converts free-text paragraphs into a structured record per patient. |

**Target output schema:**

```json
{
  "paciente_id": "12345",
  "hipertension": false,
  "dislipidemia": true,
  "tabaquismo": "EX",
  "obesidad": false,
  "estatinas": false,
  "ezetimibe": false,
  "acido_bempedoico": false,
  "otro_hipolipemiante": false,
  "evidencia_texto": "Paciente de 62 años, ex fumador, con antecedentes de dislipemia. No refiere medicación habitual."
}
```

When a note does not mention a variable, the field is returned as `null` (no
data) rather than `false`, so that an unrecorded history is never read as an
absent one. The `evidencia_texto` field keeps the source sentence for each
extraction so that every flag can be audited by a clinician.

### Integration and prioritization (STUB)

The Phase 1 table (imaging and calcium score) is joined with the Phase 2
structured records on the patient identifier.

| Group | Label | Criterion |
|---|---|---|
| A | Highest priority | Elevated coronary calcium, no lipid-lowering therapy |
| B | Under treatment | Elevated coronary calcium, active lipid-lowering therapy |
| C | No elevated risk | Normal calcium score |

### Validation and quality control (STUB)

Extraction from unstructured clinical text carries a higher degree of
uncertainty. The medical team manually reviews 10% to 15% of processed records
to compute precision and recall per variable and to tune the rules and prompts.

### Phase 3: Visualization and publication outputs (STUB)

Four publication-ready figures:

1. **Cohort flowchart (PRISMA style).** Total records, filtered by chest CT,
   evaluated in PACS, final analyzed cohort.
2. **Treatment gap.** Among patients with coronary calcium, the proportion with
   and without preventive therapy.
3. **Calcium score severity distribution.** Agatston score grouped as
   0, 1–99, 100–399 and 400+.
4. **Risk factor cross-tabulation.** Coronary calcium against hypertension,
   dyslipidemia, smoking status, obesity and age group.

---

## Quick start

### Requirements

- Python 3.11+ (3.13/3.14 tested)
- [uv](https://docs.astral.sh/uv/) (recommended) or pip

### Install

```bash
git clone git@github.com:axl-builder/cortex-coronary-calcium-detection-pipeline.git
cd cortex-coronary-calcium-detection-pipeline
uv sync
# or: pip install -e .
```

### Run Phase 1 with synthetic data (no credentials needed)

The fastest way to see the pipeline working end-to-end, without Google Sheets
access and without any real patient data:

```bash
# 1. Generate a synthetic imaging log (xlsx + json + csv)
python -m src.synthetic --profile minimo --seed 42

# 2. Run the pipeline against the synthetic data
python -m src.main fase1 --mock --mock-profile minimo --mock-seed 42 --no-upload

# 3. Inspect the output
head -5 data/processed/result.csv
cat logs/resumen_*.json | tail -20
```

Profiles:

| Profile | Description | Use case |
|---|---|---|
| `minimo` | Happy path: all TC + chest + no contrast, no defects. | Smoke test, CI |
| `realista` | Real distribution: 75% TC, 45% chest, 75% no contrast, 10% short rows, 5% empty rows. | Development |
| `caotico` | All defects: empty rows, short rows, NaN, Si/No, compound contrasts, ambiguous dates. | Robustness testing |

### Run Phase 1 against real Google Sheets (requires credentials)

1. Copy `.env.example` to `.env` and fill in `SPREADSHEET_ID` and
   `OUTPUT_FOLDER_ID`.
2. Place the service account JSON in `keys/` (for reading) and the OAuth client
   secret in `keys/oauth_client_secret.json` (for uploading).
3. Share the source Sheet with the service account email (Reader permission).
4. Share the output folder with your Google account (Editor permission).

```bash
python -m src.main fase1                 # with Drive upload
python -m src.main fase1 --no-upload     # without upload
```

Output: `data/processed/result.csv`, uploaded to Drive as
`CORTEX - Resultados YYYY-MM-DD HHMM`.

### Run the test suite

```bash
pytest tests/fase1 -v
```

48 tests. No network, no credentials, deterministic fixtures. Should pass in
under 1 second.

---

## Repository structure

```text
.
├── README.md
├── pyproject.toml
├── uv.lock
├── .env.example
├── .gitignore
├── config/
│   └── settings.yaml              # sheets, dates, columns, contrast, header
├── data/                          # gitignored, regenerated per run
│   ├── raw/
│   ├── interim/
│   ├── processed/                 # result.csv
│   └── synthetic/                 # mock xlsx / json / csv
├── docs/
│   └── fases/
│       ├── fase1_ingesta.md       # Phase 1: what it does, how to run, open questions
│       └── fase1_smoke_test.md    # End-to-end procedure with Drive
├── src/
│   ├── common/                    # paths, logging, io
│   ├── fase1_ingesta/             # Phase 1 (COMPLETE)
│   │   ├── cleaning/              # dates, filters, guards, normalize, transform
│   │   ├── ingestion/             # sheets_client, sheet_uploader
│   │   ├── config.py
│   │   └── pipeline.py
│   ├── fase2_nlp/                 # Phase 2 (STUB)
│   ├── fase3_reporting/           # Phase 3 (STUB)
│   ├── paso_intermedio_linkage/   # PACS linkage (STUB)
│   ├── synthetic/                 # Mock data generator
│   └── main.py                    # CLI
└── tests/
    ├── conftest.py
    ├── fase1/                     # 48 tests
    └── fixtures/synthetic/        # Deterministic fixtures
```

## Design principles

### Preserve raw values, classify for filtering

The output CSV keeps the original contrast value (`"NO"`, `"SEDACION"`,
`"NO, EVENTUAL"`, etc.). Classification (`sin_contraste` / `con_contraste` /
`desconocido`) is internal to the filter. This allows reclassification without
re-running the ETL and keeps the data reproducible.

### Mock is faithful to the real template

The synthetic generator replicates the actual structure of a Phase 1 sheet:
title row, checklist row, header row, patient rows, residual rows, summary
block, operational checklist. The mock is not a clean table; it includes the
defects of the real source. 14 structure tests
(`tests/fase1/test_synthetic_structure.py`) lock the mock to the real model. If
the source template changes, tests fail and force an update.

### Mock is parameterizable, not hardcoded

The generator does not know sheet names. `pestanias_con_fecha_manual` takes a
list of names with a manual date (e.g. `["Hoja 161"]`). If your real sheet has
"Hoja 200" or "Inicio 2024", pass it. The mock adapts.

### Fail fast on misconfiguration

If `contraste.incluir` has a value outside
`{sin_contraste, con_contraste, desconocido}`, the pipeline exits with a clear
error before processing. Silent failures cost hours; fail-fast costs seconds.

### Date-stamped and MOCK-tagged outputs

Output names: `CORTEX - Resultados [MOCK] YYYY-MM-DD HHMM`. Production and mock
outputs are never confused. Every run has an identifiable timestamp.

### Deterministic fixtures for CI

Fixtures are generated with fixed seeds. Same seed, same output. No network,
no credentials, no PII. Tests run in under 1 second.

---

## Ethics, privacy and regulatory status

This project processes sensitive personal health data. The repository is
designed so that none of it is ever committed.

- No real patient data, identifiers or institutional documents are stored in
  this repository.
- All examples, tests and sample files use fabricated synthetic data.
- Direct identifiers (name, national ID) are replaced by an internal
  pseudonymous key as early as possible in the pipeline, with the mapping table
  stored separately under restricted access.
- Processing is intended to run inside the institution's own environment. If an
  external LLM API is used in Phase 2, it must provide contractual guarantees of
  no data retention and no training on submitted content; otherwise a local
  model is used.
- Use of the data is subject to institutional authorization and ethics review.

The `.gitignore` blocks common data-carrying extensions (`*.csv`, `*.xlsx`,
`*.dcm`, etc.) outside of `tests/fixtures/` and `data/synthetic/` (which are
gitignored anyway). Verify with `git check-ignore -v <path>` before committing
anything that could contain PII.

**Clinical use disclaimer.** This code is a research data-processing pipeline.
It is not a medical device and has not been cleared or approved by any
regulatory authority. It is not intended to diagnose, treat, cure or prevent any
disease, nor to replace clinical judgment. Any use with real patient data
requires independent validation, institutional ethics approval and, where
applicable, regulatory review.

## Validation status

| Component | Status | Evidence |
|---|---|---|
| Phase 1 cleaning rules | Validated against real institutional data | 181 tabs → 1,708 rows; 48 deterministic tests |
| Phase 1 synthetic generator | Validated against the real sheet template | 14 structure tests lock the mock to the real model |
| Phase 1 end-to-end | Validated against Google Sheets and Drive | Smoke test (`docs/fases/fase1_smoke_test.md`) |
| Phase 2 (NLP extraction) | Not implemented | — |
| Clinical validation of the cohort | Pending ethics approval | — |

## Reproducibility

The Phase 1 pipeline is deterministic given a source sheet and a
`config/settings.yaml`. Re-running it on the same source produces the same
output. The synthetic generator is deterministic given a seed.

To reproduce a specific run:

```bash
# Re-run Phase 1 on the same source
python -m src.main fase1 --no-upload

# Regenerate the synthetic data used in a test
python -m src.synthetic --profile realista --seed 42 --format json
```

Run metadata (stats, problems, mock profile, seed) is stored in
`logs/resumen_<run_id>.json` for every run.

## Contributing

The workflow follows standard professional practice:

1. Branch from `main`: `feature/<scope>`, `fix/<scope>`, `docs/<scope>`,
   `test/<scope>`.
2. Atomic commits using Conventional Commits:
   `feat:`, `fix:`, `docs:`, `test:`, `refactor:`, `chore:`.
3. PR to `main` (protected: no direct push). Squash and merge.
4. Tag on `main` after merge: `vX.Y.Z-<milestone>`.

Before any commit:

```bash
pytest tests/fase1 -v
git check-ignore -v <file>   # for any file that could contain PII
```

## Open questions (documented, not implemented)

- **Compound contrast parser.** Values like `"NO, EVENTUAL"`, `"NO, SEDACION"`,
  `"SI, NO"` are preserved raw but classified as `desconocido`. The precedence
  rule is a clinical decision pending. Blocks subgroup analysis by contrast. See
  `docs/fases/fase1_ingesta.md`.

## Tech stack

| Component | Tools |
|---|---|
| Ingestion | `google-api-python-client`, `google-auth`, `gspread` (optional), `pandas`, `openpyxl` |
| Cleaning and rules | Python, `re`, `unicodedata` |
| Synthetic data | Python `random` with fixed seeds, `openpyxl` (xlsx export) |
| Document parsing (Phase 2) | `python-docx` |
| Structured extraction (Phase 2) | Local LLM or privacy-guaranteed API, JSON schema validation |
| Storage | SQLite or PostgreSQL |
| Visualization (Phase 3) | `matplotlib`, `seaborn` |
| Testing | `pytest` |
| Packaging | `uv`, `pyproject.toml` |

## Authors

- **Axel Lifschitz**: data engineering, pipeline design and implementation.
  GitHub: [axl-builder](https://github.com/axl-builder) ·
  LinkedIn: [axellifschitz](https://www.linkedin.com/in/axellifschitz)
- **Clinical collaborator**: clinical scope, eligibility criteria and medical
  validation. (Name and affiliation to be added upon publication.)

## License

The code is released under the MIT License (see `LICENSE`). Clinical data and
institutional documents are not covered by this license and remain subject to
institutional authorization and ethics review.

The code is not intended for clinical use without independent validation and,
where applicable, regulatory review.