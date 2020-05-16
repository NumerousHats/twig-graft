import networkx as nx


class PeopleGraph:
    def __init__(self):
        self.graph = nx.DiGraph()
        self.people = {}
        # TODO this should eventually include ability to import saved graph databases from JSON

    def append(self, record):
        self.people = {p.identifier: p for p in record.people()}
        relations = [(rel.from_id, rel.to_id, {"relation": rel}) for rel in record.relations()]
        self.graph.add_nodes_from(self.people.keys())
        self.graph.add_edges_from(relations)

    def summarize(self):
        print("{} nodes, {} edges, {} components".format(self.graph.number_of_nodes(),
                                                         self.graph.number_of_edges(),
                                                         nx.number_strongly_connected_components(self.graph)))