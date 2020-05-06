"""Module containing classes that define a genealogical data model.

This model is inspired by the Gedcom X conceptual model, but is much simpler and is specific to the particular
task at hand. It is not meant to be a general-purpose genealogical data model. Among the many differences relative
to Gedcom X are the following:

- There are no Events, only Facts.
- The Date model has been modified.
- There is a separate class for Durations (e.g. the age of a Person).
- The Name class has been grossly simplified.
- SourceDescription has been grossly simplified and renamed Source.
- PlaceDescription has been grossly simplified, made house-number-centric, and renamed Location.
- Agent, Group, and Document are not implemented.
- Added Statement class, which is like a Conclusion but without a source.
- Date, Location, Duration, and Conclusion are subclasses of Statement.

__str__ methods return a reasonably terse human-readable depiction of the object.

__repr__ methods return the full object serialized as JSON.

Each class also has a json_dict method, which returns a python dict that can be serialized into JSON
representation.

Some classes also have a summarize() method that provides a more verbose human-readable summary.

"""

import datetime
import uuid
import logging
import json


class Statement:
    """Abstract class for a statement about something.

    Attributes:
        notes (list of str): Note(s) about this statement.
        confidence (str): A confidence level for this statement. Should be either "normal" or "low".

    Args:
        notes (str or list of str or None): Note(s) about this conclusion.
    """

    def __init__(self, notes=None, confidence="normal"):
        if type(notes) is list or notes is None:
            self.notes = notes
        else:
            self.notes = [notes]

        self.confidence = confidence

    def __repr__(self):
        return json.dumps(self.json_dict())

    def json_dict(self):
        return {"notes": self.notes, "confidence": self.confidence}

    def add_note(self, note):
        if self.notes is None:
            self.notes = [note]
        else:
            self.notes.append(note)


class Conclusion(Statement):
    """Abstract class for a basic genealogical data item.

    Attributes:
        sources (list of Source): Source(s) related to this conclusion.
        notes (list of str): Note(s) about this conclusion.
        confidence (str): A confidence level for this conclusion. Should be either "normal" or "low".

    Args:
        sources (Source or list of Source or None): Source(s) related to this conclusion.
        notes (str or list of str or None): Note(s) about this conclusion.
    """
    def __init__(self, sources=None, notes=None, confidence="normal"):
        super().__init__(notes=notes, confidence=confidence)
        if type(sources) is list or sources is None:
            self.sources = sources
        else:
            self.sources = [sources]

    def json_dict(self):
        output = {}
        if self.sources:
            output.update({"sources": [x.json_dict() for x in self.sources]})
        output.update(super().json_dict())
        return output

    def add_source(self, source):
        if self.sources is None:
            self.sources = [source]
        else:
            self.sources.append(source)


class Fact(Conclusion):
    """A data item that is presumed to be true about a specific subject.

    Subjects can be a person or a relationship. In contrast to the full Gedcom X, there is no
    distinction between Facts and Events. For occurrences that involve more than one Person (e.g. marriages),
    the Fact should be attached to the Relationship object.

    Attributes:
        fact_type (str): The type of Fact. Should correspond to one of the Gedcom X Known Fact Types.
        content (str or int): Any string or numerical content associated with the fact. For example,
            in a "MaritalStatus" fact, the fact_content would be one of "Single", "Married", "Widowed", or
            "Divorced". For "NumberOfMarriages" or "NumberOfChildren", this could be an integer, or a marker
            like ">0" (if, say, the person is know to have had children, but the number is unknown).
        date (Date): The date or date range associated with the fact. Date ranges are used to
            denote precision (e.g. an event that took place in 1862 but for which we do not have a recorded
            month or year should have a Date that spans the range 1862-01-01 to 1862-12-31). Issues related
            to accuracy (e.g. handwriting issues, possible typos) should be indicated through
            Conclusion.confidence.
        age (Duration): The age of the individual at the time of the Fact.
        locations (list of Location): The Location(s) associated with this Fact took place (may be more
            than one for a marriage).
    """
    def __init__(self, fact_type=None, date=None, age=None, locations=None, content=None,
                 sources=None, notes=None, confidence="normal"):
        super().__init__(sources=sources, notes=notes, confidence=confidence)
        self.fact_type = fact_type
        self.content = content
        self.date = date
        self.age = age
        if type(locations) is list or locations is None:
            self.locations = locations
        else:
            self.locations = [locations]

    def json_dict(self):
        output = {"fact_type": self.fact_type, "content": self.content}
        if self.age:
            output.update({"age": self.age.json_dict()})
        if self.date:
            output.update({"date": self.date.json_dict()})
        if self.locations:
            output.update({"locations": [x.json_dict() for x in self.locations]})
        output.update(super().json_dict())
        return output

    def __str__(self):
        top_line = format(self.fact_type)
        if self.content:
            top_line = top_line + " = {}".format(self.content)
        top_line = top_line + "\n"
        output = [top_line]
        if self.date:
            output.append("\tDate: {}\n".format(str(self.date)))
        if self.age:
            output.append("\tAge: {}\n".format(str(self.age)))
        if self.locations:
            places = [str(loc) for loc in self.locations]
            output.append("\tHouse number(s) {}".format(", ".join(places)))

        return "".join(output)

    def add_location(self, location):
        if self.locations is None:
            self.locations = [location]
        else:
            self.locations.append(location)


class Name(Conclusion):
    """Defines a name of a person.

    Attributes:
        name_type (str): Name type, one of "birth", "married", "also_known_as", etc.
        name_parts (dict): Identified name parts. Keys are used to identify the name part (must be one
            of "prefix", "suffix", "given", "surname", or "house"), and the values are the actual names as
            found in the record.
        standard_given (str): Given name that has been standardized against a thesaurus.
        standard_surname (str): Surname that has been standardized against a thesaurus.
        date (Date): The date range of applicability of the name.

    Args:
        thesaurus (dict): The thesaurus to be used to standardize name parts. The keys consist of non-standard forms,
            and the values are the standardized from.
    """
    __name_order = ["prefix", "given", "surname", "suffix", "house"]

    def __init__(self, name_type=None, name_parts=None, date=None,
                 sources=None, notes=None, confidence="normal", thesaurus=None):
        super().__init__(sources=sources, notes=notes, confidence=confidence)
        self.name_type = name_type
        self.name_parts = name_parts
        self.date = date
        self.standard_given = None
        self.standard_surname = None

        if thesaurus:
            logger = logging.getLogger("twig_graft")
            if "given" in self.name_parts.keys():
                try:
                    self.standard_given = thesaurus[self.name_parts["given"]]
                except KeyError:
                    logger.info("key miss while standardizing given name '{}'".format(self.name_parts["given"]))

            if "surname" in self.name_parts.keys():
                try:
                    self.standard_surname = thesaurus[self.name_parts["surname"]]
                except KeyError:
                    logger.info("key miss while standardizing surname '{}'".format(self.name_parts["surname"]))

    def json_dict(self):
        output = {"name_type": self.name_type, "name_parts": self.name_parts,
                  "standard_surname": self.standard_surname,
                  "standard_given": self.standard_given}
        if self.date:
            output.update({"date": self.date.json_dict()})
        output.update(super().json_dict())
        return output

    def __str__(self):
        output = [self.name_parts[x] for x in Name.__name_order
                  if x in self.name_parts and self.name_parts[x] is not None]
        output.append("({})".format(self.name_type))
        return " ".join(output)


class Person(Conclusion):
    """A description of a person.

    Attributes:
        names (list of Name): The name(s) of the person. A person can have only one "given" and one "married" name.
        gender (str): The sex of the person.
        facts (list of Fact): Fact(s) regarding the person.
        identifier (str): A unique internal identifier for this person.

    Args:
        names (Name or list of Name or None): The name(s) of the person
        facts (Fact or list of Fact or None): Fact(s) regarding the person.
    """
    def __init__(self, names=None, gender=None, facts=None,
                 sources=None, notes=None, confidence="normal"):
        super().__init__(sources=sources, notes=notes, confidence=confidence)

        if names:
            if type(names) is list:
                if len([n for n in names if n.name_type == "birth"]) > 1:
                    raise ValueError("a Person can only have one birth Name")
                if len([n for n in names if n.name_type == "married"]) > 1:
                    raise ValueError("a Person can only have one married Name")
                self.names = names
            elif type(names) is Name:
                self.names = [names]
            else:
                raise ValueError("names must be a Name object or a list thereof")
        else:
            self.names = None

        if type(facts) is list or facts is None:
            self.facts = facts
        else:
            self.facts = [facts]

        self.gender = gender
        self.identifier = str(uuid.uuid4())

    def json_dict(self):
        output = {"identifier": self.identifier, "gender": self.gender}
        if self.names:
            output.update({"names": [x.json_dict() for x in self.names]})
        if self.facts:
            output.update({"facts": [x.json_dict() for x in self.facts]})
        output.update(super().json_dict())
        return output

    def __str__(self):
        pass
        # TODO maybe something vaguely like
        #       "Anna Bobak (nee Andrec), born 1801-02-03, married 1819-01-02, died/buried 1859-06-07"

    def add_fact(self, fact):
        if self.facts is None:
            self.facts = [fact]
        else:
            self.facts.append(fact)

    def add_name(self, name):
        if type(name) is not Name:
            raise ValueError("only Name objects can be added as the name of a Person")

        if self.names is None:
            self.names = [name]
        else:
            self.names.append(name)
            if len([n for n in self.names if n.name_type == "birth"]) > 1:
                raise ValueError("a Person can only have one birth Name")
            if len([n for n in self.names if n.name_type == "married"]) > 1:
                raise ValueError("a Person can only have one married Name")

    def summarize(self):
        """A longer-form text summary of a Person object."""
        output = ["Person {}, gender={}\n".format(self.identifier, self.gender)]
        if self.names is not None:
            for name in self.names:
                output.append("{}\n".format(str(name)))

        if self.facts is not None:
            for fact in self.facts:
                output.append("{}\n".format(str(fact)))

        return "".join(output)

    def get_name(self, name_type):
        """Extract Name of a particular type, if it exists. Return None if nonexistent.

        Only returns the first occurrence if there is more than one.
        """
        return next((n for n in self.names if n.name_type == name_type), None)


class Relationship(Conclusion):
    """A description of a relationship between two Persons.

    Attributes:
        from_id (str): Internal identifier of the "source" Person of the relationship. For a "parent-child"
            relationship_type, this is the parent. For a "spouse" relationship_type, this is the husband.
        to_id (str): Internal identifier of the "destination" Person of the relationship. For a "parent-child"
            relationship_type, this is the child. For a "spouse" relationship_type, this is the wife.
        relationship_type (str): The type of relationship. Must be either "spouse" or "parent-child".
        facts (list of Fact): Fact(s) relating to the relationship, generally a birth/baptism or marriage.
        identifier (str): A unique internal identifier for this relationship.

    Args:
        facts (Fact or list of Fact or None): Fact(s) relating to the relationship, generally a birth/baptism
            or marriage.
    """
    def __init__(self, from_id, to_id, relationship_type, facts=None,
                 sources=None, notes=None, confidence="normal"):
        super().__init__(sources=sources, notes=notes, confidence=confidence)

        if relationship_type != "spouse" and relationship_type != "parent-child":
            raise ValueError("relationship_type must be 'spouse' or 'parent-child'")

        if type(facts) is list or facts is None:
            self.facts = facts
        else:
            self.facts = [facts]

        self.from_id = from_id
        self.to_id = to_id
        self.relationship_type = relationship_type
        self.identifier = str(uuid.uuid4())

    def json_dict(self):
        output = {"identifier": self.identifier, "from_id": self.from_id, "to_id": self.to_id,
                  "relationship_type": self.relationship_type}
        if self.facts:
            output.update({"facts": [x.json_dict() for x in self.facts]})
        output.update(super().json_dict())
        return output


class Location(Statement):
    """A location specified by house number(s) and possible alternate village.

    Attributes:
        house_number (int): The house number, or the first listed house number if there was a renumbering
            (e.g. a metrical book entry like "123/245" would have a house_number of 123).
        alt_house_number (int): An alternative house number arising from renumbering (e.g. a metrical
            book entry like "123/245" would have an alt_house_number of 245). Should be None if only one
            house number is given in the metrical book entry.
        alt_village (str): The name of the village that the house number corresponds to, if it is indicated
            in the metrical book entry. Otherwise, it should be None, and is assumed to be the village
            where the parish is located.
    """
    def __init__(self, house_number=None, alt_house_number=None, alt_village=None, notes=None, confidence="normal"):
        super().__init__(notes=notes, confidence=confidence)
        self.house_number = house_number
        self.alt_house_number = alt_house_number
        self.alt_village = alt_village

    def json_dict(self):
        output = {"house_number": self.house_number, "alt_house_number": self.alt_house_number,
                  "alt_village": self.alt_village}
        output.update(super().json_dict())
        return output

    def __str__(self):
        output = []
        if self.house_number is not None:
            output.append('{}'.format(self.house_number))
        if self.alt_house_number is not None:
            output.append('/{}'.format(self.alt_house_number))
        if self.alt_village is not None:
            output.append(' ({})'.format(self.alt_village))
        return "".join(output)


class Date(Statement):
    """A date or date range of a genealogical event/fact.

    A precise date is represented by the degenerate range with self.start == self.end.
    A specific year or month should be represented as a range (e.g. the year 1898 should be
    represented as the range 1898-01-01 to 1898-12-31). For an open-ended range (i.e. where either start
    or end is unspecified), set self.start or self.end to datetime.date.min or datetime.date.max, respectively.

    Attributes:
        start (datetime.date): The start of a date rage.
        end (datetime.date): The end of the date range
        confidence (str): The confidence level of the date.

    Args:
        start_val (str or datetime.date): Should be an ISO-format date string (YYYY-MM-DD) or a datetime.date
            object. If end_date is not specified, then this is used to represent a specific day. If end_date is
            specified, this represents the start date of the interval. If the date range is to be unbounded from
            below, then it should be passed an empty string.
        end_val (str or datetime.date or None): Should be an ISO-format date string (YYYY-MM-DD) or a datetime.date
            object representing the end date of the interval. If the date range is to be unbounded from above,
            then it should be passed an empty string.
        confidence (str or None): The confidence level of the date.
    """
    def __init__(self, start_val, end_val=None, notes=None, confidence="normal"):
        super().__init__(notes=notes, confidence=confidence)
        if type(start_val) is datetime.date:
            self.start = start_val
        else:
            if start_val != "":
                self.start = datetime.datetime.strptime(start_val, "%Y-%m-%d").date()
            else:
                self.start = datetime.date.min

        if end_val is None:
            self.end = self.start
        else:
            if type(end_val) is datetime.date:
                self.end = end_val
            else:
                if end_val != "":
                    self.end = datetime.datetime.strptime(end_val, "%Y-%m-%d").date()
                else:
                    self.end = datetime.date.max

        self.confidence = confidence

    def json_dict(self):
        output = {"start": self.start.isoformat(), "end": self.end.isoformat(),
                  "confidence": self.confidence}
        output.update(super().json_dict())
        return output

    def __str__(self):
        if self.start == self.end:
            output = self.start.isoformat()
        else:
            output = 'between {} and {}'.format(self.start.isoformat(), self.end.isoformat())

        if self.confidence:
            output = output + '({} confidence)'.format(self.confidence)

        return output

    def is_exact(self):
        if self.start == self.end:
            return True
        else:
            return False

    def before(self, comp_date, strict=False):
        pass

    def after(self, comp_date, strict=False):
        pass

    def same(self, comp_date):
        pass

    def subtract(self, duration):
        """Subtract a Duration from a Date and return a new Date.

        With all of the appropriate precisions and ranges set correctly, of course.
        """
        pass


class Duration(Statement):
    """The duration of a time interval.

    Objects of this class are typically used to represent the age of a Person at the time of a particular
    Fact.

    Attributes:
        duration_list (list of int): The duration of the interval expressed as a list of the form
            (years, months, weeks, days), where each entry is an integer.
        duration  (datetime.timedelta): The duration of the interval.
        precision (str): The precision of the duration. Must be one of ("year", "month", "week", "day").
            For example, a death record specifying that the age of the deceased was "4 2/3 annorum"
            should be given a precision of "month".
        confidence (str): Confidence level (accuracy) of the duration. Must be one of "normal" or "low".
            Confidence is independent of precision: the priest may have written "4 2/3 annorum" (i.e. a
            precision of "month"), but if sloppy penmanship makes it hard to tell whether the number is
            a "4" or a "9", then the confidence level is only to within 5 years.
        year_day_ambiguity (bool): Indicates if there is a unit ambiguity between days and years.
            This happens for some death records where the pre-printed column heading for age is "dies
            vitae", but where a number was entered without units and there is a chance that the entered
            number actually represents years rather than days. Precision should correspond to the
            most likely unit based on other evidence in the record.

    Args:
        duration_list (list of int): The duration of the interval expressed as a list of the form
            (years, months, weeks, days), where each entry is an integer.
        precision (str or None): The precision of the duration (see Attributes above). If None, then
            the precision will be inferred from the duration_list.
    """
    def __init__(self, duration_list=None, precision=None, notes=None, confidence="normal",
                 year_day_ambiguity=None):
        super().__init__(notes=notes, confidence=confidence)
        self.duration_list = duration_list
        self.duration = datetime.timedelta(weeks=duration_list[2],
                                           days=365*duration_list[0]+30*duration_list[1]+duration_list[3])
        if precision is None:
            if sum(duration_list) == 0:
                self.precision = "day"
            else:
                # find last non-zero element of reversed duration_list
                index = next(x for x, val in enumerate(reversed(duration_list)) if val > 0)
                self.precision = ["day", "week", "month", "year"][index]
        else:
            self.precision = precision

        self.confidence = confidence
        self.year_day_ambiguity = year_day_ambiguity

    def json_dict(self):
        output = {"duration": self.duration_list, "confidence": self.confidence,
                  "precision": self.precision, "year_day_ambiguity": str(self.year_day_ambiguity)}
        output.update(super().json_dict())
        return output

    def __str__(self):
        time_names = ("years", "months", "weeks", "days")
        output = []
        for i in range(4):
            if self.duration_list[i] == 0:
                continue
            output.append(str(self.duration_list[i]) + " " + time_names[i])
        return ", ".join(output)


class Source:
    """A reference to a source description.

    Attributes:
        repository (str): Identification of repository where the record is located.
        volume (str): The repository's identifier for the volume in which the source record is located.
        page_number (int): The page number on which the record is located.
        entry_number (int): The entry number of the record.
        image_file (str): The name of the image file in which the source record is located.
    """
    def __init__(self, repository=None, volume=None, page_number=None, entry_number=None,
                 image_file=None):
        self.repository = repository
        self.volume = volume
        self.page_number = page_number
        self.entry_number = entry_number
        self.image_file = image_file

    def __repr__(self):
        return json.dumps(self.json_dict())

    def json_dict(self):
        return {"repository": self.repository, "volume": self.volume, "page_number": self.page_number,
                "entry_number": self.entry_number,
                "image_file": self.image_file}

    def __str__(self):
        return '{}, volume {}, page {}, entry {} ({})'.format(self.repository,
                                                              self.volume,
                                                              self.page_number,
                                                              self.entry_number,
                                                              self.image_file)
