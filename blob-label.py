import string
import random
import networkx as nx
from networkx.algorithms import isomorphism


def main():
    alphabet = list(string.ascii_uppercase)[0:15]
    edge_type = ['child', 'spouse']

    thing = nx.read_gml("blob2.gml")
    for key in thing.nodes.keys():
        thing.nodes[key]['stuff'] = random.choice(alphabet)

    for edge in thing.edges:
        thing[edge[0]][edge[1]]['type'] = random.choice(edge_type)

    nx.write_gml(thing, "blob2lab.gml")


if __name__ == "__main__":
    main()
