import logging
import csv
import re
import calendar

from data_model import *


class ParseError(Exception):
    pass


def parse_alternate_name(name_string):
    """Parse a name entry that potentially has a parenthetical alternate.

    >>> parse_alternate_name("Smith (Jones)")
    ('Smith', 'Jones')
    >>> parse_alternate_name("Smith")
    ('Smith', None)
    """
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
    """Parse comma-delimited name (i.e. surname, given).

    Args:
        name_string (str): The input string to be parsed.

    Returns:
        surname (str or None): The surname.
        given (str or None): The given name.

    >>> parse_comma_name("Doe, John")
    ("Doe", "John")
    >>> parse_comma_name("Doe")
    ("Doe", None)
    >>> parse_comma_name(", John")
    (None, "John")
    """

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


def parse_name(surname_col, given_col):
    """Construct dicts from surname and given name CSV columns.

    >>> parse_name("Smith (Jones)", "John (Shorty)")
    ({'surname': 'Smith', 'house_name': 'Jones', 'given': 'John'},
    {'surname': 'Smith', 'house_name': 'Jones', 'given': 'Shorty'}, False)
    """
    recorded_name = None
    aka_name = None
    stillbirth = False
    if surname_col:
        surname, house_name = parse_alternate_name(surname_col)
        recorded_name = {"surname": surname}
        if house_name:
            recorded_name["house_name"] = house_name

    if given_col:
        given, aka = parse_alternate_name(given_col)
        if aka:
            aka_name = recorded_name.copy()
            aka_name["given"] = aka

        if given == "[stillbirth]":
            stillbirth = True
        else:
            recorded_name["given"] = given

    return recorded_name, aka_name, stillbirth


def parse_date(date_string, year):
    """Convert date strings into a Date object.

    Args:
        date_string (str): A string of the form "YYYY-MM-DD" or "MM-DD", where "DD" could be "[?]"
        year (str): A string of the form "YYYY"

    Returns:
        Date
    """
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


def parse_notes(row):
    """Extract notes and low confidence indicators.

    Args:
        row (dict of str): A row of a transcription CSV file. Value is modified to remove comments and question marks.

    Returns:
        notes (dict of str): The extracted notes, indexed with the same keys as the row argument.
        confidence (dict of str): The extracted confidences, indexed with the same keys as the row argument.

    >>> parse_notes({"thing1": "Some information <a comment>", "thing2": "Uncertain information? <another comment>"})
    ({'thing1': 'a comment', 'thing2': 'another comment'}, {'thing2': 'low'})
    """

    notes = {}
    confidence = {}
    for key, value in row.items():
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

    return notes, confidence


def add_notes_confidence(statement, notes, confidence, fields):
    this_note = [v for k, v in notes.items() if k in fields]
    if this_note:
        statement.add_note(this_note)
    if [v for k, v in confidence.items() if k in fields]:
        statement.confidence = "low"
    return statement


class DeathRecord:
    def __init__(self, age, thesaurus, source, location, notes, confidence):
        self.age = age
        self.thesaurus = thesaurus
        self.source = source
        self.location = location
        self.notes = notes
        self.confidence = confidence

        self.recorded_name = None
        self.death_date = None

        self.decedent = Person(sources=self.source)
        self.father = None
        self.father_rel = None
        self.mother = None
        self.mother_rel = None
        self.parent_rel = None
        self.mf = None
        self.m_mf_rel = None
        self.mm = None
        self.m_mm_rel = None
        self.mmf = None
        self.mm_mmf_rel = None

        # siblings?

        self.spouse = None
        self.decedent_marriage = None

        self.logger = logging.getLogger("twig_graft")
        self.maximum_age = datetime.timedelta(days=365 * 110)

    def add_fact(self, person, fact, fields):
        """Add a Fact, along with any associated notes and confidence values, to a Person.

        Args:
            person (Person): The Person object to which the Fact is to be added.
            fact (Fact): The Fact to be added.
            fields (list of str): The names of the record columns that are relevant to that fact.
        """
        person.add_fact(
            add_notes_confidence(fact, self.notes, self.confidence, fields))

    def add_name(self, person, name, fields):
        """Add a Name, along with any associated notes and confidence values, to a Person.

        Args:
            person (Person): The Person object to which the Name is to be added.
            name (Name): The Name to be added.
            fields (list of str): The names of the record columns that are relevant to that fact.
        """
        person.add_name(
            add_notes_confidence(name, self.notes, self.confidence, fields))

    def set_decedent_names(self, surname_col, given_col, married, maiden_surname=None):
        """Set the names of the decedent.

        Args:
            surname_col (str or None): The contents of the "surname" column in the CSV file.
            given_col (str or None): The contents of the "given_name" column in the CSV file.
            married (bool or None): True if it is known that the decedent was married, False if it is known that
                that the decedent was never married, and None if the marital status is unknown.
            maiden_surname (str or None): The decedent's maiden surname.
        """
        self.recorded_name, aka_name, stillbirth = parse_name(surname_col, given_col)

        if stillbirth:
            self.decedent.add_fact(Fact(fact_type="Stillbirth", sources=self.source))
            return

        too_young_to_be_married = self.age.duration < datetime.timedelta(days=13) or \
                                  (self.age.duration < datetime.timedelta(days=365*13)
                                   and not self.age.year_day_ambiguity)

        if self.decedent.gender == "m" or (self.decedent.gender == "f" and
                                           (married is False or too_young_to_be_married)):
            if self.recorded_name:
                self.add_name(self.decedent,
                              Name(name_type="birth", name_parts=self.recorded_name, thesaurus=self.thesaurus),
                              ["surname", "given_name"])
            if aka_name:
                self.add_name(self.decedent,
                              Name(name_type="also_known_as", name_parts=aka_name, thesaurus=self.thesaurus),
                              ["surname", "given_name"])
            return

        # deal with potentially name-changing females

        if maiden_surname:
            this_name = self.recorded_name.copy()
            this_name['surname'] = maiden_surname
            this_name['house_name'] = None
            self.add_name(self.decedent,
                          Name(name_type="birth", name_parts=this_name, thesaurus=self.thesaurus),
                          ["maiden_name", "given_name"])

        if married is True:
            self.add_name(self.decedent,
                          Name(name_type="married", name_parts=self.recorded_name, thesaurus=self.thesaurus),
                          ["surname", "given_name"])

        if married is None:
            self.add_name(self.decedent,
                          Name(name_type="unknown", name_parts=self.recorded_name, thesaurus=self.thesaurus),
                          ["surname", "given_name"])

    def set_birth_death(self, death_date_col, burial_date_col, year_col, birth_year_col):
        if death_date_col:
            self.death_date = parse_date(death_date_col, year_col)
            self.add_fact(self.decedent,
                          Fact(fact_type="Death", date=self.death_date, age=self.age,
                               locations=self.location, sources=self.source),
                          ["death_date", "year"])
        else:
            self.death_date = None

        if burial_date_col:
            burial_date = parse_date(burial_date_col, year_col)
            self.add_fact(self.decedent,
                          Fact(fact_type="Burial", date=burial_date, age=self.age,
                               locations=self.location, sources=self.source),
                          ["burial_date", "year"])

            if not self.death_date:
                # We only know the burial date. Assume death occurred within the previous week.
                self.death_date = Date(burial_date.start - datetime.timedelta(days=6),
                                       burial_date.end,
                                       notes=["Death date unknown, estimated from burial date."],
                                       confidence="calculated")
                self.add_fact(self.decedent,
                              Fact(fact_type="Death", date=self.death_date, age=self.age,
                                   locations=self.location, sources=self.source),
                              ["death_date", "year"])
        else:
            burial_date = None

        if self.death_date is None and burial_date is None:
            self.logger.error("Both death and burial dates missing. Nonstandard record?")

        birth = Fact(fact_type="birth")
        notes = self.death_date.notes.append("Birth date calculated from actual or estimated death date.")
        birth.add_note(notes)
        birth_date = subtract(self.death_date, self.age)

        if birth_year_col:
            birth_year = int(birth_year_col)
            if birth_date.start < datetime.date(birth_year, 1, 1):
                birth_date.start = datetime.date(birth_year, 1, 1)
            if birth_date.end > datetime.date(birth_year, 12, 31):
                birth_date.end = datetime.date(birth_year, 12, 31)

        birth.date = birth_date
        self.add_fact(self.decedent, birth, ["birth_year"])

    def set_parents(self, father_col, father_deceased, mother_col, mother_deceased):
        if father_col:
            if father_col == "[illegitimate]":
                self.decedent.add_fact(Fact(fact_type="IllegitimateBirth", sources=self.source))
            else:
                self.father = Person(gender="m",
                                     names=Name(name_type="birth",
                                                name_parts={"given": father_col,
                                                            "surname": self.recorded_name["surname"]},
                                                thesaurus=self.thesaurus),
                                     sources=self.source)
                self.father_rel = Relationship(self.father.identifier, self.decedent.identifier,
                                               "parent-child", sources=self.source)

                if father_deceased and self.death_date:
                    self.father.add_fact(Fact(fact_type="Death",
                                         date=Date(self.death_date.start - self.maximum_age, self.death_date.end)))

        if mother_col:
            self.mother = Person(gender="f",
                                 names=Name(name_type="married",
                                            name_parts={"given": mother_col, "surname": self.recorded_name["surname"]},
                                            thesaurus=self.thesaurus),
                                 sources=self.source)

            self.mother_rel = Relationship(self.mother.identifier, self.decedent.identifier,
                                           "parent-child", sources=self.source)

            if mother_deceased and self.death_date:
                self.mother.add_fact(Fact(fact_type="Death",
                                          date=Date(self.death_date.start - self.maximum_age, self.death_date.end)))

        if self.father and self.mother:
            self.parent_rel = Relationship(self.father.identifier, self.mother.identifier, "marriage",
                                           sources=self.source)

    def set_ancestors(self, mother, mothers_father, mothers_mother, mothers_mothers_father):
        mf_given = None
        mf_surname = None
        if mothers_father:
            mf_surname, mf_given = parse_comma_name(mothers_father)

        mmf_given = None
        mmf_surname = None
        if mothers_mothers_father:
            mmf_surname, mmf_given = parse_comma_name(mothers_mothers_father)

        if mf_surname and mf_given:
            self.mf = Person(gender="m",
                                    names=Name(name_type="birth",
                                               name_parts={"given": mf_given, "surname": mf_surname},
                                               thesaurus=self.thesaurus),
                                    sources=self.source)
            self.m_mf_rel = Relationship(self.mf.identifier, self.mother.identifier, "parent-child",
                                         sources=self.source)

        if mothers_mother:
            self.mm = Person(gender="f",
                             names=Name(name_type="married",
                                        name_parts={"given": mothers_mother, "surname": mf_surname},
                                        thesaurus=self.thesaurus),
                             sources=self.source)
            if mmf_surname:
                self.mm.add_name(Name(name_type="birth",
                                      name_parts={"given": mothers_mother, "surname": mmf_surname},
                                      thesaurus=self.thesaurus))
            self.m_mm_rel = Relationship(self.mm.identifier, self.mother.identifier, "parent-child",
                                         sources=self.source)

        if mmf_given:
            self.mmf = Person(gender="m",
                              names=Name(name_type="birth",
                                         name_parts={"given": mmf_given, "surname": mmf_surname},
                                         thesaurus=self.thesaurus),
                              sources=self.source)
            self.mm_mmf_rel = Relationship(mothers_mothers_father.identifier, mothers_mother.identifier,
                                           "parent-child", sources=self.source)

        if mf_surname:
            self.mother.add_name(Name(name_type="birth",
                                 name_parts={"given": mother, "surname": mf_surname},
                                 thesaurus=self.thesaurus))

    def set_spouse(self, spouse_col, spouse_surname, spouse_deceased, years_married):
        if spouse_col:
            if self.decedent.gender == "m":
                self.spouse = Person(gender="f", names=Name(name_type="married",
                                                            name_parts={"given": spouse_col,
                                                                        "surname": self.recorded_name["surname"]},
                                                            sources=self.source, thesaurus=self.thesaurus))
                if spouse_surname:
                    self.spouse.add_name(Name(name_type="maiden",
                                              name_parts={"given": spouse_col,
                                                          "surname": spouse_surname},
                                              sources=self.source, thesaurus=self.thesaurus))

                self.decedent_marriage = Relationship(self.decedent.identifier, self.spouse.identifier, "spouse",
                                                      sources=self.source)
            else:
                self.spouse = Person(gender="m")
                if spouse_surname:
                    # TODO this means the spouse remarried?
                    pass
                self.decedent_marriage = Relationship(self.spouse.identifier, self.decedent.identifier, "spouse",
                                                      sources=self.source)

        if spouse_deceased:
            if self.spouse:
                self.spouse.add_fact(Fact(fact_type="death",
                                          date=Date(self.death_date.start - self.maximum_age, self.death_date.end),
                                          sources=self.source))
            else:
                # create a no-name spouse to record the fact that they pre-deceased the decedent
                if self.decedent.gender == "m":
                    self.spouse = Person(gender="f",
                                         names=Name(name_type="married",
                                                    name_parts={"surname": self.recorded_name["surname"]},
                                                    thesaurus=self.thesaurus))

                    self.decedent_marriage = Relationship(self.decedent.identifier, self.spouse.identifier,
                                                          "spouse", sources=self.source)
                else:
                    self.spouse = Person(gender="m")
                    self.decedent_marriage = Relationship(self.spouse.identifier, self.decedent.identifier,
                                                          "spouse", sources=self.source)
                self.spouse.add_fact(Fact(fact_type="death", date=Date(self.death_date.start - self.maximum_age,
                                                                       self.death_date.end),
                                          sources=self.source))

        if years_married:
            self.decedent_marriage.add_fact(
                Fact(fact_type="marriage",
                     date=Date(subtract(self.death_date,
                                        Duration(duration_list=[int(years_married), 0, 0, 0]))),
                     sources=self.source))

    def set_siblings(self, sibling_col):
        if sibling_col:
            siblings = sibling_col.split(';')
            for sibling_text in siblings:
                match = re.match(r'(\S+)\s+\((\S+)\)', sibling_text)
                if match:
                    sibling_name = match[1]
                    gender = match[2]
                else:
                    raise ParseError("Sibling name must have gender indication.")

                sibling = Person(gender=gender,
                                 names=Name(name_type="unknown",
                                            name_parts={"given": sibling_name,
                                                        "surname": self.recorded_name["surname"]}),
                                 sources=self.source)
            # TODO parse the semicolons, create Persons, potentially nameless parents, and
            #  parent-child Relations. This is a mess...


def import_deaths(filename, thesaurus):
    logger = logging.getLogger("twig_graft")
    logger.debug("importing {}".format(filename))

    with open(filename) as csv_file:
        reader = csv.DictReader(csv_file, delimiter=',', quotechar='"')
        for row_num, row in enumerate(reader):
            if row["surname"]:
                surname = row["surname"]
            else:
                logger.info("Row {} has no surname and so is either empty or nonstandard. Skipping.".format(row_num))
                continue

            source = Source(repository=row["repository"], volume=row["book"], page_number=row["page"],
                            entry_number=row["entry"], image_file=row["image"])

            # print(row)

            notes, confidence = parse_notes(row)
            # TODO need to add the above to the rest of the new objects

            # change empty strings to None
            # TODO do we really need this??
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

            this_record = DeathRecord(age, thesaurus, source, location, notes, confidence)
            this_record.decedent.gender = row["gender"]

            if row["coelebs"]:
                is_married = False
            elif row["uxoratus"] or row["spouse"] or row["maiden_name"] or row["widow(er)"]:
                is_married = True
            else:
                is_married = None

            this_record.set_decedent_names(row["surname"], row["given_name"], is_married, row["maiden_name"])

            if row["coelebs"]:
                this_record.decedent.add_fact(Fact(fact_type="NumberOfMarriages", content=0))

            if row["uxoratus"]:
                this_record.decedent.add_fact(Fact(fact_type="NumberOfMarriages", content=">0"))

            this_record.set_birth_death(row["death_date"], row["burial_date"], row["year"], row["birth_year"])
            this_record.set_parents(row["father"], row["father_deceased"], row["mother"], row["mother_deceased"])

            # TODO deal with "mothers_spouse". This could be a mess...

            # this_record.set_siblings(row["sibling"])

            this_record.set_spouse(row["spouse"], row["spouse_surname"], row["widow(er)"], row["years_married"])

            if row["second_marriage"]:
                this_record.set_spouse(row["spouse_2"], row["spouse_2_surname"],
                                       row["widow(er)_2"], row["years_married_2"])
