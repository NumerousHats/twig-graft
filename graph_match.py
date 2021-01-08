import itertools
from collections import defaultdict
import networkx as nx
import comparison
from mcgregor import mcgregor


def node_match(g1, g2, node1, node2):
    return not comparison.person_mismatch(g1.nodes[node1]["person"], g2.nodes[node2]["person"])


def edge_match(g1, g2, n1_in_g1, n2_in_g1, n1_in_g2, n2_in_g2):
    return g1.edges[n1_in_g1, n2_in_g1]["relation"] == g2.edges[n1_in_g2, n2_in_g2]["relation"]


def locations_in_component(people):
    """Return set of all distinct Locations associated with all Persons in a list."""
    loc_lists = [person.get_locations() for person in people]
    locations = [item for sublist in loc_lists for item in sublist]
    return set(locations)


def components_by_location(people_graph):
    """Return a representative node from each component associated with a given Location"""
    loc_components = defaultdict(list)
    components = list(nx.weakly_connected_components(people_graph.graph))
    for comp_nodes in components:
        locations = locations_in_component([people_graph.people[node] for node in comp_nodes])
        for location in locations:
            loc_components[location].append(comp_nodes)

    return loc_components


def match_components_in_location(the_graph):
    loc_components = components_by_location(the_graph)
    for location in loc_components.keys():
        print("\n###############################\n")
        print("Doing location {}".format(location))

        components = loc_components[location]
        if len(components) == 1:
            continue

        for comp1nodes, comp2nodes in itertools.combinations(components, 2):
            comp1 = the_graph.graph.subgraph(comp1nodes)
            comp2 = the_graph.graph.subgraph(comp2nodes)

            mcs = mcgregor(comp1, comp2, node_comparison=node_match, edge_comparison=edge_match)
            if mcs.maximal_common_subgraphs:
                print("\n========================================\n")

                if len(comp1nodes) > 1:
                    for pid1, pid2 in comp1.edges:
                        print(the_graph.relation_str(pid1, pid2) + "\n")
                else:
                    for pid in comp1nodes:
                        print(the_graph.people[pid])

                print("\n............\n")

                if len(comp2nodes) > 1:
                    for pid1, pid2 in comp2.edges:
                        print(the_graph.relation_str(pid1, pid2) + "\n")
                else:
                    for pid in comp2nodes:
                        print(the_graph.people[pid])

                print("\n\n++++++++++++++++++++++++++++++++++\n\n")

                print(mcs)
                for matching in mcs.maximal_common_subgraphs:
                    print("\n--------------------------\n")
                    for p1, p2 in matching.items():
                        print("matched {} to {}".format(the_graph.graph.nodes[p1]["person"],
                                                        the_graph.graph.nodes[p2]["person"]))
