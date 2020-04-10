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

            row["age_y"] = 0 if row["age_y"] is None else int(row["age_y"])
            row["age_m"] = 0 if row["age_m"] is None else int(row["age_m"])
            row["age_w"] = 0 if row["age_w"] is None else int(row["age_w"])
            row["age_d"] = 0 if row["age_d"] is None else int(row["age_d"])

            surname = row["surname"]
            slash_pos = surname.find("/")
            if slash_pos != -1:
                surname = surname[0:slash_pos]

            age = Duration(duration_list=[row["age_y"], row["age_m"], row["age_w"], row["age_d"]],
                           year_day_ambiguity=True if row["year_day"] else False)

            location = Location(house_number=row["house_number"],
                                alt_house_number=row["alt_house_number"],
                                alt_village=row["house_location"])

            source = Source(repository=row["repository"], volume=row["book"], page_number=row["page"],
                            entry_number=row["entry"], image_file=row["image"])

            decedent = Person(gender=row["gender"], sources=source)

            if row["gender"] == "m":
                decedent.add_name(Name(name_type="birth",
                                       name_parts={"given": row["given_name"], "surname": surname}))
            else:
                if row["coelebs"] is not None and row["gender"] == "f":
                    decedent.add_name(Name(name_type="birth",
                                           name_parts={"given": row["given_name"], "surname": surname}))
                else:
                    if row["maiden_name"]:
                        decedent.add_name(Name(name_type="birth",
                                               name_parts={"given": row["given_name"],
                                                           "surname": row['maiden_name']}))
                    if row["spouse"] or row["uxoratus"]:
                        decedent.add_name(Name(name_type="married",
                                               name_parts={"given": row["given_name"], "surname": surname}))
                    elif age.duration < datetime.timedelta(days=13) or \
                            (age.duration < datetime.timedelta(days=365*13) and not age.year_day_ambiguity):
                        # we'll assume 12-year-old and younger girls were not getting married...
                        decedent.add_name(Name(name_type="birth",
                                               name_parts={"given": row["given_name"], "surname": surname}))
                    else:
                        decedent.add_name(Name(name_type="unknown",
                                               name_parts={"given": row["given_name"], "surname": surname}))

            if row["coelebs"]:
                decedent.add_fact(Fact(fact_type="NumberOfMarriages", content=0))

            if row["uxoratus"]:
                decedent.add_fact(Fact(fact_type="NumberOfMarriages", content=">0"))

            if row["death_date"] is not None:
                decedent.add_fact(Fact(fact_type="Death", date=Date(row["death_date"]),
                                       age=age, locations=location, sources=source))

            if row["burial_date"] is not None:
                decedent.add_fact(Fact(fact_type="Burial", date=Date(row["burial_date"]),
                                       age=age, locations=location, sources=source))

            print('"decedent": ' + repr(decedent))

            if row["father"]:
                if row["father"] == "[illegitimate]":
                    decedent.add_fact(Fact(fact_type="IllegitimateBirth", sources=source))
                else:
                    father = Person(gender="m",
                                    names=Name(name_type="birth", name_parts={"given": row["father"],
                                                                              "surname": surname}),
                                    sources=source)
                    father_rel = Relationship(father.identifier, decedent.identifier, "parent-child", sources=source)

                    if row["father_deceased"]:
                        father.add_fact(Fact(fact_type="Death", date=Date("", row["death_date"])))

            if row["mother"]:
                mother = Person(gender="f",
                                names=Name(name_type="married", name_parts={"given": row["mother"],
                                                                            "surname": surname}),
                                sources=source)
                mother_rel = Relationship(mother.identifier, decedent.identifier, "parent-child", sources=source)

                if row["mother_deceased"]:
                    mother.add_fact(Fact(fact_type="Death", date=Date("", row["death_date"])))

            if row["spouse"]:
                if decedent.gender == "m":
                    # TODO need to determine if surname is married or maiden by comparing to decedent's surname?
                    spouse = Person(gender="f", names=Name())
                else:
                    spouse = Person(gender="m", names=Name())
