import logging
import logging.config
import csv

import import_records
import graph_model


def main():
    logging.basicConfig(format='%(asctime)s %(name)-12s %(levelname)-8s %(message)s', level=logging.DEBUG)

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
    import_records.import_deaths('test.csv', the_graph, thesaurus)
    the_graph.summarize()


if __name__ == "__main__":
    main()
