from data_model import *
import graph_model

import logging
import logging.config
import math
import networkx as nx


class NodeMatching:
    """Encapsulates the node matching of two graphs.

    Attributes:
        graph1 (nx.Graph): The input graph with the smaller number of nodes.
        graph2 (nx.Graph): The input graph with the larger number of nodes.
        g1nodes (list or nx.NodeView): The nodes of g1 arranged in priority order.
        g2nodes (list or nx.NodeView): The nodes of g2 arranged in priority order.
        assignments (dict): The current node matching (g1 nodes as keys, g2 nodes as values).
        maximal_edges_removed (int): The number of edges that needed to be removed in the in the
            largest common subgraph found up to this point. If edges_removed > maximal_edges_removed,
            then the recursion can be terminated. If a larger common subgraph is found, then
            maximal_edges_removed will decrease.
    """
    def __init__(self, graph1, graph2, g1nodes, g2nodes):
        self.graph1 = graph1
        self.graph2 = graph2
        self.g1nodes = g1nodes
        self.g2nodes = g2nodes

        self.edges_removed = 0
        self.maximal_edges_removed = math.inf
        self.assignments = {}

    def __str__(self):
        assignments = " ".join(["{};{}".format(k, v) for k, v in self.assignments.items()])
        return "[{}] with {} edges removed".format(assignments, self.edges_removed)


def node_match(node1, node2):
    # return node1["stuff"] == node2["stuff"]
    return True


def edge_match(edge1, edge2):
    return True


def mcgregor(graph1, graph2, node_comparison, edge_comparison):
    """Implements (or will implement, as the case may be) a recursive version of the McGregor algorithm
    for finding the maximal common node-induced subgraph of two input graphs subject to constraints on
    node and edge attributes.

     Args:
         graph1 (nx.Graph): The first input graph.
         graph2 (nx.Graph): The second input graph.
         node_comparison: A function that returns True if two nodes are compatible in terms of attributes
         edge_comparison: A function that returns True if two edges are compatible in terms of attributes

     Returns:
         A list of NodeMatching object(s) that contain the maximal common subgraph(s) and
         associated node matching(s).
    """

    def assign(matching):
        """The recursive function that performs a depth-first branch-and-bound search of the node
        matching solution space.

         Args:
             matching (NodeMatching): The current state of the node matching.
        """

        starting_edges_removed = matching.edges_removed
        g1todo = [x for x in matching.g1nodes if x not in matching.assignments.keys()]
        if g1todo:
            g1node = g1todo[0]
            g1_possible_edges = [(n1, n2) for (n1, n2) in graph1.edges(g1node)
                                 if n2 in matching.assignments.keys()]
            # n1 will always be g1node

            for g2node in [x for x in matching.g2nodes if x not in list(matching.assignments.values())]:
                if not node_comparison(g1node, g2node):
                    continue

                edges_removed = starting_edges_removed
                for n1, n2 in g1_possible_edges:
                    n1_2 = matching.assignments.get(n1, g2node)
                    n2_2 = matching.assignments.get(n2, g2node)
                    if graph2.has_edge(n1_2, n2_2):
                        pass
                        # TODO determine if any edges involving g1node and g2node are inconsistent
                    else:
                        edges_removed += 1

                if edges_removed > matching.maximal_edges_removed:
                    continue

                matching.assignments[g1node] = g2node
                matching.edges_removed = edges_removed
                assign(matching)
                matching.edges_removed = starting_edges_removed
            matching.assignments.pop(g1node, None)
        else:
            # recursion has bottomed out
            print(matching)
            if matching.edges_removed < matching.maximal_edges_removed:
                matching.maximal_edges_removed = matching.edges_removed
            # TODO add to match object

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

    mcgregor(blob1, blob2, node_match, edge_match)


if __name__ == "__main__":
    main()
