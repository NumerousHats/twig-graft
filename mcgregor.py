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
        assignments (dict): The current node matching (g1 nodes as keys, g2 nodes as values).
        maximal_edges_removed (int): The number of edges that needed to be removed in the in the
            largest common subgraph found up to this point. If edges_removed > maximal_edges_removed,
            then the recursion can be terminated. If a larger common subgraph is found, then
            maximal_edges_removed will decrease.
    """
    def __init__(self, graph1, graph2):
        self.graph1 = graph1
        self.graph2 = graph2

        self.edges_removed = 0
        self.maximal_edges_removed = math.inf
        self.assignments = {}

        self.g1nodes = graph1.nodes
        self.g2nodes = graph2.nodes

    def __str__(self):
        assignments = " ".join(["{};{}".format(k, v) for k, v in self.assignments.items()])
        return "[{}] with {} edges removed".format(assignments, self.edges_removed)


def node_match(g1, g2, node1, node2):
    # logger = logging.getLogger(__name__)
    # logger.debug("nodes are %s and %s", g1.nodes[node1]["stuff"], g2.nodes[node2]["stuff"])
    return g1.nodes[node1]["stuff"] == g2.nodes[node2]["stuff"]
    # return True


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

        logger = logging.getLogger(__name__)
        logger.debug("Entering assign() with %s", matching)

        starting_edges_removed = matching.edges_removed
        g1todo = [x for x in matching.g1nodes if x not in matching.assignments.keys()]
        if g1todo:
            g1node = g1todo[0]
            logger.debug('Attempting to add node %s in graph1', g1node)
            g1_possible_edges = [(n1, n2) for (n1, n2) in graph1.edges(g1node)
                                 if n2 in matching.assignments.keys()]
            # n1 will always be g1node

            for g2node in [x for x in matching.g2nodes if x not in list(matching.assignments.values())]:
                logger.debug('Attempting to match %s in graph1 with %s in graph2', g1node, g2node)
                if not node_comparison(matching.graph1, matching.graph2, g1node, g2node):
                    logger.debug("Nodes incompatible")
                    continue

                edges_removed = starting_edges_removed
                for n1, n2 in g1_possible_edges:
                    n1_2 = matching.assignments.get(n1, g2node)
                    n2_2 = matching.assignments.get(n2, g2node)
                    logger.debug('Comparing %s %s pair to %s %s', n1, n2, n1_2, n2_2)
                    if graph2.has_edge(n1_2, n2_2):
                        logger.debug("Both graphs have an edge")
                        # TODO determine if any edges involving g1node and g2node are inconsistent
                    else:
                        # TODO this is actually a problem for sparse graphs, since the "removed edge" approach
                        #   treats a node pair with an edge in both graphs and a node pair with no edges
                        #   in either graph as equivalent. However, the former should be favored since it
                        #   leads to the "larger" graph. 
                        edges_removed += 1
                        logger.debug("Missing edge, edges_removed = %s", edges_removed)

                if edges_removed > matching.maximal_edges_removed:
                    logger.debug("Too many removed edges")
                    continue

                matching.assignments[g1node] = g2node
                matching.edges_removed = edges_removed
                assign(matching)
                matching.edges_removed = starting_edges_removed
                matching.assignments.pop(g1node, None)
        else:
            logger.debug("Recursion bottomed out")
            logger.info("%s", matching)
            if matching.edges_removed < matching.maximal_edges_removed:
                logger.debug("Found better bound of %s, was %s", matching.edges_removed,
                             matching.maximal_edges_removed)
                matching.maximal_edges_removed = matching.edges_removed
            # TODO add to match object

    if graph1.number_of_nodes() < graph2.number_of_nodes():
        small = graph1
        big = graph2
    else:
        small = graph2
        big = graph1

    mcs = NodeMatching(small, big)
    assign(mcs)


def main():
    logging.basicConfig(format='%(asctime)s %(name)-12s %(levelname)-8s %(message)s', level=logging.INFO)

    # blob1 = nx.Graph()
    # blob1.add_edge("A", "B")
    # blob1.add_edge("A", "C")
    # blob1.add_edge("C", "B")
    # blob1.add_edge("C", "D")
    # blob1.add_edge("D", "E")
    #
    # blob2 = nx.Graph()
    # blob2.add_edge("a", "c")
    # blob2.add_edge("b", "c")
    # blob2.add_edge("c", "d")
    # blob2.add_edge("d", "g")
    # blob2.add_edge("d", "e")
    # blob2.add_edge("e", "f")
    # blob2.add_edge("f", "g")

    blob1 = nx.read_gml("blob1lab.gml")
    blob2 = nx.read_gml("blob2lab.gml")
    blob1 = blob1.to_undirected()
    blob2 = blob2.to_undirected()

    # print(nx.number_of_nodes(blob1))
    # print(nx.number_of_nodes(blob2))

    mcgregor(blob1, blob2, node_match, edge_match)


if __name__ == "__main__":
    main()
