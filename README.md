# twig_grafter

Reconstruct family trees from Greek Catholic birth and death records
that have been hand-transcribed into CSV files.  The tool constructs
small family-tree fragments ("twigs") from individual records, finds
overlapping twigs via McGregor maximal common subgraph matching, and
merges ("grafts") them into larger connected trees.

## Quick Start

```bash
# 1. Import birth records CSV into a JSON graph
python birth_import.py

# 2. Merge overlapping twigs
python birth_merge.py

# 3. Convert JSON to GML for visualization in Gephi
python twig2gml.py dum.json > output.gml
```

## Workflow

1. **Transcribe** parish register pages into CSV files following the
   schemas in [`docs/data_format.md`](docs/data_format.md).
2. **Import** CSVs into a JSON graph with `birth_import.py` or
   `birth_import.py`.  Each record becomes a "twig" — a small family
   tree fragment of 2–4 generations.
3. **Merge** overlapping twigs with `birth_merge.py`.  The tool uses
   McGregor's algorithm to find maximal common subgraphs between twigs,
   then grafts matching twigs together.
4. **Visualize** the resulting graph in Gephi by converting to GML with
   `twig2gml.py`.

## Module Map

| Module | Purpose |
|---|---|
| `data_model.py` | Core genealogical data model (Person, Name, Fact, Date, ...) |
| `import_records.py` | CSV parsing and record construction |
| `graph_model.py` | NetworkX-based graph wrapper |
| `comparison.py` | Person, name, date, and location comparison functions |
| `mcgregor.py` | McGregor maximal common subgraph algorithm |
| `graph_match.py` | Location-based component matching |
| `birth_import.py` | Pipeline: CSV → JSON |
| `birth_merge.py` | Pipeline: JSON → merged JSON |
| `twig2gml.py` | JSON → GML converter (CLI) |
| `global_align.py` | Experimental Needleman-Wunsch alignment |
| `local_align.py` | Experimental Smith-Waterman alignment |
| `repr_check.py` | JSON round-trip verification utility |
| `test_import.py` | Import unit tests |
| `test_data_model.py` | Data model unit tests |

## Dependencies

- Python 3.x
- `networkx~=2.4`
- `click~=7.1.2`

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
- `global_align.py` and `local_align.py` (experimental sequence alignment)
- Priority subset ordering in McGregor (not yet implemented)

## Contact

Open an issue or reach out on Twitter (@NumerousHats).
