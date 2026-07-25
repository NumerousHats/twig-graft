# Algorithms

## McGregor Maximal Common Subgraph

The core matching algorithm.  Given two directed graphs G1 and G2, it
finds the largest node-induced subgraph H1 of G1 and H2 of G2 such that
H1 and H2 are isomorphic.

The current implementation does not use McGregor's "priority subset" method for choosing the order in which to attempt node pairing.

Ref: McGregor, James J. "Backtrack search algorithms and the maximal
common subgraph problem" (1982).  Software -- Practice and Experience,
vol. 12, 23-34.

### How it works

1. **Pre-filtering**: For each node in G1, compute the set of G2 nodes
   that are compatible based on `node_comparison`.  This prunes the
   search space before recursion begins.

2. **Depth-first branch-and-bound**: `graph_matcher()` recursively
   assigns G1 nodes to G2 nodes one at a time.  At each step it
   computes how many edges between already-mapped nodes would be lost
   (i.e. exist in G1 but not in the corresponding G2 induced subgraph).

3. **Bounding**: If `edges_removed` exceeds the best solution found so
   far, the current branch is pruned.  This is the key speedup over
   brute-force enumeration.

4. **Null assignments**: If `null_matches_allowed` is True (i.e. when
   node pre-filtering produces empty candidate sets for some G1 nodes),
   a G1 node can be left unmapped.  This is bounded by
   `maximal_nodes_removed`.

5. **Termination**: When all G1 nodes have been assigned, the current
   mapping is compared against the best found so far.  If it has more
   edges (or fewer removed nodes), the old solutions are discarded.

### Input

- `graph1`: The smaller graph (by node count).
- `graph2`: The larger graph.
- `node_comparison(graph1, graph2, g1_node, g2_node) → bool`: Whether
  two nodes are compatible.
- `edge_comparison(graph1, graph2, g1_n1, g1_n2, g2_n1, g2_n2) → bool`:
  Whether two edges are compatible.

### Output

A `NodeMatching` object containing:
- `maximal_common_subgraphs`: List of `{g1_node: g2_node}` dicts, one
  per maximal common subgraph found.
- `edges_in_maximal_subgraph`: Number of edges in the MCS.

### Complexity

Worst case is O(n! * m) where n = |V(G1)| and m = |E(G1)|, but the
bounding typically cuts this dramatically for genealogical graphs.

---

## Person Comparison

### `person_mismatch(person1, person2) → bool`

Returns True if two Person objects **cannot** be the same person-in-real-life.
Used as the `node_comparison` callback for McGregor.

Checks (in order):
1. Either person is a stillbirth → mismatch (stillbirths are never matched).
2. Gender mismatch → mismatch.
3. Name mismatch via `name_match()` → mismatch.
4. Date mismatch via `birth_death_match()` → mismatch.
5. Otherwise → not a mismatch.

### `compare_person(person1, person2, graph=None) → (name_matches, date_matches, location_match)`

A richer comparison that returns match scores rather than a boolean.
Used for diagnostics and the older `graph_match.py` workflow.

---

## Name Matching

### `name_match(names1, names2) → (matches, comparisons)`

Compares two dicts of names (keyed by name_type: "birth", "married",
"unknown").

Algorithm:
1. Compare birth names first.  If birth-name surnames differ → return
   immediate mismatch (-1, 0).
2. Cross-compare all married/unknown names between the two persons.
3. Cross-compare birth name of one against married names of the other.

Returns `(-1, 0)` for definitive mismatch, or `(matches, comparisons)`
where `matches` is the count of agreeing name pairs.

### `compare_fullname(name1, name2, disqualify_surname_mismatch=False) → True/False/None`

Compares two Name objects on both given-name and surname.  Uses
standardized forms (via thesaurus) when available.  Falls back to
`None` (unknown) when one or both standardized forms are missing.

- `True`: both parts match.
- `False`: at least one part definitively disagrees.
- `None`: inconclusive (missing data).

### `compare_name_part(name1, name2, part) → True/False/None`

Compares a single name part (given or surname) using standardized forms.

---

## Date Matching

### `birth_death_match(person1, person2) → (matches, comparisons)`

Compares birth and death date ranges of two Persons.

Checks:
1. If both have birth dates: their ranges must overlap (via
   `datelist_overlap`).
2. If both have death dates: their ranges must overlap.
3. If one has birth and the other has death: the birth must be before
   the death.

Returns `(-1, 0)` for mismatch, or `(matches, comparisons)`.

### `date_overlap(date1, date2) → bool`

Two Date intervals overlap if:
```
date1.start - accuracy ≤ date2.end + accuracy
AND
date2.start - accuracy ≤ date1.end + accuracy
```

### `datelist_overlap(datelist1, datelist2) → bool`

True if any date in list 1 overlaps with any date in list 2.

---

## Location Matching

### `compare_location(loc1, loc2) → True/False`

Two Locations are consistent if:
1. `alt_village` matches.
2. At least one house number matches across both numbering systems.

### `location_match(locations1, locations2) → int`

Counts the number of matching location pairs across two lists.

---

## Twig Merge (`birth_merge.py`)

### Surname Index

An inverted index mapping each standardized surname to the set of
processed twig IDs that contain at least one person with that surname.
This avoids running McGregor against every previously processed twig.

### Merge Criteria

A merge occurs when:
1. McGregor returns exactly 1 maximal common subgraph.
2. The MCS has at least `minimum_match_size` (default 5) nodes.
3. Edge merges on shared neighbors do not raise ValueError.

### Edge Rerouting

After merging two matched persons p1 and p2 into merged_id:
- Edges from p1 or p2 to unique neighbors are rerouted to merged_id.
- Edges from both p1 and p2 to the same neighbor are merged into a
  single edge.
