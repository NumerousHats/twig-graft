import json
import logging
from collections import defaultdict
from dataclasses import dataclass, field
import uuid
from copy import deepcopy

import networkx as nx

import comparison
import graph_model
from mcgregor import mcgregor


def node_match(g1, g2, node1, node2):
    return not comparison.person_mismatch(g1.nodes[node1]["person"], g2.nodes[node2]["person"])


def edge_match(g1, g2, n1_in_g1, n2_in_g1, n1_in_g2, n2_in_g2):
    type1 = g1.edges[n1_in_g1, n2_in_g1]["relation"].relationship_type
    type2 = g2.edges[n1_in_g2, n2_in_g2]["relation"].relationship_type
    return type1 == type2


def twig_dump(twig, graph):
    out = ["\n"]
    for node in twig:
        out.append(str(graph.nodes[node]["person"]))
    out.append("\n")

    twig_graph = graph.subgraph(twig)

    for u, v, a in twig_graph.edges.data('relation'):
        out.append("{} {} {}".format(u[:7], v[:7], a.relationship_type))

    return "\n".join(out)


def add_processed_twig(new_twig, new_twig_surnames, processed_twigs, surname_index):
    id = str(uuid.uuid4())
    processed_twigs[id] = new_twig
    for name in new_twig_surnames:
        surname_index[name] = surname_index[name] | {id}
    return id


def sanity_check(graph):
    logger = logging.getLogger(__name__)
    for node in graph.nodes:
        try:
            val = graph.nodes[node]["person"]
        except KeyError:
            logger.warning("missing person for node {}".format(node))
            raise


@dataclass
class MergeProposal:
    """A candidate merge between two twigs, as found by the McGregor maximal common subgraph search.

    Proposals are generated against a single, fixed snapshot of the graph (see `generate_proposals`);
    none of the merges they describe have actually been applied to the graph yet. Applying a proposal
    is a separate step (see `apply_merge`), which allows a human reviewer to inspect, score, and
    approve/reject proposals before any graph mutation happens.

    Attributes:
        target_twig_id (str): The identifier (in the `processed_twigs` sense) of the twig that
            `new_twig` is proposed to be merged into.
        new_twig (list of str): Node identifiers of the incoming twig.
        target_twig (list of str): Node identifiers of the target twig, as they existed when the
            proposal was generated.
        node_mapping (dict): Mapping from node identifiers in one twig to their proposed
            correspondence in the other, as produced by `mcgregor.mcgregor`.
        match_size (int): The number of node pairs in `node_mapping`.
        plausibility (plausibility.PlausibilityResult or None): Filled in by the caller after scoring.
        conflict (bool): True if this proposal shares one or more nodes with another proposal in the
            same batch (see `detect_conflicts`), meaning both proposals cannot be applied.
        conflict_reason (str or None): A human-readable explanation of the conflict, if any.
        conflicts_with (list of int): Indices (within the same proposals list passed to
            `detect_conflicts`) of the other proposals this one conflicts with. Empty if there is no
            conflict.
    """
    target_twig_id: str
    new_twig: list
    target_twig: list
    node_mapping: dict
    match_size: int
    plausibility: object = None
    conflict: bool = False
    conflict_reason: str = None
    conflicts_with: list = field(default_factory=list)


def generate_proposals(the_graph, minimum_match_size=5):
    """Find candidate twig merges without modifying the graph.

    This replays the same twig-queue/surname-index logic as the original merge loop, but instead of
    applying an accepted match immediately, it records a `MergeProposal` and moves on. All proposals
    are generated against the same, unmodified snapshot of `the_graph` -- i.e. `target_twig` in each
    proposal reflects the graph's state at call time, not the state after any other proposal (accepted
    or not) is applied. This means proposals can conflict with each other (see `detect_conflicts`).

    Args:
        the_graph (nx.DiGraph): The full people graph. Not modified by this function.
        minimum_match_size (int): The minimum number of matched node pairs required to accept a
            candidate match as a proposal.

    Returns:
        list of MergeProposal
    """
    logger = logging.getLogger(__name__)

    the_graph_not_merged = the_graph.subgraph([node for node in the_graph.nodes
                                               if not the_graph.nodes[node]["person"].merged])
    twig_queue = sorted(list(nx.weakly_connected_components(the_graph_not_merged)), key=len)
    processed_twigs = {}
    surname_index = defaultdict(set)
    proposals = []

    while twig_queue:
        new_twig = list(twig_queue.pop())
        if len(new_twig) < minimum_match_size:
            logger.debug("twig too small to achieve minimum match size, terminating")
            break

        new_twig_graph = the_graph.subgraph(new_twig)
        new_twig_surnames = [the_graph.nodes[person_id]["person"].standardized_surnames() for person_id in new_twig]
        new_twig_surnames = set().union(*new_twig_surnames)

        if not processed_twigs:
            add_processed_twig(new_twig, new_twig_surnames, processed_twigs, surname_index)
            continue

        targets = set()
        for name in new_twig_surnames:
            targets = targets | surname_index[name]

        if not targets:
            add_processed_twig(new_twig, new_twig_surnames, processed_twigs, surname_index)
            continue

        proposal_found = False
        for target_key in targets:
            target_twig = processed_twigs[target_key]
            logger.debug("attempting to match {} with {}".format(new_twig, target_twig))
            target_twig_graph = the_graph.subgraph(target_twig)
            try:
                if len(new_twig) < len(target_twig):
                    mcs = mcgregor(new_twig_graph, target_twig_graph,
                                   node_comparison=node_match, edge_comparison=edge_match)
                else:
                    mcs = mcgregor(target_twig_graph, new_twig_graph,
                                   node_comparison=node_match, edge_comparison=edge_match)
            except ValueError:
                logger.error("error during mcgregor with twig {} against {}".format(new_twig, target_key))
                raise

            if not mcs.maximal_common_subgraphs:
                logger.info("no common subgraph")
                continue
            if len(mcs.maximal_common_subgraphs) > 1:
                logger.info("multiple maximal common subgraphs, skipping")
                continue

            match = mcs.maximal_common_subgraphs[0]
            if len(match) < minimum_match_size:
                logger.debug("match not big enough")
                continue

            logger.info("proposing merge of twig against target {}".format(target_key))
            proposals.append(MergeProposal(
                target_twig_id=target_key,
                new_twig=list(new_twig),
                target_twig=list(target_twig),
                node_mapping=dict(match),
                match_size=len(match),
            ))
            proposal_found = True
            break

        if not proposal_found:
            add_processed_twig(new_twig, new_twig_surnames, processed_twigs, surname_index)

    return proposals


def detect_conflicts(proposals):
    """Flag proposals that cannot all be applied together because they share one or more nodes.

    Two proposals conflict if any node (from either side of the node_mapping) appears in both --
    since a given Person can only be merged once. This mutates `proposal.conflict` and
    `proposal.conflict_reason` in place for every proposal that has at least one conflicting peer.

    Args:
        proposals (list of MergeProposal)

    Returns:
        list of MergeProposal (the same list, mutated in place, returned for convenience)
    """
    node_to_proposals = defaultdict(list)
    for i, proposal in enumerate(proposals):
        nodes = set(proposal.node_mapping.keys()) | set(proposal.node_mapping.values())
        for node in nodes:
            node_to_proposals[node].append(i)

    for i, proposal in enumerate(proposals):
        nodes = set(proposal.node_mapping.keys()) | set(proposal.node_mapping.values())
        conflicting = set()
        for node in nodes:
            for j in node_to_proposals[node]:
                if j != i:
                    conflicting.add(j)
        if conflicting:
            proposal.conflict = True
            proposal.conflicts_with = sorted(conflicting)
            proposal.conflict_reason = "shares node(s) with proposal(s) {}".format(proposal.conflicts_with)
        else:
            proposal.conflict = False
            proposal.conflicts_with = []
            proposal.conflict_reason = None

    return proposals


def apply_merge(the_graph, new_twig, target_twig, node_mapping, spew=False):
    """Apply a single approved merge proposal to the live graph.

    Args:
        the_graph (nx.DiGraph): The full people graph. Modified in place.
        new_twig (list of str): Node identifiers of the incoming twig.
        target_twig (list of str): Node identifiers of the target twig, prior to this merge.
        node_mapping (dict): Mapping between node identifiers to be merged with one another.
        spew (bool): If True, print a diagnostic message on merge failure.

    Returns:
        (bool, list of str): A tuple of (success, updated_target_twig). If success is False, the
        merge was aborted (due to an edge-merge conflict) partway through and the graph may have been
        partially modified for pairs processed before the failure; updated_target_twig reflects
        whatever was completed before the abort.
    """
    logger = logging.getLogger(__name__)
    target_twig = list(target_twig)

    for p1, p2 in node_mapping.items():
        # get pre-merge predecessors and successors for later use
        p1_succ = {node for node in the_graph.successors(p1)
                   if not the_graph.nodes[node]["person"].merged}
        p1_pred = {node for node in the_graph.predecessors(p1)
                   if not the_graph.nodes[node]["person"].merged}
        p2_succ = {node for node in the_graph.successors(p2)
                   if not the_graph.nodes[node]["person"].merged}
        p2_pred = {node for node in the_graph.predecessors(p2)
                   if not the_graph.nodes[node]["person"].merged}

        try:  # check to make sure edge merge will actually work before committing
            for neighbor in p1_succ & p2_succ:
                test_relation1 = deepcopy(the_graph.edges[p1, neighbor]["relation"])
                test_relation1.from_id = "merged"
                test_relation2 = deepcopy(the_graph.edges[p2, neighbor]["relation"])
                test_relation2.from_id = "merged"
                test_relation1.merge(test_relation2)
            for neighbor in p1_pred & p2_pred:
                test_relation1 = deepcopy(the_graph.edges[neighbor, p1]["relation"])
                test_relation1.to_id = "merged"
                test_relation2 = deepcopy(the_graph.edges[neighbor, p2]["relation"])
                test_relation2.to_id = "merged"
                test_relation1.merge(test_relation2)
        except ValueError:
            logger.warning("aborting due to edge merge error")
            if spew:
                print("\nMERGE ERROR\n")
            return False, target_twig

        # merge nodes
        merged_person, p1_merge_rel, p2_merge_rel = the_graph.nodes[p1]["person"]. \
            merge(the_graph.nodes[p2]["person"])
        merged_id = merged_person.identifier
        the_graph.add_node(merged_id, person=merged_person)
        the_graph.add_edge(p1_merge_rel.from_id, p1_merge_rel.to_id, relation=p1_merge_rel)
        the_graph.add_edge(p2_merge_rel.from_id, p2_merge_rel.to_id, relation=p2_merge_rel)
        target_twig.append(merged_id)

        # reroute or merge edges
        for neighbor in p1_succ - p2_succ:
            relation = the_graph.edges[p1, neighbor]["relation"]
            relation.from_id = merged_id
            the_graph.remove_edge(p1, neighbor)
            the_graph.add_edge(merged_id, neighbor, relation=relation)
        for neighbor in p2_succ - p1_succ:
            relation = the_graph.edges[p2, neighbor]["relation"]
            relation.from_id = merged_id
            the_graph.remove_edge(p2, neighbor)
            the_graph.add_edge(merged_id, neighbor, relation=relation)
        for neighbor in p1_pred - p2_pred:
            relation = the_graph.edges[neighbor, p1]["relation"]
            relation.to_id = merged_id
            the_graph.remove_edge(neighbor, p1)
            the_graph.add_edge(neighbor, merged_id, relation=relation)
        for neighbor in p2_pred - p1_pred:
            relation = the_graph.edges[neighbor, p2]["relation"]
            relation.to_id = merged_id
            the_graph.remove_edge(neighbor, p2)
            the_graph.add_edge(neighbor, merged_id, relation=relation)

        for neighbor in p1_succ & p2_succ:
            relation1 = the_graph.edges[p1, neighbor]["relation"]
            relation1.from_id = merged_id
            relation2 = the_graph.edges[p2, neighbor]["relation"]
            relation2.from_id = merged_id
            merged_relation = relation1.merge(relation2)
            the_graph.remove_edge(p1, neighbor)
            the_graph.remove_edge(p2, neighbor)
            the_graph.add_edge(merged_id, neighbor, relation=merged_relation)
        for neighbor in p1_pred & p2_pred:
            relation1 = the_graph.edges[neighbor, p1]["relation"]
            relation1.to_id = merged_id
            relation2 = the_graph.edges[neighbor, p2]["relation"]
            relation2.to_id = merged_id
            merged_relation = relation1.merge(relation2)
            the_graph.remove_edge(neighbor, p1)
            the_graph.remove_edge(neighbor, p2)
            the_graph.add_edge(neighbor, merged_id, relation=merged_relation)

    # add any additional component nodes to target
    for person in new_twig:
        if person not in target_twig:
            target_twig.append(person)

    target_twig = [person for person in target_twig if not the_graph.nodes[person]["person"].merged]
    return True, target_twig


def main():
    logging.basicConfig(format='%(asctime)s %(name)-12s %(levelname)-8s %(message)s', level=logging.WARNING)
    logging.getLogger('mcgregor').setLevel(logging.WARNING)
    logging.getLogger('comparison').setLevel(logging.WARNING)
    logger = logging.getLogger(__name__)

    spew = True
    minimum_match_size = 5

    with open('dum.json') as f:
        input_json = json.load(f)

    the_graph_model = graph_model.PeopleGraph(graph_json=input_json)
    the_graph = the_graph_model.graph
    sanity_check(the_graph_model.graph)

    proposals = generate_proposals(the_graph, minimum_match_size=minimum_match_size)
    detect_conflicts(proposals)

    for proposal in proposals:
        if proposal.conflict:
            logger.warning("skipping conflicting proposal against target {}: {}".format(
                proposal.target_twig_id, proposal.conflict_reason))
            continue

        if spew:
            with open("twigdump_{}".format(proposal.target_twig_id), "a") as dumpfile:
                dumpfile.write("\n\n------------------- merging with ------------------------\n")
                dumpfile.write(twig_dump(proposal.new_twig, the_graph))
                dumpfile.write("\n\nusing the mapping\n\n")
                for p1, p2 in proposal.node_mapping.items():
                    dumpfile.write("{} --- {}\n".format(str(the_graph.nodes[p1]["person"]),
                                                        str(the_graph.nodes[p2]["person"])))

        success, target_twig = apply_merge(the_graph, proposal.new_twig, proposal.target_twig,
                                            proposal.node_mapping, spew=spew)
        if success:
            logger.warning("good match, merged into {}".format(proposal.target_twig_id))
            sanity_check(the_graph_model.graph)
            if spew:
                with open("twigdump_{}".format(proposal.target_twig_id), "a") as dumpfile:
                    dumpfile.write("\n\n------------------- merge result ------------------------\n")
                    dumpfile.write(twig_dump(target_twig, the_graph))
        else:
            logger.warning("merge failed for target {}".format(proposal.target_twig_id))

    logger.warning("finished")
    sanity_check(the_graph_model.graph)
    with open('dum2.json', 'w') as json_file:
        json.dump(the_graph_model.json(), json_file, indent=2)


if __name__ == "__main__":
    main()
