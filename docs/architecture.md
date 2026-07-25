# Architecture

## Overview

twig_grafter is a pipeline for reconstructing family trees from
hand-transcribed Greek Catholic parish registers.  It reads CSV
transcriptions, builds small family-tree fragments ("twigs"), finds
overlapping twigs via graph matching, and merges ("grafts") them into
larger connected trees.

## Dependency Layers

```
Layer 5  birth_import.py / birth_merge.py   (pipeline scripts)
                |
Layer 4  graph_model.py                     (PeopleGraph wrapper)
                |
Layer 3  import_records.py                  (CSV parsing, record classes)
                |
Layer 2  data_model.py                      (Person, Name, Fact, Date, ...)
                |
Layer 1  mcgregor.py                        (maximal common subgraph)
         comparison.py                      (person/name/date matching)
         graph_match.py                     (component-level matching)
```

Layer 1 has no internal dependencies beyond `networkx` and the standard
library.  Each layer depends only on layers below it.

## Module Map

### Pipeline scripts (Layer 5)

| Module | Purpose |
|---|---|
| `birth_import.py` | Reads a birth CSV, loads the thesaurus, builds a `PeopleGraph`, writes `dum.json`. |
| `birth_merge.py` | Reads `dum.json`, splits the graph into twig components, runs McGregor to find overlaps, merges matching twigs, writes `dum2.json`. |

### Graph model (Layer 4)

| Module | Purpose |
|---|---|
| `graph_model.py` | `PeopleGraph` class: wraps a `nx.DiGraph`, provides `append()` to add records, `json()` to serialize, `direct_relations()` to query neighbors. |

### Record import (Layer 3)

| Module | Purpose |
|---|---|
| `import_records.py` | `BirthRecord` and `DeathRecord` classes, CSV parsing functions (`parse_name`, `parse_date`, `parse_notes`), `import_births()` and `import_deaths()` entry points. |

### Data model (Layer 2)

| Module | Purpose |
|---|---|
| `data_model.py` | Core genealogical classes: `Person`, `Name`, `Fact`, `Relationship`, `Date`, `Duration`, `Location`, `Source`, `Statement`, `Conclusion`.  Also `merge()` and `subtract()` utility functions. |

### Matching (Layer 1)

| Module | Purpose |
|---|---|
| `mcgregor.py` | McGregor's branch-and-bound algorithm for maximal common (sub)graph isomorphism. |
| `comparison.py` | `person_mismatch()`, `compare_person()`, `name_match()`, `birth_death_match()`, `compare_location()`, etc. |
| `graph_match.py` | `components_by_location()` and `match_components_in_location()` for location-based component matching. |

### Utilities

| Module | Purpose |
|---|---|
| `twig2gml.py` | Click CLI to convert `dum.json` → GML for Gephi visualization. |
| `global_align.py` | Experimental Needleman-Wunsch sequence alignment on name strings. |
| `local_align.py` | Experimental Smith-Waterman sequence alignment on name strings. |
| `repr_check.py` | Utility to verify `__repr__` / JSON round-tripping of data model objects. |
| `test_import.py` | Unit tests for CSV import functions. |
| `test_data_model.py` | Unit tests for data model classes. |

## Core Concepts

### Twig
A "twig" is a single family-tree fragment: a set of `Person` objects
connected by `Relationship` edges, typically covering 2–4 generations
around one birth or death record.  Each birth/death record imported from
CSV becomes one twig.

### Graft
Grafting is the process of merging two twigs that share one or more
common individuals.  McGregor's algorithm finds the maximum common
subgraph between two twig graphs; if the match is large enough (default
minimum: 5 nodes), the twigs are merged by combining Person objects and
Rerouting edges.

### Merge
`Person.merge()` creates a new `Person` that combines the names, facts,
and sources of two input Persons.  The originals are marked `merged =
True` and are no longer processed.  Two `"merged-into"` Relationship
edges link the originals to the new Person.

## Pipeline Walkthrough

### 1. Import (`birth_import.py`)

```
birth_import.main()
  ├── Load thesaurus from standardized_surnames.csv + standardized_given.csv
  ├── Create empty PeopleGraph
  ├── import_records.import_births('test.csv', graph, thesaurus)
  │     └── For each CSV row:
  │           ├── Parse source, location, notes, confidence
  │           ├── Create BirthRecord
  │           ├── set_newborn_names()    → Person + Name(s)
  │           ├── set_birth_death()      → Birth/Baptism/Death Facts
  │           ├── set_parents()          → Father, Mother, Relationships
  │           ├── set_father_ancestors() → Grandparents, great-grandparents
  │           └── set_mother_ancestors()
  │           └── graph.append(record)   → adds nodes + edges to DiGraph
  └── Write dum.json
```

### 2. Merge (`birth_merge.py`)

```
birth_merge.main()
  ├── Load dum.json → PeopleGraph
  ├── Split graph into weakly connected components (twigs)
  ├── Sort twigs by size (ascending)
  ├── For each twig in queue:
  │     ├── Look up surname index for candidate targets
  │     ├── For each candidate target:
  │     │     ├── Run mcgregor(new_twig_graph, target_twig_graph, ...)
  │     │     ├── If exactly 1 MCS and size >= minimum_match_size (5):
  │     │     │     ├── Validate edge merges on shared neighbors
  │     │     │     ├── For each matched person pair (p1, p2):
  │     │     │     │     ├── person.merge() → merged_person
  │     │     │     │     ├── Reroute unique edges to merged node
  │     │     │     │     └── Merge shared edges
  │     │     │     └── Add unmatched nodes to target twig
  │     │     └── Else: no merge
  │     └── If no target matched: register as new processed twig
  └── Write dum2.json
```

### 3. Visualization

```
twig2gml.py dum.json > output.gml   # import into Gephi
```
