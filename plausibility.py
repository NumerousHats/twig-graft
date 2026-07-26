"""Biological plausibility scoring for proposed twig merges.

This module evaluates a McGregor-derived node mapping between two twigs (the "proposal") and flags
merges that would be biologically implausible if applied -- for example, a parent younger than their
child, or spouses with an implausible age gap. These checks are deliberately separate from
`comparison.person_mismatch`, which is a fast negative filter used *during* subgraph matching.
`plausibility.score_proposal` is intended to run *after* McGregor has already produced a candidate
mapping, to help a human reviewer decide whether to approve it.

Note: location is intentionally NOT checked here, since a person's location can legitimately change
over their lifetime (e.g. due to marriage or migration).
"""

import logging
from dataclasses import dataclass, field

# Age gap thresholds (in years)
MIN_PARENT_CHILD_GAP_ERROR = 12
MIN_PARENT_CHILD_GAP_WARNING = 15
MAX_SPOUSE_GAP_WARNING = 50
MAX_SPOUSE_GAP_ERROR = 70

# Score penalties
WARNING_PENALTY = 0.2
ERROR_PENALTY = 0.5

DAYS_PER_YEAR = 365.25


@dataclass
class PlausibilityWarning:
    """A single plausibility issue found while scoring a merge proposal.

    Attributes:
        check (str): The name of the check that produced this warning, e.g. "parent_age_gap",
            "spouse_age_gap", or "coelebs".
        severity (str): Either "warning" or "error".
        message (str): A human-readable description of the issue.
    """
    check: str
    severity: str
    message: str


@dataclass
class PlausibilityResult:
    """The result of scoring a merge proposal for biological plausibility.

    Attributes:
        warnings (list of PlausibilityWarning): All issues found, in the order they were discovered.
        score (float): A score in [0.0, 1.0], where 1.0 means no issues were found and 0.0 means the
            merge is (or is close to) biologically impossible.
    """
    warnings: list = field(default_factory=list)
    score: float = 1.0

    def errors(self):
        return [w for w in self.warnings if w.severity == "error"]

    def has_errors(self):
        return any(w.severity == "error" for w in self.warnings)


def _is_unbounded(date):
    """Return True if a Date's range is unbounded on either side (datetime.date.min/.max), which
    indicates that no real date information is available."""
    import datetime
    return date.start == datetime.date.min or date.end == datetime.date.max


def _person_birth_date(person):
    """Return a single representative Date for a Person's birth, or None if unavailable/ambiguous."""
    dates = person.birth_date()
    if not dates:
        return None
    # If there are multiple candidate dates (ambiguity), use the first (most likely), per the
    # data model's convention that dates are ordered from most to least likely.
    date = dates[0]
    if _is_unbounded(date):
        return None
    return date


def _child_parent_gaps(parent_birth, child_birth):
    """Return all four parent-child birth gaps in years (child - parent), one per endpoint
    combination of the two Date ranges.  A negative gap means the parent was born after the child
    (biologically impossible)."""
    return [
        (child_start_ord - parent_ord) / DAYS_PER_YEAR
        for parent_ord in (parent_birth.start.toordinal(), parent_birth.end.toordinal())
        for child_start_ord in (child_birth.start.toordinal(), child_birth.end.toordinal())
    ]


def _spouse_gaps(birth1, birth2):
    """Return all four absolute spouse birth gaps in years, one per endpoint combination of the two
    Date ranges."""
    return [
        abs(ord1 - ord2) / DAYS_PER_YEAR
        for ord1 in (birth1.start.toordinal(), birth1.end.toordinal())
        for ord2 in (birth2.start.toordinal(), birth2.end.toordinal())
    ]


def _check_parent_child_ages(graph1, graph2, node_mapping):
    """Check that every parent-child relationship implied by the merge has a plausible age gap.

    For each mapped pair (child1, child2), find the parents of child1 in graph1 and the parents of
    child2 in graph2.  All four endpoint combinations of the parent's and child's birth-date ranges
    are checked.  A warning or error is only emitted when the gap is implausible at *every*
    endpoint combination -- if any combination yields a plausible gap the relationship is accepted.
    """
    warnings = []

    for child1, child2 in node_mapping.items():
        child1_birth = _person_birth_date(graph1.nodes[child1]["person"])
        child2_birth = _person_birth_date(graph2.nodes[child2]["person"])

        for graph, child, child_birth in ((graph1, child1, child1_birth), (graph2, child2, child2_birth)):
            if child_birth is None:
                continue
            for parent, _, edge_data in graph.in_edges(child, data=True):
                if edge_data["relation"].relationship_type != "parent-child":
                    continue
                parent_birth = _person_birth_date(graph.nodes[parent]["person"])
                if parent_birth is None:
                    continue

                gaps = _child_parent_gaps(parent_birth, child_birth)
                if all(g < MIN_PARENT_CHILD_GAP_ERROR for g in gaps):
                    warnings.append(PlausibilityWarning(
                        check="parent_age_gap",
                        severity="error",
                        message="Parent {} and child {} have an implausible age gap of only "
                                 "{:.1f}--{:.1f} years (minimum {} required)".format(
                                     parent[:7], child[:7], min(gaps), max(gaps),
                                     MIN_PARENT_CHILD_GAP_ERROR)))
                elif all(g < MIN_PARENT_CHILD_GAP_WARNING for g in gaps):
                    warnings.append(PlausibilityWarning(
                        check="parent_age_gap",
                        severity="warning",
                        message="Parent {} and child {} have a low age gap of {:.1f}--{:.1f} years "
                                 "(recommended minimum {})".format(
                                     parent[:7], child[:7], min(gaps), max(gaps),
                                     MIN_PARENT_CHILD_GAP_WARNING)))

    return warnings


def _check_spouse_ages(graph1, graph2, node_mapping):
    """Check that spouses implied by the merge have a plausible age gap.

    All four endpoint combinations of the two birth-date ranges are checked.  A warning or error is
    only emitted when *every* combination exceeds the threshold -- if any combination falls within
    the plausible range, the relationship is accepted.
    """
    warnings = []
    seen_pairs = set()

    for person1, person2 in node_mapping.items():
        for graph, node in ((graph1, person1), (graph2, person2)):
            birth = _person_birth_date(graph.nodes[node]["person"])
            if birth is None:
                continue
            for u, v, edge_data in list(graph.out_edges(node, data=True)) + \
                    [(v, u, d) for u, v, d in graph.in_edges(node, data=True)]:
                if edge_data["relation"].relationship_type != "spouse":
                    continue
                spouse = v if u == node else u
                pair_key = (id(graph), frozenset((node, spouse)))
                if pair_key in seen_pairs:
                    continue
                seen_pairs.add(pair_key)

                spouse_birth = _person_birth_date(graph.nodes[spouse]["person"])
                if spouse_birth is None:
                    continue

                gaps = _spouse_gaps(birth, spouse_birth)
                if all(g > MAX_SPOUSE_GAP_ERROR for g in gaps):
                    warnings.append(PlausibilityWarning(
                        check="spouse_age_gap",
                        severity="error",
                        message="Spouses {} and {} have an implausible age gap of {:.1f}--{:.1f} "
                                 "years (maximum {} expected)".format(
                                     node[:7], spouse[:7], min(gaps), max(gaps),
                                     MAX_SPOUSE_GAP_ERROR)))
                elif all(g > MAX_SPOUSE_GAP_WARNING for g in gaps):
                    warnings.append(PlausibilityWarning(
                        check="spouse_age_gap",
                        severity="warning",
                        message="Spouses {} and {} have a large age gap of {:.1f}--{:.1f} years "
                                 "(recommended maximum {})".format(
                                     node[:7], spouse[:7], min(gaps), max(gaps),
                                     MAX_SPOUSE_GAP_WARNING)))

    return warnings


def _has_spouse_edge(graph, node):
    for _, _, edge_data in graph.out_edges(node, data=True):
        if edge_data["relation"].relationship_type == "spouse":
            return True
    for _, _, edge_data in graph.in_edges(node, data=True):
        if edge_data["relation"].relationship_type == "spouse":
            return True
    return False


def _check_coelebs(graph1, graph2, node_mapping):
    """Check that a person flagged as never-married (Coelebs) is not merged with a person who has
    spouse relationships or a married name, mirroring the logic in comparison.compare_person."""
    warnings = []

    for node1, node2 in node_mapping.items():
        person1 = graph1.nodes[node1]["person"]
        person2 = graph2.nodes[node2]["person"]

        if person1.has_fact("Coelebs"):
            names2 = person2.get_names()
            if _has_spouse_edge(graph2, node2) or names2["married"]:
                warnings.append(PlausibilityWarning(
                    check="coelebs",
                    severity="warning",
                    message="{} is flagged as never-married (Coelebs) but {} has spouse "
                             "relationships or a married name".format(node1[:7], node2[:7])))

        if person2.has_fact("Coelebs"):
            names1 = person1.get_names()
            if _has_spouse_edge(graph1, node1) or names1["married"]:
                warnings.append(PlausibilityWarning(
                    check="coelebs",
                    severity="warning",
                    message="{} is flagged as never-married (Coelebs) but {} has spouse "
                             "relationships or a married name".format(node2[:7], node1[:7])))

    return warnings


def score_proposal(graph1, graph2, node_mapping):
    """Score a proposed merge (a McGregor node mapping between two twigs) for biological plausibility.

    Args:
        graph1 (nx.DiGraph): The graph containing the nodes that are keys of node_mapping.
        graph2 (nx.DiGraph): The graph containing the nodes that are values of node_mapping.
        node_mapping (dict): Mapping from node identifiers in graph1 to node identifiers in graph2,
            as produced by mcgregor.mcgregor()'s maximal_common_subgraphs.

    Returns:
        PlausibilityResult
    """
    logger = logging.getLogger(__name__)

    warnings = []
    warnings.extend(_check_parent_child_ages(graph1, graph2, node_mapping))
    warnings.extend(_check_spouse_ages(graph1, graph2, node_mapping))
    warnings.extend(_check_coelebs(graph1, graph2, node_mapping))

    num_errors = sum(1 for w in warnings if w.severity == "error")
    num_warnings = sum(1 for w in warnings if w.severity == "warning")
    score = 1.0 - (WARNING_PENALTY * num_warnings) - (ERROR_PENALTY * num_errors)
    score = max(0.0, min(1.0, score))

    if warnings:
        logger.debug("scored proposal: %s warnings, %s errors, score=%.2f", num_warnings, num_errors, score)

    return PlausibilityResult(warnings=warnings, score=score)
