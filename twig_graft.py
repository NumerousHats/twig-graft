import logging
import logging.config
import csv

import import_deaths


def main():
    logging_config = dict(
        version=1,
        formatters={
            'f': {'format': '%(asctime)s %(name)-12s %(levelname)-8s %(message)s'}
        },
        handlers={
            'h': {'class': 'logging.StreamHandler',
                  'formatter': 'f',
                  'level': logging.DEBUG}
        },
        root={
            'handlers': ['h'],
            'level': logging.DEBUG,
        },
    )
    logging.config.dictConfig(logging_config)
    logger = logging.getLogger("twig_graft")

    thesaurus = {}
    with open('standardized_surnames.csv') as csv_file:
        reader = csv.DictReader(csv_file, delimiter=',', quotechar='"')
        for row in reader:
            thesaurus[row["raw"]] = row["standardized"]

    with open('standardized_given.csv') as csv_file:
        reader = csv.DictReader(csv_file, delimiter=',', quotechar='"')
        for row in reader:
            thesaurus[row["raw"]] = row["standardized"]

    import_deaths.import_deaths('test.csv', thesaurus)


if __name__ == "__main__":
    main()
