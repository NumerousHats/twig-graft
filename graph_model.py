"""Module defining a graph model for genealogical relationships between people.

The model is a directed graph implemented using the NetworkX package. Although nodes correspond to objects of type
data_model.Person, since Person objects are mutable, the actual NetworkX nodes are the value of Person.identifier,
and the actual Person object is stored in a dict indexed by identifier. Edges have the property "relation" which
contain an object of type data_model.Relationship.
"""


from collections import defaultdict
import json

import networkx as nx

from import_records import Record
from data_model import Person, Relationship


class PeopleGraph:
    def __init__(self, graph_json=None):
        self.graph = nx.DiGraph()
        self.people = {}

        if graph_json:
            relations = []
            for p in graph_json["persons"]:
                person = Person(json_dict=p)
                self.people.update({person.identifier: person})
            for r in graph_json["relations"]:
                relation = Relationship(None, None, None, json_dict=r)
                relations.append((relation.from_id, relation.to_id, {"relation": relation}))

            self.graph.add_nodes_from(self.people.keys())
            self.graph.add_edges_from(relations)

    def json(self):
        graph = {"persons": [x.json() for x in self.people.values()], "relations": []}
        for (u, v, relation) in self.graph.edges.data('relation'):
            graph["relations"].append(relation.json())
        return graph

    def __repr__(self):
        return json.dumps(self.json())

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

    def relation_str(self, pid1, pid2):
        out = [str(self.people[pid1])]

        rel_type = self.graph[pid1][pid2]['relation'].relationship_type
        if rel_type == "parent-child":
            out.append("parent of")
        elif rel_type == "spouse":
            out.append("spouse of")
        else:
            raise ValueError("invalid relationship type")

        out.append(str(self.people[pid2]))
        return "\n".join(out)

