import logging
import csv

from data_model import *


def import_deaths(filename):
    logger = logging.getLogger("twig_graft")
    logger.debug("importing {}".format(filename))

    with open(filename) as csv_file:
        reader = csv.DictReader(csv_file, delimiter=',', quotechar='"')
        for row in reader:
            def c(i): return i or None
            row = {k: c(v) for k, v in row.items()}  # change empty strings to None

            row["age_y"] = 0 if row["age_y"] is None else row["age_y"]
            row["age_m"] = 0 if row["age_m"] is None else row["age_m"]
            row["age_w"] = 0 if row["age_w"] is None else row["age_w"]
            row["age_d"] = 0 if row["age_d"] is None else row["age_d"]

            surname = row["surname"]
            slash_pos = surname.find("/")
            if slash_pos != -1:
                surname = surname[0:slash_pos]

            age = Duration(duration_list=[int(x) for x in
                                          [row["age_y"], row["age_m"], row["age_w"], row["age_d"]]],
                           year_day_ambiguity=True if row["year_day"] else False)

            location = Location(house_number=row["house_number"],
                                alt_house_number=row["alt_house_number"],
                                alt_village=row["house_location"])

            source = Source(repository=row["repository"], volume=row["book"], page_number=row["page"],
                            entry_number=row["entry"], image_file=row["image"])

            decedent = Person(gender=row["gender"], sources=source)

            # for testing only. in production, need to check if the decedent was married or not
            decedent.add_name(Name(name_type="birth",
                                   name_parts={"given": row["given_name"], "surname": surname}))

            if row["death_date"] is not None:
                decedent.add_fact(Fact(fact_type="Death", date=Date(row["death_date"]),
                                       age=age, locations=location, sources=source))

            if row["burial_date"] is not None:
                decedent.add_fact(Fact(fact_type="Burial", date=Date(row["burial_date"]),
                                       age=age, locations=location, sources=source))

            print(decedent)
