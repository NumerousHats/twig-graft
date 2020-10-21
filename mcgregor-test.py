from data_model import *
import graph_model

import logging
import logging.config
import networkx as nx


class NodeMatching:
    """Encapsulates the node matching of two graphs.

    Attributes:
        graph1 (nx.Graph): The smaller of the two input graphs.
        graph2 (nx.Graph): The larger of the two input graphs.
        g1nodes (list or nx.NodeView): The nodes of g1 arranged in priority order.
        g2nodes (list or nx.NodeView): The nodes of g2 arranged in priority order.
        assignments (dict): The current node matching (g1 nodes as keys, g2 nodes as values).
        maximal_edges (int): The number of edges in the largest common subgraph found up to this point.
    """
    def __init__(self, graph1, graph2, g1nodes, g2nodes):
        self.graph1 = graph1
        self.graph2 = graph2
        self.g1nodes = g1nodes
        self.g2nodes = g2nodes

        self.maximal_edges = 0
        self.assignments = {}


def node_match(node1, node2):
    return node1["stuff"] == node2["stuff"]


def edge_match(edge1, edge2):
    pass


def mcgregor(graph1, graph2, node_comp=None, edge_comp=None):
    """Implements (or will implement, as the case may be) a recursive version of the McGregor algorithm
    for finding the maximal common node-induced subgraph of two input graphs subject to constraints on
    node and edge attributes.

     Args:
         graph1 (nx.Graph): The first input graph.
         graph2 (nx.Graph): The second input graph.
         node_comp: A function that returns True if two nodes are compatible in terms of attributes
         edge_comp: A function that returns True if two edges are compatible in terms of attributes

     Returns:
         Some sort of object that encapsulates the maximal common subgraph(s) and associated node matching(s).
    """

    def assign(matching):
        """The recursive function that performs a depth-first branch-and-bound search of the node
        matching space.

         Args:
             matching (NodeMatching): The current state of the node matching.
        """

        if matching.assignments:
            # TODO construct the common subgraph induced by the current node matching
            # TODO terminate early if the number of remaining feasible edges is too small
            pass

        g1todo = [x for x in matching.g1nodes if x not in matching.assignments.keys()]
        if g1todo:
            g1node = g1todo[0]
            for g2node in [x for x in matching.g2nodes if x not in list(matching.assignments.values())]:
                # TODO determine if g2node is consistent with g1node
                # TODO determine if any edges involving g1node and g2node are inconsistent
                matching.assignments[g1node] = g2node
                assign(matching)
            del matching.assignments[g1node]
        else:
            # recursion has bottomed out
            print(" ".join(["{}{}".format(k, v) for k, v in matching.assignments.items()]))
            # TODO if maximal, add to match object

    if graph1.number_of_nodes() < graph2.number_of_nodes():
        small = graph1
        big = graph2
    else:
        small = graph2
        big = graph1

    mcs = NodeMatching(small, big, small.nodes, big.nodes)
    assign(mcs)


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

    mcgregor(blob1, blob2)


if __name__ == "__main__":
    main()
