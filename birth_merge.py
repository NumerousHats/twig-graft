import json
import logging
from collections import defaultdict
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
    print("\n")
    for node in twig:
        print(str(graph.nodes[node]["person"]))
    print("\n")

    twig_graph = graph.subgraph(twig)

    for u, v, a in twig_graph.edges.data('relation'):
        print("{} {} {}".format(u[:7], v[:7], a.relationship_type))


def add_processed_twig(new_twig, new_twig_surnames, processed_twigs, surname_index):
    id = str(uuid.uuid4())
    processed_twigs[id] = new_twig
    for name in new_twig_surnames:
        surname_index[name] = surname_index[name] | {id}


def main():
    logging.basicConfig(format='%(asctime)s %(name)-12s %(levelname)-8s %(message)s', level=logging.DEBUG)
    logging.getLogger('mcgregor').setLevel(logging.WARNING)
    logging.getLogger('comparison').setLevel(logging.WARNING)
    logger = logging.getLogger(__name__)

    with open('dum.json') as f:
        input_json = json.load(f)

    the_graph_model = graph_model.PeopleGraph(graph_json=input_json)
    the_graph = the_graph_model.graph
    the_graph_not_merged = the_graph.subgraph([node for node in the_graph.nodes
                                               if not the_graph.nodes[node]["person"].merged])
    twig_queue = sorted(list(nx.weakly_connected_components(the_graph_not_merged)), key=len)
    processed_twigs = {}
    surname_index = defaultdict(set)

    minimum_match_size = 5

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

        merge_successful = False
        for target_key in targets:
            target_twig = deepcopy(processed_twigs[target_key])
            logger.debug("attempting to merge {} with {}".format(new_twig, target_twig))
            target_twig_graph = the_graph.subgraph(target_twig)
            if len(new_twig) < len(target_twig):
                flipped = False
                mcs = mcgregor(new_twig_graph, target_twig_graph,
                               node_comparison=node_match, edge_comparison=edge_match)
            else:
                flipped = True
                mcs = mcgregor(target_twig_graph, new_twig_graph,
                               node_comparison=node_match, edge_comparison=edge_match)

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

            logger.debug("good match, merging")
            merge_successful = True
            for p1, p2 in match.items():
                # get predecessors and successors pre-merge for later use
                p1_succ = {node for node in the_graph.successors(p1) if not the_graph.nodes[node]["person"].merged}
                p1_pred = {node for node in the_graph.predecessors(p1) if not the_graph.nodes[node]["person"].merged}
                p2_succ = {node for node in the_graph.successors(p2) if not the_graph.nodes[node]["person"].merged}
                p2_pred = {node for node in the_graph.predecessors(p2) if not the_graph.nodes[node]["person"].merged}

                # merge nodes
                merged_person, p1_merge_rel, p2_merge_rel = the_graph.nodes[p1]["person"].\
                    merge(the_graph.nodes[p2]["person"])
                merged_id = merged_person.identifier
                the_graph_model.people[merged_id] = merged_person
                the_graph.add_node(merged_id, person=merged_person)
                the_graph.add_edge(p1_merge_rel.from_id, p1_merge_rel.to_id, relation=p1_merge_rel)
                the_graph.add_edge(p2_merge_rel.from_id, p2_merge_rel.to_id, relation=p2_merge_rel)
                target_twig.append(merged_id)

                # reroute or merge edges
                for neighbor in p1_succ - p2_succ:
                    logger.debug("rerouting ({0}, {1}) to ({2}, {1})".format(p1, neighbor, merged_id))
                    relation = the_graph.edges[p1, neighbor]["relation"]
                    relation.from_id = merged_id
                    the_graph.remove_edge(p1, neighbor)
                    the_graph.add_edge(merged_id, neighbor, relation=relation)
                for neighbor in p2_succ - p1_succ:
                    logger.debug("rerouting ({0}, {1}) to ({2}, {1})".format(p2, neighbor, merged_id))
                    relation = the_graph.edges[p2, neighbor]["relation"]
                    relation.from_id = merged_id
                    the_graph.remove_edge(p2, neighbor)
                    the_graph.add_edge(merged_id, neighbor, relation=relation)
                for neighbor in p1_pred - p2_pred:
                    logger.debug("rerouting ({1}, {0}) to ({1}, {2})".format(p1, neighbor, merged_id))
                    relation = the_graph.edges[neighbor, p1]["relation"]
                    relation.to_id = merged_id
                    the_graph.remove_edge(neighbor, p1)
                    the_graph.add_edge(neighbor, merged_id, relation=relation)
                for neighbor in p2_pred - p1_pred:
                    logger.debug("rerouting ({1}, {0}) to ({1}, {2})".format(p2, neighbor, merged_id))
                    relation = the_graph.edges[neighbor, p2]["relation"]
                    relation.to_id = merged_id
                    the_graph.remove_edge(neighbor, p2)
                    the_graph.add_edge(neighbor, merged_id, relation=relation)

                for neighbor in p1_succ & p2_succ:
                    logger.debug("doing edge merge of ({0}, {2}) to ({1}, {2}) and connecting to {3}".format(p1,
                                                                                                             p2,
                                                                                                             neighbor,
                                                                                                             merged_id))
                    relation1 = the_graph.edges[p1, neighbor]["relation"]
                    relation1.from_id = merged_id
                    relation2 = the_graph.edges[p2, neighbor]["relation"]
                    relation2.from_id = merged_id
                    merged_relation = relation1.merge(relation2)
                    the_graph.remove_edge(p1, neighbor)
                    the_graph.remove_edge(p2, neighbor)
                    the_graph.add_edge(merged_id, neighbor, relation=merged_relation)
                for neighbor in p1_pred & p2_pred:
                    logger.debug("doing edge merge of ({2}, {0}) to ({2}, {1}) and connecting to {3}".format(p1,
                                                                                                             p2,
                                                                                                             neighbor,
                                                                                                             merged_id))
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

            # we're done, no need to look for further matches
            target_twig = [person for person in target_twig if not the_graph.nodes[person]["person"].merged]
            processed_twigs[target_key] = target_twig
            break

        if not merge_successful:
            add_processed_twig(new_twig, new_twig_surnames, processed_twigs, surname_index)

    with open('dum2.json', 'w') as json_file:
        json.dump(the_graph_model.json(), json_file, indent=2)


if __name__ == "__main__":
    main()
