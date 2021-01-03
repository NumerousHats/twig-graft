"""Implements the McGregor algorithm for finding the maximum common subgraph(s) of two input graphs.

A maximum common subgraph of graphs G1 and G2 is the largest subgraph H1 of G1 and the largest subgraph
H2 of G2 such that H1 and H2 are isomorphic. H1 and H2 need not be unique. The McGregor algorithm is a
branch-and-bound search over all possible mappings of the nodes of G1 to the nodes of G2 that terminates
early if the current branch cannot lead to a solution that is as large as the largest subgraph found thus far.
The implementation here retains most of the spirit and methodology of McGregor's paper, but differs from the
pseudocode therein in that it is recursive and makes use of Pythonic idioms.

McGregor's "priority subset" method for choosing the order in which to attempt node pairing is not yet implemented.

Ref: McGregor, James J. Backtrack search algorithms and the maximal common subgraph problem (1982).
Software -- Practice and Experience, vol. 12, 23-34.
http://www.cs.uoi.gr/~pvassil/downloads/GraphDistance/maxCommonSubgraph_McGregor_1982.pdf
"""


import logging
import logging.config
import math
import copy
from collections import defaultdict
import networkx as nx


class NodeMatching:
    """Encapsulates the node matching of two graphs.

    Attributes:
        graph1 (nx.Graph): The input graph with the smaller number of nodes.
        graph2 (nx.Graph): The input graph with the larger number of nodes.
        node_matching (dict or None): The possible nodes of graph2 that can be feasibly matched to each node of graph1
            based on node attributes. The keys are graph1 nodes, and the values are lists of graph2 nodes. If None,
            then it is assumed that every node in graph1 is allowed to be matched to any node in graph2.
        assignments (dict): The current node matching assignments (g1 nodes as keys, g2 nodes as values).
        edges_removed (int): The number of edges in graph1 that have been removed in the current common subgraph
            because the analogous edge in graph2 does not exist.
        maximal_edges_removed (int): The number of edges that needed to be removed in the in the largest common
            subgraph found up to this point. If edges_removed > maximal_edges_removed, then the recursion can be
            terminated. If a larger common subgraph is found, then maximal_edges_removed will decrease.
        maximal_common_subgraphs (list): A list of assignment dicts corresponding to the node matching assignments
            corresponding to the maximal common subgraphs found thus far.
    """
    def __init__(self, graph1, graph2, node_matching=None):
        self.graph1 = graph1
        self.graph2 = graph2

        if node_matching:
            self.node_matching = node_matching
        else:
            self.node_matching = {}
            g1nodes = graph1.nodes
            g2nodes = graph2.nodes
            for node in g1nodes:
                self.node_matching[node] = g2nodes

        self.edges_removed = 0
        self.maximal_edges_removed = math.inf
        self.edges_added = 0
        self.edges_in_maximal_subgraph = 0
        self.assignments = {}
        self.maximal_common_subgraphs = []

    def __str__(self):
        assignments = " ".join(["{};{}".format(k, v) for k, v in self.assignments.items()])
        return "{} maximal common subgraphs with {} edges ({} edges removed)".format(
            len(self.maximal_common_subgraphs), self.edges_in_maximal_subgraph, self.maximal_edges_removed)

    def g1nodes(self):
        """Return all nodes in g1"""
        return self.node_matching.keys()

    def g2nodes(self, g1node):
        """Return all nodes in g2 that are compatible with g1node"""
        return self.node_matching[g1node]

    def add_as_maximal(self):
        """Add the current set of assignments as a maximal common subgraph.

        If the current induced common subgraph is larger than the one(s) previously found, then
        clear the maximal subgraph list prior to adding."""

        logger = logging.getLogger(__name__)
        if self.edges_added == self.edges_in_maximal_subgraph:
            logger.debug("found another common subgraph of the same size: %s", str(self))
            self.maximal_common_subgraphs.append(copy.deepcopy(self.assignments))
        elif self.edges_added > self.edges_in_maximal_subgraph:
            logger.info("found new common subgraph with more edges: %s", str(self))
            self.maximal_common_subgraphs.clear()
            self.maximal_common_subgraphs.append(copy.deepcopy(self.assignments))
            self.edges_in_maximal_subgraph = self.edges_added

        if self.edges_removed < self.maximal_edges_removed:
            logger.info("found new bound on removed edges: %s", str(self))
            self.maximal_edges_removed = self.edges_removed


def node_match(g1, g2, node1, node2):
    # logger = logging.getLogger(__name__)
    # logger.debug("nodes are %s and %s", g1.nodes[node1]["stuff"], g2.nodes[node2]["stuff"])
    return g1.nodes[node1]["stuff"] == g2.nodes[node2]["stuff"]
    # return True


def edge_match(g1, g2, n1_in_g1, n2_in_g1, n1_in_g2, n2_in_g2):
    return g1.edges[n1_in_g1, n2_in_g1]["type"] == g2.edges[n1_in_g2, n2_in_g2]["type"]


def mcgregor(graph1, graph2, node_comparison=None, edge_comparison=None):
    """Implements a recursive version of the McGregor algorithm for finding the maximal common node-induced
    subgraph of two input graphs subject to constraints on node and edge attributes.

     Args:
         graph1 (nx.Graph): The first input graph.
         graph2 (nx.Graph): The second input graph.
         node_comparison: A function that returns True if two nodes have compatible attributes. The function should
            have 4 arguments, namely, graph1, graph2, a node in graph1, and a node in graph2.
         edge_comparison: A function that returns True if two edges have compatible attributes. The function should
            have 6 arguments, namely, graph1, graph2, nodes 1 and 2 that define the edge in graph1, and nodes 1
            and 2 that define the edge in graph2.

     Returns:
         A NodeMatching object that contains the maximal common subgraph(s) and
         associated node matching(s).
    """

    def graph_matcher(matching):
        """The recursive function that performs a depth-first branch-and-bound search of the node
        matching solution space.

         Args:
             matching (NodeMatching): The current state of the node matching.
        """

        logger = logging.getLogger(__name__)
        logger.debug("Entering assign() with %s", matching)

        starting_edges_removed = matching.edges_removed
        starting_edges_added = matching.edges_added
        g1todo = [x for x in matching.g1nodes() if x not in matching.assignments.keys()]
        if g1todo:
            g1node = g1todo[0]
            logger.debug('Attempting to add node %s in graph1', g1node)
            g1_possible_edges = edges_to_subgraph(matching, g1node)

            for g2node in [x for x in matching.g2nodes(g1node) if x not in list(matching.assignments.values())]:
                logger.debug('Attempting to match %s in graph1 with %s in graph2', g1node, g2node)

                edges_removed = starting_edges_removed
                edges_added = starting_edges_added
                for n1, n2 in g1_possible_edges:
                    n1_2 = matching.assignments.get(n1, g2node)
                    n2_2 = matching.assignments.get(n2, g2node)
                    logger.debug('Comparing %s %s pair to %s %s', n1, n2, n1_2, n2_2)
                    compatible_edge = False
                    if graph2.has_edge(n1_2, n2_2):
                        logger.debug("Both graphs have an edge")
                        if edge_comparison:
                            if edge_comparison(graph1, graph2, n1, n2, n1_2, n2_2):
                                compatible_edge = True
                            else:
                                logger.debug("Edges are incompatible")
                        else:
                            compatible_edge = True
                    else:
                        logger.debug("No corresponding edge in graph 2")

                    if compatible_edge:
                        edges_added += 1
                    else:
                        edges_removed += 1
                        logger.debug("No compatible edge, edges_removed = %s", edges_removed)

                if edges_removed > matching.maximal_edges_removed:
                    logger.debug("Too many removed edges")
                    continue

                matching.assignments[g1node] = g2node
                matching.edges_removed = edges_removed
                matching.edges_added = edges_added
                graph_matcher(matching)
                matching.edges_removed = starting_edges_removed
                matching.edges_added = starting_edges_added
                matching.assignments.pop(g1node, None)
        else:
            logger.debug("Recursion bottomed out")
            if matching.edges_removed <= matching.maximal_edges_removed \
                    or matching.edges_added >= matching.edges_in_maximal_subgraph:
                logger.debug("Found a possible new maximal subgraph")
                matching.add_as_maximal()

    def edges_to_subgraph_undirected(matching, new_node):
        """Returns all edges from a node to the currently matched subgraph of g1
        if g1 is undirected."""
        g1_subgraph_nodes = matching.assignments.keys()
        return [(n1, n2) for (n1, n2) in matching.graph1.edges(new_node)
                if n1 in g1_subgraph_nodes or n2 in g1_subgraph_nodes]

    def edges_to_subgraph_directed(matching, new_node):
        """Returns all edges from a node to the currently matched subgraph of g1
        if g1 is directed."""
        raise NotImplementedError

    logger = logging.getLogger(__name__)

    if graph1.is_multigraph() or graph2.is_multigraph():
        raise TypeError

    if graph1.is_directed() and graph2.is_directed():
        edges_to_subgraph = edges_to_subgraph_directed
    elif not graph1.is_directed() and not graph2.is_directed():
        edges_to_subgraph = edges_to_subgraph_undirected
    else:
        raise TypeError

    if graph1.number_of_nodes() < graph2.number_of_nodes():
        small = graph1
        big = graph2
    else:
        small = graph2
        big = graph1

    if node_comparison:
        node_matches = defaultdict(list)
        for s_node in small.nodes:
            for b_node in big.nodes:
                if node_comparison(small, big, s_node, b_node):
                    node_matches[s_node].append(b_node)
    else:
        node_matches = None

    mcs = NodeMatching(small, big, node_matches)
    graph_matcher(mcs)

    logger.info("found %s maximal common subgraphs with %s nodes and %s edges",
                len(mcs.maximal_common_subgraphs), len(mcs.maximal_common_subgraphs[0].keys()),
                mcs.edges_in_maximal_subgraph)

    return mcs


def main():
    logging.basicConfig(format='%(asctime)s %(name)-12s %(levelname)-8s %(message)s', level=logging.INFO)

    blob1 = nx.Graph()
    blob1.add_edge("A", "B", type="straight")
    blob1.add_edge("A", "C", type="wavy")
    blob1.add_edge("C", "B", type="straight")
    blob1.add_edge("C", "D", type="wavy")
    blob1.add_edge("D", "E", type="straight")

    blob2 = nx.Graph()
    blob2.add_edge("a", "c", type="straight")
    blob2.add_edge("b", "c", type="wavy")
    blob2.add_edge("c", "d", type="wavy")
    blob2.add_edge("d", "g", type="straight")
    blob2.add_edge("d", "e", type="straight")
    blob2.add_edge("e", "f", type="straight")
    blob2.add_edge("f", "g", type="straight")

    # blob1 = nx.read_gml("blob1lab.gml")
    # blob2 = nx.read_gml("blob2lab.gml")
    # blob1 = blob1.to_undirected()
    # blob2 = blob2.to_undirected()

    # mcgregor(blob1, blob2, node_match)
    output = mcgregor(blob1, blob2, edge_comparison=edge_match)
    print(output)
    print(output.maximal_common_subgraphs)


if __name__ == "__main__":
    main()
