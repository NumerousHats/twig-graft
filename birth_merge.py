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
    # logging.basicConfig(format='%(asctime)s %(name)-12s %(levelname)-8s %(message)s', level=logging.DEBUG)

    with open('dum.json') as f:
        input_json = json.load(f)

    the_graph_model = graph_model.PeopleGraph(graph_json=input_json)
    the_graph = the_graph_model.graph  # but filter out merged nodes
    original_components = sorted(list(nx.weakly_connected_components(the_graph)), key=len, reverse=True)
    processed_components = None

    for component in original_components:
        component_graph = the_graph.subgraph(component)
        if processed_components:
            for target in processed_components:
                target_graph = the_graph.subgraph(target)
                mcs = mcgregor(component_graph, target_graph, node_comparison=node_match, edge_comparison=edge_match)

                if len(mcs.maximal_common_subgraphs) == 1:
                    match = mcs.maximal_common_subgraphs[0]
                    if len(match) > 5:
                        print("\n\n++++++++++++++++++++++++++++++++++\n\n")
                        print(mcs)
                        for matching in mcs.maximal_common_subgraphs:
                            print("\n--------------------------\n")
                            for p1, p2 in matching.items():
                                print("matched {} to {}".format(the_graph.nodes[p1]["person"],
                                                                the_graph.nodes[p2]["person"]))
                        # merge
                        # reconstruct the target based on merge result

                else:
                    print("multiple maximal common subgraphs, skipping")

            processed_components.append(component)
        else:
            processed_components = [component]


if __name__ == "__main__":
    main()
