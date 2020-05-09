import logging
import csv
import re
import calendar

from data_model import *

maximum_age = datetime.timedelta(days=365*110)


class ParseError(Exception):
    pass


def parse_name(name_string):
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


def parse_comma_name(name_string):
    parts = name_string.split(',')
    
    if len(parts) == 1:
        surname = parts[0].strip()
        given = None
    elif len(parts) == 2:
        if parts[0] == "":
            surname = None
            given = parts[1].strip()
        else:
            surname = parts[0].strip()
            given = parts[1].strip()
    else:
        raise ParseError("couldn't parse name {}".format(name_string))

    return surname, given


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


def add_notes_confidence(statement, notes, confidence, fields):
    this_note = [v for k, v in notes.items() if k in fields]
    if this_note:
        statement.add_note(this_note)
    if [v for k, v in confidence.items() if k in fields]:
        statement.confidence = "low"
    return statement


def import_deaths(filename, thesaurus):
    logger = logging.getLogger("twig_graft")
    logger.debug("importing {}".format(filename))

    output = {}
    with open(filename) as csv_file:
        reader = csv.DictReader(csv_file, delimiter=',', quotechar='"')
        for row_num, row in enumerate(reader):
            if row["surname"]:
                surname = row["surname"]
            else:
                logger.info("Row {} has no surname and so is either empty or nonstandard. Skipping.".format(row_num))
                continue

            # print(row)

            # pull out notes and low confidence indicators
            notes = {}
            confidence = {}
            for key, value in row.items():
                # print("doing {}: {}".format(key, value))
                if value:
                    match = re.search(r'<(.+)>', value)
                    if match:
                        notes[key] = match[1]
                        row[key] = value.replace(match[0], "").strip()
                        value = row[key]

                    match = re.search(r'\?$', value)
                    if match:
                        confidence[key] = "low"
                        row[key] = value.rstrip(" ?")

            # TODO need to add the above to the rest of the new objects

            # change empty strings to None
            def c(i): return i or None
            row = {k: c(v) for k, v in row.items()}

            row["age_y"] = 0 if row["age_y"] is None else int(row["age_y"])
            row["age_m"] = 0 if row["age_m"] is None else int(row["age_m"])
            row["age_w"] = 0 if row["age_w"] is None else int(row["age_w"])
            row["age_d"] = 0 if row["age_d"] is None else int(row["age_d"])

            age = Duration(duration_list=[row["age_y"], row["age_m"], row["age_w"], row["age_d"]],
                           year_day_ambiguity=True if row["year_day"] else False)
            add_notes_confidence(age, notes, confidence, ["age_y", "age_m", "age_w", "age_d"])

            location = Location(house_number=row["house_number"],
                                alt_house_number=row["alt_house_number"],
                                alt_village=row["house_location"])
            add_notes_confidence(location, notes, confidence,
                                 ["house_number", "alt_house_number", "house_location"])

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

            # parse the other comma-delimited ancestor names for use below
            mf_given = None
            mf_surname = None
            if row["mothers_father"]:
                mf_surname, mf_given = parse_comma_name(row["mothers_father"])

            mmf_given = None
            mmf_surname = None
            if row["mothers_mothers_father"]:
                mmf_surname, mmf_given = parse_comma_name(row["mothers_mothers_father"])

            if row["gender"] == "m":
                if recorded_name:
                    decedent.add_name(
                        add_notes_confidence(Name(name_type="birth", name_parts=recorded_name,
                                                  thesaurus=thesaurus),
                                             notes, confidence, ["surname", "given_name"]))
                if aka_name:
                    decedent.add_name(
                        add_notes_confidence(Name(name_type="also_known_as", name_parts=aka_name,
                                                  thesaurus=thesaurus),
                                             notes, confidence, ["surname", "given_name"]))
            else:
                if row["coelebs"] is not None:
                    if recorded_name:
                        decedent.add_name(
                            add_notes_confidence(Name(name_type="birth", name_parts=recorded_name,
                                                      thesaurus=thesaurus),
                                                 notes, confidence, ["surname", "given_name"]))
                    if aka_name:
                        decedent.add_name(
                            add_notes_confidence(Name(name_type="also_known_as", name_parts=aka_name,
                                                      thesaurus=thesaurus),
                                                 notes, confidence, ["surname", "given_name"]))
                else:
                    if row["maiden_name"]:
                        this_name = recorded_name.copy()
                        this_name['surname'] = row['maiden_name']
                        this_name['house_name'] = None
                        decedent.add_name(
                            add_notes_confidence(Name(name_type="birth", name_parts=this_name,
                                                      thesaurus=thesaurus),
                                                 notes, confidence, ["maiden_name", "given_name"]))

                    if row["spouse"] or row["uxoratus"]:
                        decedent.add_name(
                            add_notes_confidence(Name(name_type="married", name_parts=recorded_name,
                                                      thesaurus=thesaurus),
                                                 notes, confidence, ["surname", "given_name"]))
                    elif age.duration < datetime.timedelta(days=13) or \
                            (age.duration < datetime.timedelta(days=365*13) and not age.year_day_ambiguity):
                        # we'll assume girls 12 years old and younger were not getting married...
                        decedent.add_name(
                            add_notes_confidence(Name(name_type="birth", name_parts=recorded_name,
                                                      thesaurus=thesaurus),
                                                 notes, confidence, ["surname", "given_name"]))
                    else:
                        decedent.add_name(
                            add_notes_confidence(Name(name_type="unknown", name_parts=recorded_name,
                                                      thesaurus=thesaurus),
                                                 notes, confidence, ["surname", "given_name"]))

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
                burial_date = parse_date(row["burial_date"], row["year"])
                decedent.add_fact(Fact(fact_type="Burial", date=burial_date,
                                       age=age, locations=location, sources=source))
            else:
                burial_date = None

            if death_date or burial_date:
                birth = Fact(fact_type="birth")
                if death_date:
                    birth_date = subtract(death_date, age)
                else:
                    # we only know the burial date, so assume death occurred within one week
                    birth_date = subtract(burial_date, age)
                    birth_date.start = birth_date.start - datetime.timedelta(days=6)
                    death_date = Date(burial_date.start - datetime.timedelta(days=6),
                                      burial_date.end,
                                      notes=["Death date unknown, estimated from burial date"],
                                      confidence="calculated")

                if row["birth_year"]:
                    birth_year = int(row["birth_year"])
                    if birth_date.start < datetime.date(birth_year, 1, 1):
                        birth_date.start = datetime.date(birth_year, 1, 1)
                    if birth_date.end > datetime.date(birth_year, 12, 31):
                        birth_date.end = datetime.date(birth_year, 12, 31)

                birth.date = birth_date
            else:
                logger.error("No death or burial date. Nonstandard record?")

            row_data = {"decedent": decedent.json_dict()}

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
                        father.add_fact(Fact(fact_type="Death",
                                             date=Date(death_date.start-maximum_age, death_date.end)))

                    row_data.update({"father": father.json_dict()})
                    row_data.update({"father_rel": father_rel.json_dict()})

            if row["mother"]:
                mother = Person(gender="f",
                                names=Name(name_type="married",
                                           name_parts={"given": row["mother"], "surname": surname},
                                           thesaurus=thesaurus),
                                sources=source)
                if mf_surname:
                    mother.add_name(Name(name_type="birth",
                                         name_parts={"given": row["mother"], "surname": mf_surname},
                                         thesaurus=thesaurus))

                mother_rel = Relationship(mother.identifier, decedent.identifier, "parent-child", sources=source)

                if row["mother_deceased"] and death_date:
                    mother.add_fact(Fact(fact_type="Death", date=Date(death_date.start-maximum_age, death_date.end)))

                row_data.update({"mother": mother.json_dict()})
                row_data.update({"mother_rel": mother_rel.json_dict()})

            if father and mother:
                parent_rel = Relationship(father.identifier, mother.identifier, "marriage", sources=source)
                # TODO broken! crash if record is missing a parent record

            if mf_surname and mf_given:
                mothers_father = Person(gender="m",
                                        names=Name(name_type="birth",
                                                   name_parts={"given": mf_given, "surname": mf_surname},
                                                   thesaurus=thesaurus),
                                        sources=source)
                m_mf_rel = Relationship(mothers_father.identifier, mother.identifier, "parent-child",
                                        sources=source)

            if row["mothers_mother"]:
                mothers_mother = Person(gender="f",
                                        names=Name(name_type="married",
                                                   name_parts={"given": row["mothers_mother"], "surname": mf_surname},
                                                   thesaurus=thesaurus),
                                        sources=source)
                if mmf_surname:
                    mothers_mother.add_name(Name(name_type="birth",
                                                 name_parts={"given": row["mothers_mother"], "surname": mmf_surname},
                                                 thesaurus=thesaurus))
                m_mm_rel = Relationship(mothers_mother.identifier, mother.identifier, "parent-child",
                                        sources=source)

            if mmf_given:
                mothers_mothers_father = Person(gender="m",
                                                names=Name(name_type="birth",
                                                           name_parts={"given": mmf_given, "surname": mmf_surname},
                                                           thesaurus=thesaurus),
                                                sources=source)
                mm_mmf_rel = Relationship(mothers_mothers_father.identifier, mothers_mother.identifier,
                                          "parent-child", sources=source)

            # TODO deal with "mothers_spouse". This could be a mess...

            if row['sibling']:
                siblings = row['sibling'].split(';')
                for sibling_text in siblings:
                    match = re.match(r'(\S+)\s+\((\S+)\)', sibling_text)
                    if match:
                        sibling_name = match[1]
                        gender = match[2]
                    else:
                        raise ParseError("Sibling name must have gender indication.")

                    sibling = Person(gender=gender,
                                     names=Name(name_type="unknown", name_parts={"given": sibling_name,
                                                                                 "surname": recorded_name["surname"]}),
                                     sources=source)
                # TODO parse the semicolons, create Persons, potentially nameless parents, and
                #  parent-child Relations. This is a mess...

            if row["spouse"]:
                if decedent.gender == "m":
                    spouse = Person(gender="f", names=Name(name_type="married",
                                                           name_parts={"given": row["spouse"],
                                                                       "surname": recorded_name["surname"]},
                                                           sources=source, thesaurus=thesaurus))
                    if row["spouse_surname"]:
                        spouse.add_name(Name(name_type="maiden",
                                             name_parts={"given": row["spouse"],
                                                         "surname": row["spouse_surname"]},
                                             sources=source, thesaurus=thesaurus))

                    decedent_marriage = Relationship(decedent.identifier, spouse.identifier, "spouse",
                                                     sources=source)
                else:
                    spouse = Person(gender="m")
                    if row["spouse_surname"]:
                        # TODO this means the spouse remarried. Ugh.
                        pass
                    decedent_marriage = Relationship(spouse.identifier, decedent.identifier, "spouse",
                                                     sources=source)

            if row["widow(er)"]:
                if spouse:
                    spouse.add_fact(Fact(fact_type="death", date=Date(death_date.start-maximum_age, death_date.end),
                                         sources=source))
                else:
                    # create a no-name spouse to record the fact that they pre-deceased the decedent
                    if decedent.gender == "m":
                        spouse = Person(gender="f",
                                        names=Name(name_type="married",
                                                   name_parts={"surname": recorded_name["surname"]},
                                                   thesaurus=thesaurus))

                        decedent_marriage = Relationship(decedent.identifier, spouse.identifier, "spouse",
                                                         sources=source)
                    else:
                        spouse = Person(gender="m")
                        decedent_marriage = Relationship(spouse.identifier, decedent.identifier, "spouse",
                                                         sources=source)
                    spouse.add_fact(Fact(fact_type="death", date=Date(death_date.start - maximum_age,
                                                                      death_date.end),
                                         sources=source))

            if row["years_married"]:
                decedent_marriage.add_fact(
                    Fact(fact_type="marriage",
                         date=Date(subtract(death_date,
                                            Duration(duration_list=[int(row["years_married"]), 0, 0, 0]))),
                         sources=source))

            # TODO now do it all over again for the second marriage, if there is one

            output["row{}".format(row_num)] = row_data

    print(json.dumps(output))
