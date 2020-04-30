import logging
import csv
import re
import calendar

from data_model import *


class ParseError(Exception):
    pass


def parse_name(name_string):
    main_name = None
    sub_name = None

    match = re.match(r'(\S+)(?:\s+\((\S+)\))?', name_string)
    if match:
        matches = match.groups()
        if len(matches) == 1:
            main_name = matches[0]
            sub_name = None
        else:
            main_name = matches[0]
            sub_name = matches[1]
    else:
        raise ParseError("couldn't parse name {}".format(name_string))

    return main_name, sub_name

def parse_date(date_string, year):
    match = re.search(r'\d{4}-(\d{2})-(.{2,3})', date_string)
    if match:
        full_date = date_string
    else:
        full_date = "{}-{}".format(year, date_string)
        match = re.search(r'\d{4}-(\d{2})-(.{2,3})', full_date)
        if not match:
            raise ParseError

    if match[2] != "[?]":
        date = Date(full_date)
    else:
        start = full_date.replace("[?]", "01")
        end = full_date.replace("[?]", str(calendar.monthrange(int(year), int(match[1]))[1]))
        date = Date(start, end)

    return date

def import_deaths(filename, thesaurus):
    logger = logging.getLogger("twig_graft")
    logger.debug("importing {}".format(filename))

    with open(filename) as csv_file:
        reader = csv.DictReader(csv_file, delimiter=',', quotechar='"')
        for row in reader:
            if row["surname"]:
                surname = row["surname"]
            else:
                # if there is no surname, assume it's an empty or nonstandard record
                continue

            print(row)

            # pull out notes and low confidence indicators
            notes = {}
            confidence = {}
            for key, value in row.items():
                if value:
                    match = re.search(r'<(.+)>', value)
                    if match:
                        notes[key] = match[1]
                        row[key] = value.replace(match[0], "").strip()

                    match = re.search(r'\?$', value)
                    if match:
                        confidence[key] = "low"
                        row[key] = value.rstrip(" ?")

            # TODO and now we need to do something with them...

            # change empty strings to None
            def c(i): return i or None
            row = {k: c(v) for k, v in row.items()}

            row["age_y"] = 0 if row["age_y"] is None else int(row["age_y"])
            row["age_m"] = 0 if row["age_m"] is None else int(row["age_m"])
            row["age_w"] = 0 if row["age_w"] is None else int(row["age_w"])
            row["age_d"] = 0 if row["age_d"] is None else int(row["age_d"])

            # this_note = [v for k, v in notes.items() if k in ["age_y", "age_m", "age_w", "age_d"]]
            # Durations don't have notes (yet)

            age = Duration(duration_list=[row["age_y"], row["age_m"], row["age_w"], row["age_d"]],
                           year_day_ambiguity=True if row["year_day"] else False)
            if [v for k, v in confidence.items() if k in ["age_y", "age_m", "age_w", "age_d"]]:
                age.confidence = "low"

            location = Location(house_number=row["house_number"],
                                alt_house_number=row["alt_house_number"],
                                alt_village=row["house_location"])

            source = Source(repository=row["repository"], volume=row["book"], page_number=row["page"],
                            entry_number=row["entry"], image_file=row["image"])

            decedent = Person(gender=row["gender"], sources=source)

            recorded_name = None
            aka_name = None
            if row["surname"]:
                surname, house_name = parse_name(row["surname"])
                recorded_name = {"surname": surname}
                if house_name:
                    recorded_name["house_name"] = house_name

            if row["given_name"]:
                given, aka = parse_name(row["given_name"])
                if aka:
                    aka_name = recorded_name.copy()
                    aka_name["given"] = aka

                if given == "[stillbirth]":
                    decedent.add_fact(Fact(fact_type="Stillbirth", sources=source))
                else:
                    recorded_name["given"] = given

            if row["gender"] == "m":
                if recorded_name:
                    decedent.add_name(Name(name_type="birth", name_parts=recorded_name, thesaurus=thesaurus))
                if aka_name:
                    decedent.add_name(Name(name_type="also_known_as", name_parts=aka_name, thesaurus=thesaurus))
            else:
                if row["coelebs"] is not None and row["gender"] == "f":
                    if recorded_name:
                        decedent.add_name(Name(name_type="birth", name_parts=recorded_name, thesaurus=thesaurus))
                    if aka_name:
                        decedent.add_name(
                            Name(name_type="also_known_as", name_parts=aka_name, thesaurus=thesaurus))
                else:
                    if row["maiden_name"]:
                        this_name = recorded_name.copy()
                        this_name['surname'] = row['maiden_name']
                        this_name['house_name'] = None
                        decedent.add_name(Name(name_type="birth", name_parts=this_name, thesaurus=thesaurus))

                    if row["spouse"] or row["uxoratus"]:
                        decedent.add_name(Name(name_type="married", name_parts=recorded_name, thesaurus=thesaurus))
                    elif age.duration < datetime.timedelta(days=13) or \
                            (age.duration < datetime.timedelta(days=365*13) and not age.year_day_ambiguity):
                        # we'll assume 12-year-old and younger girls were not getting married...
                        decedent.add_name(Name(name_type="birth", name_parts=recorded_name, thesaurus=thesaurus))
                    else:
                        decedent.add_name(Name(name_type="unknown", name_parts=recorded_name, thesaurus=thesaurus))

            if row["coelebs"]:
                decedent.add_fact(Fact(fact_type="NumberOfMarriages", content=0))

            if row["uxoratus"]:
                decedent.add_fact(Fact(fact_type="NumberOfMarriages", content=">0"))

            if row["death_date"]:
                death_date = parse_date(row["death_date"], row["year"])
                decedent.add_fact(Fact(fact_type="Death", date=death_date,
                                       age=age, locations=location, sources=source))
            else:
                death_date = None

            if row["burial_date"]:
                decedent.add_fact(Fact(fact_type="Burial", date=parse_date(row["burial_date"], row["year"]),
                                       age=age, locations=location, sources=source))

            print('"decedent": ' + repr(decedent))

            if row["father"]:
                if row["father"] == "[illegitimate]":
                    decedent.add_fact(Fact(fact_type="IllegitimateBirth", sources=source))
                else:
                    father = Person(gender="m",
                                    names=Name(name_type="birth",
                                               name_parts={"given": row["father"], "surname": surname},
                                               thesaurus=thesaurus),
                                    sources=source)
                    father_rel = Relationship(father.identifier, decedent.identifier, "parent-child", sources=source)

                    if row["father_deceased"] and death_date:
                        father.add_fact(Fact(fact_type="Death", date=Date("", death_date.end)))

                    print('"father": ' + repr(father))

            if row["mother"]:
                mother = Person(gender="f",
                                names=Name(name_type="married",
                                           name_parts={"given": row["mother"], "surname": surname},
                                           thesaurus=thesaurus),
                                sources=source)
                mother_rel = Relationship(mother.identifier, decedent.identifier, "parent-child", sources=source)

                if row["mother_deceased"] and death_date:
                    mother.add_fact(Fact(fact_type="Death", date=Date("", death_date.end)))

                print('"mother": ' + repr(mother))

            if row["spouse"]:
                if decedent.gender == "m":
                    spouse = Person(gender="f", names=Name())
                else:
                    spouse = Person(gender="m", names=Name())
