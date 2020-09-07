import itertools
import networkx as nx
from comparison import compare_person


def locations_in_component(people):
    """Return set of all distinct Locations associated with all Persons in a list."""
    loc_lists = [person.get_locations() for person in people]
    locations = [item for sublist in loc_lists for item in sublist]
    return set(locations)


def loclist_str(loclist):
    if loclist:
        return ", ".join([str(x) for x in loclist])
    else:
        return ""


def compare_all_components(people_graph):
    components = list(nx.weakly_connected_components(people_graph.graph))
    for comp1nodes, comp2nodes in itertools.combinations(components, 2):
        comp1 = people_graph.graph.subgraph(comp1nodes)
        comp2 = people_graph.graph.subgraph(comp2nodes)

        comp1locations = locations_in_component([people_graph.people[node] for node in comp1nodes])
        comp2locations = locations_in_component([people_graph.people[node] for node in comp2nodes])
        location_overlap = comp1locations.intersection(comp2locations)

        has_name_match = False
        for pid1 in comp1nodes:
            for pid2 in comp2nodes:
                p1 = people_graph.people[pid1]
                p2 = people_graph.people[pid2]
                name_matches, date_matches, house_matches = compare_person(p1, p2, people_graph)
                if name_matches > 0:
                    has_name_match = True

        if has_name_match and location_overlap:
            print("\n###############################\n")

            if len(comp1nodes) > 1:
                for pid1, pid2 in comp1.edges:
                    print(people_graph.relation_str(pid1, pid2) + "\n")
            else:
                for pid in comp1nodes:
                    print(people_graph.people[pid])

            print("\n-----\n")

            if len(comp2nodes) > 1:
                for pid1, pid2 in comp2.edges:
                    print(people_graph.relation_str(pid1, pid2) + "\n")
            else:
                for pid in comp2nodes:
                    print(people_graph.people[pid])
