# Data Formats

This document describes every data format used by twig_grafter: the CSV
transcriptions it imports, the JSON it produces, the GML it exports, and
the thesaurus files it reads.

---

## 1. Birth Record CSV

One row per birth/baptism entry.  The header row lists all column names.
Produced by hand-transcription from scanned parish registers of the Greek
Catholic church in the Sanok region of Galicia.

### Source metadata columns

| Column | Description |
|---|---|
| `repository` | Archive name (e.g. `Archiwum państwowe w Rzeszowie oddział w Sanoku`) |
| `book` | Volume identifier (e.g. `60_437_0_3`) |
| `page` | Page number in the register |
| `image` | Filename of the scanned image |
| `entry` | Entry number on the page (may be `[13]` for interpolated entries) |
| `year` | Year of the event |

### Event date columns

| Column | Description |
|---|---|
| `birth_date` | Date of birth as `MM-DD` or `YYYY-MM-DD`.  May end with `[?]` when the day is uncertain. |
| `baptism_date` | Date of baptism, same format. |
| `death_date` | Date of death (if the infant died before baptism). |

### House/location columns

| Column | Description |
|---|---|
| `house_number` | Primary house number in the village |
| `alt_house_number` | Alternate house number (old numbering system) |
| `house_location` | Village name if the house is in a different village |

### Newborn columns

| Column | Description |
|---|---|
| `given_name` | Given name(s).  Parenthetical alternate: `"Maria (Marianna)"`. |
| `surname` | Surname.  Parenthetical house name: `"Bobak (Kuzior)"`. |
| `gender` | `m` or `f` |
| `illegitimate` | `y` if the child was illegitimate |
| `primogenitus` | Non-empty if the child was the first-born |
| `midwife` | Midwife name (may be comma-delimited) |

### Father's family columns

| Column | Description |
|---|---|
| `father` | Father's given name |
| `f_father` | Father's father's given name |
| `f_mother` | Father's mother's given name |
| `f_m_father_given` | Father's mother's father's given name |
| `f_m_father_surname` | Father's mother's father's surname |
| `f_m_mother_given` | Father's mother's mother's given name |
| `f_m_mother_surname` | Father's mother's mother's surname |
| `father_deceased` | Non-empty if the father was already deceased at time of birth |

### Mother's family columns

| Column | Description |
|---|---|
| `mother` | Mother's given name (maiden name is derived from child's surname) |
| `m_father_given` | Mother's father's given name |
| `m_father_surname` | Mother's father's surname (i.e. the mother's maiden surname) |
| `m_mother` | Mother's mother's given name |
| `m_m_father_given` | Mother's mother's father's given name |
| `m_m_father_surname` | Mother's mother's father's surname |
| `m_m_mother_given` | Mother's mother's mother's given name |
| `m_m_mother_surname` | Mother's mother's mother's surname |
| `m_m_m_father_given` | Mother's mother's mother's father's given name |
| `mothers_spouse` | Mother's spouse (if different from father) |
| `mother_previous_spouse` | Mother's previous spouse |

### Godparent columns

| Column | Description |
|---|---|
| `godfather_given` | Godfather's given name |
| `godfather_surname` | Godfather's surname |
| `godmother_given` | Godmother's given name |
| `godmother_surname` | Godmother's surname |
| `godmothers_spouse` | Godmother's spouse |
| `godmothers_father` | Godmother's father |
| `additional_godfathers` | Additional godfather names |
| `additional_godmothers` | Additional godmother names |

### Other columns

| Column | Description |
|---|---|
| `noncatholic` | Non-empty if the family was non-Catholic |
| `parents_marriage` | Notes about the parents' marriage |
| `notes` | Free-text notes |

### Inline annotation conventions

- **Comments**: Text inside `<angle brackets>` is treated as a transcription note and extracted by `parse_notes()`.
- **Low confidence**: A trailing `?` marks uncertain readings; it is stripped from the value and recorded as `"low"` confidence.
- **Bracketed text**: `[text]` in a name field is treated as the primary reading (brackets are stripped).

---

## 2. Death Record CSV

One row per death/burial entry.

### Source metadata and event date columns

Same structure as birth CSV: `repository`, `book`, `page`, `image`, `entry`, `year`, `death_date`, `burial_date`.

### House/location columns

Same as birth CSV: `house_number`, `alt_house_number`, `house_location`.

### Decedent columns

| Column | Description |
|---|---|
| `surname` | Decedent's surname |
| `given_name` | Decedent's given name(s) |
| `gender` | `m` or `f` |
| `uxoratus` | Non-empty if the decedent was married (husband) |
| `coelebs` | Non-empty if the decedent was unmarried |
| `maiden_name` | Maiden name of a married female decedent |

### Family columns

| Column | Description |
|---|---|
| `father` | Father's given name |
| `father_deceased` | Non-empty if father was deceased |
| `mother` | Mother's given name |
| `mother_deceased` | Non-empty if mother was deceased |
| `mothers_father` | Mother's father (given name or comma-delimited) |
| `mothers_mother` | Mother's mother's given name |
| `mothers_mothers_father` | Mother's mother's father |
| `mothers_spouse` | Mother's spouse (if different from father) |
| `sibling` | Sibling name(s) |

### Spouse columns

| Column | Description |
|---|---|
| `spouse` | Spouse's given name |
| `spouse_surname` | Spouse's surname |
| `widow(er)` | Non-empty if the decedent was a widow/widower |
| `years_married` | Duration of marriage |
| `second_marriage` | Non-empty if there was a second marriage |
| `spouse_2` | Second spouse's given name |
| `spouse_2_surname` | Second spouse's surname |
| `widow(er)_2` | Non-empty if widowed from second spouse |
| `years_married_2` | Duration of second marriage |

### Age columns

| Column | Description |
|---|---|
| `age_y` | Age in years |
| `age_m` | Age in months |
| `age_w` | Age in weeks |
| `age_d` | Age in days |
| `year_day` | Non-empty if the age was given in year-and-day format (ambiguous) |
| `birth_year` | Year of birth (if recorded) |

### Other columns

| Column | Description |
|---|---|
| `noncatholic` | Non-empty if non-Catholic |
| `notes` | Free-text notes |

---

## 3. JSON Graph Format

Produced by `birth_import.py` and `birth_merge.py`.  Top-level keys:

```json
{
  "persons": [ ... ],
  "relations": [ ... ]
}
```

### Person object

```json
{
  "identifier": "UUID string",
  "gender": "m" | "f",
  "names": [ <name>, ... ],
  "facts": [ <fact>, ... ],
  "sources": [ <source>, ... ],
  "confidence": "normal" | "low" | "calculated"
}
```

### Name object

```json
{
  "name_type": "birth" | "married",
  "name_parts": {
    "surname": "Bobak",
    "given": "Maria",
    "house_name": "Kuzior"       // optional
  },
  "standard_surname": "Bobak",   // looked up in thesaurus
  "standard_given": "Maria",     // looked up in thesaurus
  "confidence": "normal" | "low"
}
```

### Fact object

```json
{
  "fact_type": "Birth" | "Baptism" | "Death" | "Burial" |
               "Stillbirth" | "IllegitimateBirth" | "Primogenitus" |
               "Uxoratus" | "Coelebs" | "Marriage",
  "date": [ <date>, ... ],          // 1-2 DateRange objects
  "locations": [ <location>, ... ], // optional
  "sources": [ <source>, ... ],
  "confidence": "normal" | "low" | "calculated"
}
```

### DateRange object

```json
{
  "start": "YYYY-MM-DD",
  "end": "YYYY-MM-DD",       // same as start if exact
  "accuracy": 0              // 0 = exact, >0 = uncertain
}
```

### Location object

```json
{
  "house_number": "54",
  "alt_house_number": "",
  "alt_village": "",
  "confidence": "normal"
}
```

### Source object

```json
{
  "repository": "Archiwum państwowe w Rzeszowie oddział w Sanoku",
  "volume": "60_437_0_3",
  "page_number": "170",
  "entry_number": "7",
  "image_file": "098.jpg"
}
```

### Relation object

```json
{
  "person1_identifier": "UUID",
  "person2_identifier": "UUID",
  "type": "parent-child" | "spouse",
  "sources": [ <source>, ... ],
  "confidence": "normal" | "low" | "calculated"
}
```

---

## 4. GML Graph Format

Produced by `twig2gml.py` for import into Gephi.  Uses the NetworkX GML
writer with custom attributes.  Nodes are persons, edges are relations.

```
graph [
  directed 1
  node [
    id "UUID"
    label "Givenname Surname"
    gender "m"
  ]
  edge [
    source "UUID-parent"
    target "UUID-child"
    relation "parent-child"
  ]
]
```

---

## 5. Thesaurus Files

Two CSV files used to normalize variant spellings of names.

### `standardized_surnames.csv`

```
raw,standardized
Andrejec,Andrec
Andryc,Andrec
```

### `standardized_given.csv`

```
raw,standardized
Agata,Agatha
Agrippina,Agrippina
```

Both files have a header row.  The `raw` column contains the spelling
as it appears in the parish register; the `standardized` column contains
the canonical form used for matching.

Lookups are case-sensitive.  The thesaurus is loaded as a `dict` by
`graph_model.py` and passed through to `Name` objects during import.
