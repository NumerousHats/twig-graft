# twig_grafter

Reconstruct family trees from Greek Catholic birth and death records
that have been hand-transcribed into CSV files.  The tool constructs
small family-tree fragments ("twigs") from individual records, finds
overlapping twigs via McGregor maximal common subgraph matching, and
merges ("grafts") them into larger connected trees.

**Note that this README file and the files in `docs/` were generated
using AI. They have been partially edited, reviewed, and corrected by
a human, but there still may be mistakes.**

## Quick Start

```bash
# 1. Install dependencies
uv sync

# 2. Import birth records CSV into a JSON graph
uv run python birth_import.py

# 3. Merge overlapping twigs (fully automatic)
uv run python birth_merge.py

# 3'. ...or review proposed merges in a browser before applying them
uv run streamlit run merge_review_app.py

# 4. Convert JSON to GML for visualization in Gephi
uv run python twig2gml.py dum.json > output.gml
```

## Workflow

1. **Transcribe** parish register pages into CSV files following the
   schemas in [`docs/data_format.md`](docs/data_format.md).
2. **Import** CSVs into a JSON graph with `birth_import.py`.  Each
   record becomes a "twig" — a small family tree fragment of 2–4
   generations.
3. **Merge** overlapping twigs with `birth_merge.py`.  The tool uses
   McGregor's algorithm to find maximal common subgraphs between twigs,
   then grafts matching twigs together automatically.

   As an alternative, `merge_review_app.py` presents the same candidate
   merges in a Streamlit GUI, scored for biological plausibility (see
   `plausibility.py`), so a human can approve, reject, or flag each one
   before it is applied. See [Merge Review App](#merge-review-app) below.
4. **Visualize** the resulting graph in Gephi by converting to GML with
   `twig2gml.py`.

## Merge Review App

Merging twigs purely on McGregor match size can produce biologically
implausible results (e.g. a parent younger than their child). The
`merge_review_app.py` Streamlit app addresses this with a
human-in-the-loop workflow:

```bash
uv run streamlit run merge_review_app.py
```

1. Point it at a graph JSON file (e.g. `dum.json`) and click **Load &
   score proposals**. This generates every candidate merge (via
   `birth_merge.generate_proposals`) without modifying the graph, scores
   each for biological plausibility (via `plausibility.score_proposal`
   — parent/child age gaps, spouse age gaps, and Coelebs consistency),
   and flags proposals that conflict with one another (a person can
   only be merged once).
2. Review each proposal: side-by-side person cards for every matched
   pair, an interactive graph of both twigs (drawn with `pyvis`), and
   any plausibility warnings.
3. **Approve**, **reject**, or **skip** each proposal. Approving a
   proposal automatically flags any other proposal sharing a node with
   it as conflicted.
4. **Apply approved & export** applies all approved, non-conflicting
   merges to a fresh copy of the graph and writes both the merged graph
   JSON and a JSON audit log recording every decision made (including
   the plausibility score and warnings at the time of the decision).

## Module Map

### Source modules

| Module | Purpose |
|---|---|
| `data_model.py` | Core genealogical data model (Person, Name, Fact, Date, ...) |
| `import_records.py` | CSV parsing and record construction |
| `graph_model.py` | NetworkX-based graph wrapper |
| `comparison.py` | Person, name, date, and location comparison functions |
| `mcgregor.py` | McGregor maximal common subgraph algorithm |
| `graph_match.py` | Location-based component matching |
| `plausibility.py` | Biological plausibility scoring for proposed merges |

### Pipeline scripts

| Module | Purpose |
|---|---|
| `birth_import.py` | Pipeline: CSV → JSON |
| `birth_merge.py` | Pipeline: JSON → merged JSON (fully automatic) |
| `merge_review_app.py` | Streamlit GUI: review and approve/reject proposed merges |
| `twig2gml.py` | JSON → GML converter (CLI) |

### Tests

| Module | Purpose |
|---|---|
| `test_data_model.py` | Data model unit tests |
| `test_import.py` | Import unit tests |
| `test_comparison.py` | Comparison function tests |
| `test_mcgregor.py` | McGregor algorithm tests |
| `test_graph_model.py` | PeopleGraph tests |
| `test_merge.py` | Person/Relationship merge tests, and proposal generation/conflict/apply tests |
| `test_plausibility.py` | Plausibility scoring tests |


## Dependencies

Managed with [uv](https://github.com/astral-sh/uv).  See `pyproject.toml`
for the full specification.

- Python >= 3.10
- `networkx>=3.4,<3.5`
- `click~=7.1.2`
- `streamlit>=1.30`
- `pyvis>=0.3`
- `pytest` (dev)

## Running Tests

```bash
uv run pytest
```

## Documentation

- [`docs/data_format.md`](docs/data_format.md) — CSV schemas, JSON/GML formats, thesaurus files
- [`docs/architecture.md`](docs/architecture.md) — Layer diagram, module descriptions, pipeline walkthrough
- [`docs/algorithms.md`](docs/algorithms.md) — McGregor algorithm, person/name/date comparison

## Status

Work in progress.  The import and merge pipeline is functional.  The
following are incomplete or experimental:

- Death record import (partially implemented)
- Second-marriage handling
- Mother's spouse handling
- Priority subset ordering in McGregor (not yet implemented)

## Contact

Please open an issue.
