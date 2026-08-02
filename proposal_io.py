"""Serialization for merge proposals.

This module provides a JSON round-trip for `MergeProposal` objects and their
`plausibility.PlausibilityResult` scores, plus the on-disk format used to exchange
pre-generated proposals between `generate_proposals.py` and `merge_review_app.py`.

The point of the on-disk format is to separate the (slow) proposal generation step -- running
McGregor subgraph matching and scoring every candidate -- from the (fast, interactive) review step.
The generation script writes a self-contained file that embeds the graph the proposals were
generated against, so the review app never needs to re-run any comparisons and cannot get out of
sync with the graph.

On-disk format (format name "twig_grafter_proposals", version 1):

    {
        "format": "twig_grafter_proposals",
        "version": 1,
        "generated_at": "2026-08-02T12:00:00.000000",
        "input_file": "dum.json",
        "minimum_match_size": 5,
        "graph": {"persons": [...], "relations": [...]},
        "proposals": [
            {
                "index": 0,
                "target_twig_id": "...",
                "new_twig": [...],
                "target_twig": [...],
                "node_mapping": {...},
                "match_size": 3,
                "plausibility": {"score": 0.8, "warnings": [{"check": "...", "severity": "...", "message": "..."}]},
                "conflict": false,
                "conflict_reason": null,
                "conflicts_with": []
            },
            ...
        ],
        "decisions": {"0": "approved", "3": "rejected"}
    }
"""

import datetime
import json

from birth_merge import MergeProposal
from plausibility import PlausibilityResult, PlausibilityWarning

FORMAT = "twig_grafter_proposals"
VERSION = 1


def plausibility_to_dict(result):
    """Serialize a PlausibilityResult (or None) to a JSON-serializable dict."""
    if result is None:
        return None
    return {
        "score": result.score,
        "warnings": [
            {"check": w.check, "severity": w.severity, "message": w.message}
            for w in result.warnings
        ],
    }


def plausibility_from_dict(data):
    """Rebuild a PlausibilityResult from the dict produced by plausibility_to_dict."""
    if data is None:
        return None
    warnings = [
        PlausibilityWarning(check=w["check"], severity=w["severity"], message=w["message"])
        for w in data.get("warnings", [])
    ]
    return PlausibilityResult(warnings=warnings, score=data.get("score", 1.0))


def proposal_to_dict(proposal, index):
    """Serialize a MergeProposal to a JSON-serializable dict, including its batch index."""
    return {
        "index": index,
        "target_twig_id": proposal.target_twig_id,
        "new_twig": list(proposal.new_twig),
        "target_twig": list(proposal.target_twig),
        "node_mapping": dict(proposal.node_mapping),
        "match_size": proposal.match_size,
        "plausibility": plausibility_to_dict(proposal.plausibility),
        "conflict": proposal.conflict,
        "conflict_reason": proposal.conflict_reason,
        "conflicts_with": list(proposal.conflicts_with),
    }


def proposal_from_dict(data):
    """Rebuild a MergeProposal from the dict produced by proposal_to_dict."""
    return MergeProposal(
        target_twig_id=data["target_twig_id"],
        new_twig=list(data["new_twig"]),
        target_twig=list(data["target_twig"]),
        node_mapping=dict(data["node_mapping"]),
        match_size=data["match_size"],
        plausibility=plausibility_from_dict(data.get("plausibility")),
        conflict=data.get("conflict", False),
        conflict_reason=data.get("conflict_reason"),
        conflicts_with=list(data.get("conflicts_with", [])),
    )


def write_proposals_file(path, graph_json, proposals, decisions=None,
                         minimum_match_size=None, input_file=None):
    """Write a proposals file containing the embedded graph, every proposal, and any decisions.

    Args:
        path (str): Destination file path.
        graph_json (dict): The PeopleGraph JSON ("persons" / "relations") the proposals were
            generated against.
        proposals (list of MergeProposal): The proposals to persist.
        decisions (dict or None): Mapping from proposal index to decision string, if any.
        minimum_match_size (int or None): The minimum match size used to generate the proposals.
        input_file (str or None): The path of the graph JSON the proposals were generated from.
    """
    document = {
        "format": FORMAT,
        "version": VERSION,
        "generated_at": datetime.datetime.now().isoformat(),
        "input_file": input_file,
        "minimum_match_size": minimum_match_size,
        "graph": graph_json,
        "proposals": [proposal_to_dict(p, i) for i, p in enumerate(proposals)],
        "decisions": {str(k): v for k, v in (decisions or {}).items()},
    }
    with open(path, "w") as f:
        json.dump(document, f, indent=2)


def read_proposals_file(path):
    """Read a proposals file produced by write_proposals_file (or generate_proposals.py).

    Returns:
        dict with keys: "graph_json", "proposals" (list of MergeProposal), "decisions"
        (dict of str -> str), "generated_at", "input_file", "minimum_match_size".
    """
    with open(path) as f:
        document = json.load(f)

    if document.get("format") != FORMAT:
        raise ValueError("not a {} proposals file: {}".format(FORMAT, path))
    if document.get("version") != VERSION:
        raise ValueError("unsupported {} version {} in {}".format(
            FORMAT, document.get("version"), path))

    proposals = [proposal_from_dict(d) for d in document["proposals"]]
    decisions = {}
    for k, v in document.get("decisions", {}).items():
        try:
            decisions[int(k)] = v
        except (TypeError, ValueError):
            decisions[k] = v
    return {
        "graph_json": document["graph"],
        "proposals": proposals,
        "decisions": decisions,
        "generated_at": document.get("generated_at"),
        "input_file": document.get("input_file"),
        "minimum_match_size": document.get("minimum_match_size"),
    }


def write_decisions(path, decisions):
    """Update the decisions in an existing proposals file in place, preserving everything else."""
    with open(path) as f:
        document = json.load(f)
    document["decisions"] = {str(k): v for k, v in decisions.items()}
    with open(path, "w") as f:
        json.dump(document, f, indent=2)
