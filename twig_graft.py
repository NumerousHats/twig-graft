import logging
import logging.config
import csv
import json

import import_records
import graph_model
import random
import comparison
from graph_match import *


def main():
    logging.basicConfig(format='%(asctime)s %(name)-12s %(levelname)-8s %(message)s', level=logging.WARNING)

    # thesaurus = {}
    # with open('standardized_surnames.csv') as csv_file:
    #     reader = csv.DictReader(csv_file, delimiter=',', quotechar='"')
    #     for row in reader:
    #         thesaurus[row["raw"]] = row["standardized"]
    #
    # with open('standardized_given.csv') as csv_file:
    #     reader = csv.DictReader(csv_file, delimiter=',', quotechar='"')
    #     for row in reader:
    #         thesaurus[row["raw"]] = row["standardized"]
    #
    # the_graph = graph_model.PeopleGraph()
    # import_records.import_deaths('test.csv', the_graph, thesaurus)
    # with open('dum.json', 'w') as json_file:
    #     json.dump(the_graph.json(), json_file, indent=2)

    with open('dum.json') as f:
        input_json = json.load(f)

    the_graph = graph_model.PeopleGraph(graph_json=input_json)
    match_components_in_location(the_graph)


if __name__ == "__main__":
    main()
