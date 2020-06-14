import networkx as nx
import itertools
from collections import defaultdict
from import_records import Record
from comparison import compare_person


class PeopleGraph:
    def __init__(self):
        self.graph = nx.DiGraph()
        self.people = {}
        # TODO this should eventually include ability to import saved graph databases from JSON

    def __repr__(self):
        # TODO this should create a JSON serialization of the entire graph
        pass

    def append(self, record: Record):
        self.people.update({p.identifier: p for p in record.people()})
        relations = [(rel.from_id, rel.to_id, {"relation": rel}) for rel in record.relations()]
        self.graph.add_nodes_from(self.people.keys())
        self.graph.add_edges_from(relations)

    def summarize(self):
        print("{} nodes, {} edges, {} components".format(self.graph.number_of_nodes(),
                                                         self.graph.number_of_edges(),
                                                         nx.number_weakly_connected_components(self.graph)))

    def direct_relations(self, pid):
        relations = defaultdict(list)
        for edge in self.graph.in_edges(pid):
            relation = self.graph.get_edge_data(edge[0], edge[1])["relation"]
            if relation.relationship_type == "parent-child":
                relations["parents"].append(edge[0])
            if relation.relationship_type == "spouse":
                relations["spouses"].append(edge[0])

        for edge in self.graph.out_edges(pid):
            relation = self.graph.get_edge_data(edge[0], edge[1])["relation"]
            if relation.relationship_type == "parent-child":
                relations["children"].append(edge[1])
            if relation.relationship_type == "spouse":
                relations["spouses"].append(edge[1])

        return relations

    def all_vs_all(self):
        for pid1, pid2 in itertools.combinations(self.people, 2):
            p1 = self.people[pid1]
            p2 = self.people[pid2]
            matches, comparisons = compare_person(p1, p2, self)
            if matches > 0:
                print("possible match:\n\t{}\n\t{}\n{} matches in {} comparisons".format(p1, p2, matches, comparisons))
