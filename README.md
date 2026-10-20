# Opportunistic Coronary Calcium Detection Pipeline

A data engineering pipeline to identify patients with undiagnosed coronary artery disease from routine chest CT scans, and to flag those who are not receiving preventive treatment.

Developed in collaboration with a practicing cardiologist.

**Status:** Design and scoping. The architecture, business rules and validation approach are defined; implementation is in progress.

---

## Overview

Many patients undergo non-contrast chest CT for reasons unrelated to the heart (emergency visits, pneumonia, persistent cough). These scans contain information about coronary calcification that is rarely used. The coronary artery calcium score, measured on a non-contrast chest CT, is a validated indicator for estimating 10-year cardiovascular risk.

This project builds the data infrastructure needed to:

1. Find every eligible chest CT in the institution's historical records.
2. Link each study to the patient's clinical history.
3. Determine whether the patient is on preventive therapy (statins or aspirin).
4. Produce a consolidated dataset for retrospective analysis, clinical referral and scientific publication.

The main obstacle is not clinical but technical: the required information is spread across disconnected systems and captured without standardization.

## The Problem

| Issue | Description |
|---|---|
| Disconnected data silos | Imaging requests are logged in an Excel sheet. The DICOM images live in a separate PACS/RIS that is not linked or indexed against that sheet. |
| Free-text study names | The sheet mixes every study type with no fixed categories. Entries vary in case, spelling and abbreviations, and include compound studies (for example `TORAX`, `Tórax Abdomen Pelvis`, `Angio TC con contraste`, `TC cerebro`). |
| Unstructured clinical notes | Comorbidities and medications are recorded in informal emergency-room notes and ward handovers, stored as Word or plain text files. |
| Manual process | Clinical staff do not have the time to filter thousands of historical records by hand. |

## Architecture

```
Imaging request log (Excel)
          |
          v
[Phase 1] Ingestion, cleaning and filtering
          --> list of patients with an eligible chest CT
          |
          v
[Intermediate step] PACS linkage
          --> access to each study for calcium score measurement
          |
          v
[Phase 2] Clinical data extraction (rules + LLM-assisted NLP)
          --> comorbidities and treatment status per patient
          |
          v
Integration and clinical prioritization
          --> final dataset, groups A / B / C
          |
          v
Medical audit (sample review)
          |
          v
[Phase 3] Visualization and publication outputs
```

### Phase 1: Request log ingestion and cleaning

1. **Extract.** Read the Excel log from local storage, a shared network folder or Google Sheets.
2. **Transform.**
   - Text normalization: lowercase, accent removal, special character and whitespace cleanup.
   - Rule-based study classification with regular expressions.
3. **Load.** Produce a clean table of patients with an eligible chest CT.

**Eligibility rules**

| Include | Exclude |
|---|---|
| Chest CT (TC / TAC de tórax) | Other anatomical regions (brain, spine, pelvis, limbs) |
| Combined studies that include the chest (for example chest + abdomen + pelvis) | Contrast or vascular studies that distort calcium measurement (for example CT angiography of the chest) |
| | Other imaging modalities (MRI, ultrasound) |

Illustrative sketch of the classification logic:

```python
import re
import unicodedata

INCLUDE = re.compile(r"\b(torax|tx)\b")
EXCLUDE = re.compile(r"\b(angio|contraste|cerebro|columna|resonancia|rm|eco\w*)\b")

def normalize(text: str) -> str:
    text = unicodedata.normalize("NFKD", text.lower())
    text = "".join(c for c in text if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9 ]", " ", text)).strip()

def is_eligible(study_name: str) -> bool:
    name = normalize(study_name)
    return bool(INCLUDE.search(name)) and not EXCLUDE.search(name)
```

The final term lists will be refined with the clinical team after reviewing the real vocabulary used in the log.

### Intermediate step: PACS linkage

The cleaned list is matched against the patient identifier in the imaging system so that radiologists can open each study directly and measure the calcium score. The linkage key must be a stable identifier (national ID, medical record number or study accession number), never the patient name.

### Phase 2: Clinical data extraction

**Inputs.** The filtered list from Phase 1, and Word or text files with emergency-room notes and ward handovers.

**Target variables**

- Comorbidities: diabetes, dyslipidemia or elevated cholesterol, hypertension.
- Preventive medication: active statin therapy (atorvastatin, rosuvastatin, simvastatin) or aspirin.

**Processing layers**

| Layer | Purpose |
|---|---|
| Document parsing | Convert Word files to plain text (`python-docx`) and assign each text block to a patient identifier. |
| Rules and dictionaries | Regular expressions and clinical term dictionaries, with negation and context handling (for example "niega diabetes", "sin antecedentes de dislipidemia", "suspende aspirina"). |
| LLM-assisted extraction | A language model, local or behind an API with data privacy guarantees, converts free-text paragraphs into a structured record per patient. |

Target output schema:

```json
{
  "paciente_id": "12345",
  "es_diabetico": false,
  "tiene_dislipidemia": true,
  "toma_estatinas": false,
  "toma_aspirina": false,
  "evidencia_texto": "Paciente de 62 años con antecedentes de dislipemia. No refiere medicación habitual."
}
```

The `evidencia_texto` field keeps the source sentence for each extraction so that every flag can be audited by a clinician.

### Integration and prioritization

The Phase 1 table (imaging and calcium score) is joined with the Phase 2 structured records on the patient identifier.

| Group | Label | Criterion |
|---|---|---|
| A | Highest priority | Elevated calcium score, no statin or aspirin |
| B | Under treatment | Elevated calcium score, active preventive therapy |
| C | No elevated risk | Normal calcium score |

### Validation and quality control

Extraction from unstructured clinical text carries a higher degree of uncertainty. The medical team manually reviews 10% to 15% of processed records. That sample is used to compute precision and recall per variable and to tune the rules and prompts.

### Phase 3: Visualization and publication outputs

From the consolidated dataset the pipeline generates four publication-ready figures:

1. **Cohort flowchart (PRISMA style).** Total records, filtered by chest CT, evaluated in PACS, final analyzed cohort.
2. **Treatment gap.** Among patients with coronary calcium, the proportion with and without preventive therapy.
3. **Calcium score severity distribution.** Agatston score grouped as 0, 1 to 99, 100 to 399 and 400 or more.
4. **Risk factor cross-tabulation.** Coronary calcium against diabetes, hypertension and age group.

## Tech Stack

| Component | Tools |
|---|---|
| Ingestion | `pandas`, `openpyxl`, Google Sheets API |
| Cleaning and rules | Python, `re`, `unicodedata` |
| Document parsing | `python-docx` |
| Structured extraction | Local LLM or API with privacy guarantees, JSON output validated against a schema |
| Storage | SQLite or PostgreSQL |
| Visualization | `matplotlib`, `seaborn` |

## Proposed Repository Structure

```
.
├── README.md
├── pyproject.toml
├── config/
│   └── study_terms.yaml        # inclusion and exclusion vocabulary
├── data/
│   └── synthetic/              # fabricated sample data only
├── docs/
│   └── architecture.md
├── src/
│   ├── ingestion/              # Excel / Sheets readers
│   ├── cleaning/               # normalization and study classification
│   ├── linkage/                # PACS and patient identifier matching
│   ├── nlp/                    # parsing, rules, LLM extraction
│   ├── integration/            # joins and priority groups
│   └── reporting/              # figures and summary tables
└── tests/
```

## Data Privacy

This project processes sensitive personal health data. The repository is designed so that none of it is ever committed.

- No real patient data, identifiers or institutional documents are stored in this repository.
- All examples, tests and sample files use fabricated synthetic data.
- Direct identifiers (name, national ID) are to be replaced by an internal pseudonymous key as early as possible in the pipeline, with the mapping table stored separately under restricted access.
- Processing is intended to run inside the institution's own environment. If an external LLM API is used, it must provide contractual guarantees of no data retention and no training on submitted content; otherwise a local model is used.
- Use of the data is subject to institutional authorization and ethics review.

## Roadmap

- [x] Define clinical objective, scope and eligibility criteria
- [x] Design the three-phase architecture
- [ ] Confirm data access: Excel location, PACS permissions, clinical note storage
- [ ] Confirm the patient linkage key across all three sources
- [ ] Define how the calcium score is obtained (existing value or retrospective measurement)
- [ ] Define the calcium score threshold used for groups A, B and C
- [ ] Phase 1: ingestion, cleaning and study classification
- [ ] Intermediate step: PACS linkage
- [ ] Phase 2: clinical note parsing, rules and LLM-assisted extraction
- [ ] Integration, prioritization and audit sampling
- [ ] Phase 3: figures for presentation and publication

## Author

Axel, data engineer with a background in architecture.

- GitHub: [axl-builder](https://github.com/axl-builder)
- LinkedIn: [axellifschitz](https://linkedin.com/in/axellifschitz)

## License

To be defined.