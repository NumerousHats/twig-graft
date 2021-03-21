import logging
import logging.config
import csv
import json

import import_records
import graph_model


def main():
    logging.basicConfig(format='%(asctime)s %(name)-12s %(levelname)-8s %(message)s', level=logging.INFO)

    thesaurus = {}
    with open('standardized_surnames.csv') as csv_file:
        reader = csv.DictReader(csv_file, delimiter=',', quotechar='"')
        for row in reader:
            thesaurus[row["raw"]] = row["standardized"]

    with open('standardized_given.csv') as csv_file:
        reader = csv.DictReader(csv_file, delimiter=',', quotechar='"')
        for row in reader:
            thesaurus[row["raw"]] = row["standardized"]

    the_graph = graph_model.PeopleGraph()
    import_records.import_births('test.csv', the_graph, thesaurus)
    with open('dum.json', 'w') as json_file:
        json.dump(the_graph.json(), json_file, indent=2)


if __name__ == "__main__":
    main()
