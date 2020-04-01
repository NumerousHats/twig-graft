import logging
import csv

from data_model import *


def import_deaths(filename):
    logger = logging.getLogger("twig_graft")
    logger.debug("importing {}".format(filename))

    with open(filename) as csv_file:
        reader = csv.DictReader(csv_file, delimiter=',', quotechar='"')
        for row in reader:
            row = {k: str(v or None) for k, v in row.items()}  # change empty strings to None
            source = Source(repository=row["repository"], volume=row["book"], page_number=row["page"],
                            entry_number=row["entry"], image_file=row["image"])

            surname = row["surname"]
            slash_pos = surname.find("/")
            if slash_pos != -1:
                surname = surname[0:slash_pos]

            person = Person(names=Name(name_type="birth",
                                       name_parts={"given": row["given_name"], "surname": surname}),
                            gender=row["gender"],
                            # facts=Fact(fact_type="Death",
                            #            date=Date(row["death_date"])),
                            sources=source)
