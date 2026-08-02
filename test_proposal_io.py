import json
import os

import pytest

from birth_merge import MergeProposal
from plausibility import PlausibilityResult, PlausibilityWarning
from proposal_io import (plausibility_from_dict, plausibility_to_dict,
                         proposal_from_dict, proposal_to_dict,
                         read_proposals_file, write_decisions, write_proposals_file)


def make_proposal(index=0, scored=True, conflicted=False):
    proposal = MergeProposal(
        target_twig_id="target-1234",
        new_twig=["n1", "n2", "n3"],
        target_twig=["m1", "m2", "m3"],
        node_mapping={"n1": "m1", "n2": "m2", "n3": "m3"},
        match_size=3,
    )
    if scored:
        proposal.plausibility = PlausibilityResult(
            warnings=[PlausibilityWarning(check="parent_age_gap", severity="warning",
                                          message="low age gap of 13.0 years")],
            score=0.8,
        )
    if conflicted:
        proposal.conflict = True
        proposal.conflict_reason = "shares node(s) with proposal(s) [1]"
        proposal.conflicts_with = [1]
    return proposal


def make_graph_json():
    return {"persons": [{"identifier": "n1", "gender": "m", "names": [], "facts": None,
                         "sources": [], "confidence": "normal"}],
            "relations": []}


def test_plausibility_round_trip():
    result = PlausibilityResult(
        warnings=[PlausibilityWarning(check="spouse_age_gap", severity="error",
                                      message="implausible age gap")],
        score=0.3,
    )
    rebuilt = plausibility_from_dict(plausibility_to_dict(result))
    assert rebuilt.score == 0.3
    assert len(rebuilt.warnings) == 1
    assert rebuilt.warnings[0].check == "spouse_age_gap"
    assert rebuilt.warnings[0].severity == "error"
    assert rebuilt.warnings[0].message == "implausible age gap"


def test_plausibility_none_round_trip():
    assert plausibility_to_dict(None) is None
    assert plausibility_from_dict(None) is None


def test_proposal_round_trip_scored():
    proposal = make_proposal(index=2)
    data = proposal_to_dict(proposal, index=2)
    assert data["index"] == 2

    rebuilt = proposal_from_dict(data)
    assert rebuilt.target_twig_id == "target-1234"
    assert rebuilt.new_twig == ["n1", "n2", "n3"]
    assert rebuilt.target_twig == ["m1", "m2", "m3"]
    assert rebuilt.node_mapping == {"n1": "m1", "n2": "m2", "n3": "m3"}
    assert rebuilt.match_size == 3
    assert rebuilt.plausibility is not None
    assert rebuilt.plausibility.score == 0.8
    assert rebuilt.plausibility.warnings[0].check == "parent_age_gap"
    assert rebuilt.conflict is False
    assert rebuilt.conflicts_with == []


def test_proposal_round_trip_conflicted():
    proposal = make_proposal(scored=False, conflicted=True)
    rebuilt = proposal_from_dict(proposal_to_dict(proposal, index=0))
    assert rebuilt.conflict is True
    assert rebuilt.conflict_reason == "shares node(s) with proposal(s) [1]"
    assert rebuilt.conflicts_with == [1]
    assert rebuilt.plausibility is None


def test_write_and_read_proposals_file(tmp_path):
    path = os.path.join(str(tmp_path), "proposals.json")
    proposals = [make_proposal(index=0, scored=True), make_proposal(index=1, scored=False)]
    decisions = {"0": "approved", "1": "deferred"}

    write_proposals_file(path, make_graph_json(), proposals,
                         decisions=decisions, minimum_match_size=5, input_file="dum.json")

    data = read_proposals_file(path)
    assert data["graph_json"]["persons"][0]["identifier"] == "n1"
    assert len(data["proposals"]) == 2
    assert data["decisions"] == {0: "approved", 1: "deferred"}
    assert data["minimum_match_size"] == 5
    assert data["input_file"] == "dum.json"
    assert data["proposals"][0].plausibility.score == 0.8
    assert data["proposals"][1].plausibility is None


def test_read_empty_decisions(tmp_path):
    path = os.path.join(str(tmp_path), "proposals.json")
    write_proposals_file(path, make_graph_json(), [make_proposal(scored=False)])
    data = read_proposals_file(path)
    assert data["decisions"] == {}
    assert len(data["proposals"]) == 1


def test_read_rejects_wrong_format(tmp_path):
    path = os.path.join(str(tmp_path), "bad.json")
    with open(path, "w") as f:
        json.dump({"format": "something_else", "version": 1, "graph": {}, "proposals": []}, f)
    with pytest.raises(ValueError):
        read_proposals_file(path)


def test_read_rejects_unsupported_version(tmp_path):
    path = os.path.join(str(tmp_path), "bad.json")
    with open(path, "w") as f:
        json.dump({"format": "twig_grafter_proposals", "version": 99, "graph": {},
                   "proposals": []}, f)
    with pytest.raises(ValueError):
        read_proposals_file(path)


def test_write_decisions_preserves_rest(tmp_path):
    path = os.path.join(str(tmp_path), "proposals.json")
    write_proposals_file(path, make_graph_json(), [make_proposal(scored=False)],
                         decisions={}, minimum_match_size=5)

    write_decisions(path, {"0": "approved"})

    data = read_proposals_file(path)
    assert data["decisions"] == {0: "approved"}
    assert data["minimum_match_size"] == 5
    assert len(data["proposals"]) == 1
