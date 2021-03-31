import logging
import logging.config
import json

import click

import graph_model
from graph_match import *


@click.command()
@click.argument('infile')
@click.option('--no-merged', is_flag=True)
def cli(infile, no_merged):
    logging.basicConfig(format='%(asctime)s %(name)-12s %(levelname)-8s %(message)s', level=logging.WARNING)
    outfile = infile.replace(".json", ".gml")

    with open(infile) as f:
        input_json = json.load(f)

    people_graph = graph_model.PeopleGraph(graph_json=input_json)
    the_graph = people_graph.graph
    if no_merged:
        the_graph.remove_nodes_from([n for n in the_graph if the_graph.nodes[n]['person'].merged])

    for (n, d) in the_graph.nodes(data=True):
        d["person"] = str(d["person"])
    for (u, v, d) in the_graph.edges(data=True):
        d["relation"] = d["relation"].relationship_type

    nx.write_gml(the_graph, outfile)


if __name__ == "__main__":
    cli()
