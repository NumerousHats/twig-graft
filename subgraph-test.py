from data_model import *
import graph_model

import logging
import logging.config
import json
import itertools
import networkx as nx
from networkx.algorithms import isomorphism
import comparison


def node_match(node1, node2):
    try:
        print("{} vs {}".format(node1["person"], node2["person"]))
        if comparison.person_mismatch(node1["person"], node2["person"]):
            return False
    except KeyError:
        return True
    return True


def main():
    logging.basicConfig(format='%(asctime)s %(name)-12s %(levelname)-8s %(message)s', level=logging.INFO)

    with open('testgraph.json') as f:
        input_json = json.load(f)

    the_graph = graph_model.PeopleGraph(graph_json=input_json)

    components = list(nx.weakly_connected_components(the_graph.graph))
    for comp1nodes, comp2nodes in itertools.combinations(components, 2):
        comp1 = the_graph.graph.subgraph(comp1nodes)
        comp2 = the_graph.graph.subgraph(comp2nodes)

        matcher = isomorphism.DiGraphMatcher(comp1, comp2, node_match=node_match)
        for match_set in matcher.subgraph_isomorphisms_iter():
            print("\n\nmatch set start\n")
            for p1 in match_set.keys():
                print("matched {} to {}".format(the_graph.people[p1], the_graph.people[match_set[p1]]))


if __name__ == "__main__":
    main()
