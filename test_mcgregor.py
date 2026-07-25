import networkx as nx
from mcgregor import mcgregor


def node_match_shape(g1, g2, n1, n2):
    return g1.nodes[n1]["shape"] == g2.nodes[n2]["shape"]


def edge_match_type(g1, g2, n1g1, n2g1, n1g2, n2g2):
    return g1.edges[n1g1, n2g1]["type"] == g2.edges[n1g2, n2g2]["type"]


class TestMcGregorIdentical:
    def test_identical_directed(self):
        g1 = nx.DiGraph()
        g1.add_edge("A", "B", type="parent-child")
        g1.nodes["A"]["shape"] = "round"
        g1.nodes["B"]["shape"] = "square"

        g2 = nx.DiGraph()
        g2.add_edge("a", "b", type="parent-child")
        g2.nodes["a"]["shape"] = "round"
        g2.nodes["b"]["shape"] = "square"

        result = mcgregor(g1, g2, node_comparison=node_match_shape, edge_comparison=edge_match_type)
        assert len(result.maximal_common_subgraphs) >= 1
        match = result.maximal_common_subgraphs[0]
        assert len(match) == 2

    def test_identical_undirected(self):
        g1 = nx.Graph()
        g1.add_edge("A", "B")
        g1.add_edge("B", "C")
        g1.nodes["A"]["label"] = "x"
        g1.nodes["B"]["label"] = "y"
        g1.nodes["C"]["label"] = "z"

        g2 = nx.Graph()
        g2.add_edge("a", "b")
        g2.add_edge("b", "c")
        g2.nodes["a"]["label"] = "x"
        g2.nodes["b"]["label"] = "y"
        g2.nodes["c"]["label"] = "z"

        result = mcgregor(g1, g2,
                          node_comparison=lambda g1, g2, n1, n2: g1.nodes[n1]["label"] == g2.nodes[n2]["label"])
        assert len(result.maximal_common_subgraphs) >= 1
        match = result.maximal_common_subgraphs[0]
        assert len(match) == 3


class TestMcGregorSubset:
    def test_g2_contains_g1(self):
        g1 = nx.DiGraph()
        g1.add_edge("A", "B", type="pc")
        g1.nodes["A"]["val"] = 1
        g1.nodes["B"]["val"] = 2

        g2 = nx.DiGraph()
        g2.add_edge("a", "b", type="pc")
        g2.add_edge("b", "c", type="pc")
        g2.add_edge("a", "c", type="pc")
        g2.nodes["a"]["val"] = 1
        g2.nodes["b"]["val"] = 2
        g2.nodes["c"]["val"] = 3

        result = mcgregor(g1, g2,
                          node_comparison=lambda g1, g2, n1, n2: g1.nodes[n1]["val"] == g2.nodes[n2]["val"])
        assert len(result.maximal_common_subgraphs) >= 1
        match = result.maximal_common_subgraphs[0]
        assert len(match) == 2


class TestMcGregorNoMatch:
    def test_no_common_subgraph(self):
        g1 = nx.DiGraph()
        g1.add_edge("A", "B")
        g1.nodes["A"]["shape"] = "round"
        g1.nodes["B"]["shape"] = "round"

        g2 = nx.DiGraph()
        g2.add_edge("a", "b")
        g2.nodes["a"]["shape"] = "square"
        g2.nodes["b"]["shape"] = "square"

        result = mcgregor(g1, g2, node_comparison=node_match_shape)
        assert len(result.maximal_common_subgraphs) == 0


class TestMcGregorNodeFilter:
    def test_node_filter_reduces_match(self):
        g1 = nx.DiGraph()
        g1.add_edge("A", "B")
        g1.nodes["A"]["color"] = "red"
        g1.nodes["B"]["color"] = "blue"

        g2 = nx.DiGraph()
        g2.add_edge("a", "b")
        g2.add_edge("b", "c")
        g2.nodes["a"]["color"] = "red"
        g2.nodes["b"]["color"] = "blue"
        g2.nodes["c"]["color"] = "red"

        # A→B (red→blue) matches a→b (red→blue)
        result = mcgregor(g1, g2,
                          node_comparison=lambda g1, g2, n1, n2: g1.nodes[n1]["color"] == g2.nodes[n2]["color"])
        assert len(result.maximal_common_subgraphs) >= 1
        match = result.maximal_common_subgraphs[0]
        # g1 has 2 nodes, so max match size is 2
        assert len(match) == 2


class TestMcGregorEdgeFilter:
    def test_edge_type_mismatch(self):
        g1 = nx.DiGraph()
        g1.add_edge("A", "B", rel="parent-child")

        g2 = nx.DiGraph()
        g2.add_edge("a", "b", rel="spouse")

        result = mcgregor(g1, g2,
                          edge_comparison=lambda g1, g2, n1a, n2a, n1b, n2b:
                          g1.edges[n1a, n2a]["rel"] == g2.edges[n1b, n2b]["rel"])
        # McGregor finds node mappings, but with 0 edges matched (1 edge removed)
        # Both A→a,B→b and A→b,B→a are valid (no compatible edges)
        assert len(result.maximal_common_subgraphs) >= 1
        assert result.edges_in_maximal_subgraph == 0


class TestMcGregorSize:
    def test_graph1_must_be_smaller(self):
        g1 = nx.DiGraph()
        g1.add_node("A")
        g1.add_node("B")
        g1.add_node("C")

        g2 = nx.DiGraph()
        g2.add_node("a")

        import pytest
        with pytest.raises(ValueError):
            mcgregor(g1, g2)


class TestMcGregorMultiple:
    def test_multiple_maximal_subgraphs(self):
        # Two separate edges in g1 that could each match different edges in g2
        g1 = nx.Graph()
        g1.add_edge("A", "B")
        g1.nodes["A"]["val"] = 1
        g1.nodes["B"]["val"] = 2

        g2 = nx.Graph()
        g2.add_edge("a", "b")
        g2.add_edge("c", "d")
        g2.nodes["a"]["val"] = 1
        g2.nodes["b"]["val"] = 2
        g2.nodes["c"]["val"] = 1
        g2.nodes["d"]["val"] = 2

        result = mcgregor(g1, g2,
                          node_comparison=lambda g1, g2, n1, n2: g1.nodes[n1]["val"] == g2.nodes[n2]["val"])
        # A-B (1-2) matches both a-b and c-d
        assert len(result.maximal_common_subgraphs) == 2
