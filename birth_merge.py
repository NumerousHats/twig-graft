import json
import logging
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
    components_queue = sorted(list(nx.weakly_connected_components(the_graph_not_merged)), key=len, reverse=True)
    processed_components = []

    while components_queue:
        component = list(components_queue.pop())
        component_graph = the_graph.subgraph(component)

        if not processed_components:
            processed_components = [component]
            continue

        for target in processed_components:
            logger.debug("attempting to merge {} with {}".format(component, target))
            target_graph = the_graph.subgraph(target)
            if len(component) < len(target):
                flipped = False
                mcs = mcgregor(component_graph, target_graph, node_comparison=node_match, edge_comparison=edge_match)
            else:
                flipped = True
                mcs = mcgregor(target_graph, component_graph, node_comparison=node_match, edge_comparison=edge_match)

            if not mcs.maximal_common_subgraphs:
                processed_components.append(component)
                continue
            if len(mcs.maximal_common_subgraphs) > 1:
                logger.info("multiple maximal common subgraphs, skipping")
                processed_components.append(component)
                continue

            match = mcs.maximal_common_subgraphs[0]
            if len(match) < 5:
                logger.debug("match not big enough")
                processed_components.append(component)
                continue

            logger.debug("good match, merging")
            for p1, p2 in match.items():
                # merge nodes
                merged_person, p1_merge_rel, p2_merge_rel = the_graph.nodes[p1]["person"].\
                    merge(the_graph.nodes[p2]["person"])
                merged_id = merged_person.identifier
                the_graph_model.people[merged_id] = merged_person
                the_graph.add_node(merged_id, person=merged_person)
                the_graph.add_edge(p1_merge_rel.from_id, p1_merge_rel.to_id, relation=p1_merge_rel)
                the_graph.add_edge(p2_merge_rel.from_id, p2_merge_rel.to_id, relation=p2_merge_rel)

                # update nodes in target
                target.append(merged_person.identifier)
                if p1 in target:
                    target.remove(p1)
                if p2 in target:
                    target.remove(p2)

                # reroute or merge edges
                p1_succ = set(the_graph.successors(p1))
                p1_pred = set(the_graph.predecessors(p1))
                p2_succ = set(the_graph.successors(p2))
                p2_pred = set(the_graph.predecessors(p2))

                for neighbor in p1_succ - p2_succ:
                    # reroute (p1, neighbor) edge to (merged_person, neighbor)
                    pass
                for neighbor in p2_succ - p1_succ:
                    # reroute (p2, neighbor) edge to (merged_person, neighbor)
                    pass
                for neighbor in p1_pred - p2_pred:
                    # reroute (neighbor, p1) edge to (neighbor, merged_person)
                    pass
                for neighbor in p2_pred - p1_pred:
                    # reroute (neighbor, p2) edge to (neighbor, merged_person)
                    pass

                for neighbor in p1_succ & p2_succ:
                    # merge the (p1, neighbor) and (p2, neighbor) edges and connect it to merged_person
                    pass
                for neighbor in p1_pred & p2_pred:
                    # merge the (neighbor, p1) and (neighbor, p2) edges and connect it to merged_person
                    pass

            # add any additional component nodes to target
            for person in component:
                if person not in target and not the_graph.nodes[person]["person"].merged:
                    target.append(person)

    with open('dum2.json', 'w') as json_file:
        json.dump(the_graph_model.json(), json_file, indent=2)


if __name__ == "__main__":
    main()
