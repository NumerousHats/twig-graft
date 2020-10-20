from data_model import *
import graph_model

import logging
import logging.config
import copy
import networkx as nx


def node_match(node1, node2):
    return node1["stuff"] == node2["stuff"]


def edge_match(edge1, edge2):
    pass


def mcgregor(graph1, graph2):
    def match(g1, g2, g1nodes, g2nodes, matches):
        if g1nodes:
            target = g1nodes.pop(0)
            for g2n in g2nodes:
                temp2 = copy.copy(g2nodes)
                temp2.remove(g2n)
                match(g1, g2, g1nodes, temp2, )

    if graph1.number_of_nodes() < graph2.number_of_nodes():
        small = graph1
        big = graph2
    else:
        small = graph2
        big = graph1

    # node_matches = defaultdict(list)
    # for s_key in small.nodes.keys():
    #     for b_key in big.nodes.keys():
    #         if node_match(small.nodes[s_key], big.nodes[b_key]):
    #             node_matches[s_key].append(b_key)


def assign(g1nodes, g2nodes, assignments=None):
    if assignments is None:
        assignments = {}

    g1todo = [x for x in g1nodes if x not in assignments.keys()]
    if g1todo:
        g1node = g1todo[0]
        for g2node in [x for x in g2nodes if x not in list(assignments.values())]:
            assignments[g1node] = g2node
            assign(g1nodes, g2nodes, assignments)
        del assignments[g1node]
    else:
        print(assignments)


def main():
    logging.basicConfig(format='%(asctime)s %(name)-12s %(levelname)-8s %(message)s', level=logging.INFO)

    # blob1 = nx.read_gml("blob1lab.gml")
    # blob2 = nx.read_gml("blob2lab.gml")

    blob1 = nx.Graph()
    blob1.add_edge("A", "B")
    blob1.add_edge("A", "C")
    blob1.add_edge("C", "B")
    blob1.add_edge("C", "D")
    blob1.add_edge("D", "E")

    blob2 = nx.Graph()
    blob2.add_edge("a", "c")
    blob2.add_edge("b", "c")
    blob2.add_edge("c", "d")
    blob2.add_edge("d", "g")
    blob2.add_edge("d", "e")
    blob2.add_edge("e", "f")
    blob2.add_edge("f", "g")

    assign(blob1.nodes, blob2.nodes)


if __name__ == "__main__":
    main()
