"""Module containing classes that define a genealogical data model.

This model is loosely based on the Gedcom X conceptual model, but has been greatly simplified and modified.
The primary differences are as follows:

- There are no Events, only Facts
- The Date model has been modified
- The Name class has been grossly simplified
- The Source model has been modified
- Locations are house-number-centric
- Agents are not implemented

"""

import datetime
import uuid


class Conclusion:
    """Abstract class for a basic genealogical data item.

    Attributes:
        sources (list of Source): Source(s) related to this conclusion.
        notes (list of str): Note(s) about this conclusion.
        confidence (str): A confidence level for this conclusion.

    Args:
        sources (Source or list of Source or None): Source(s) related to this conclusion.
        notes (str or list of str or None): Note(s) about this conclusion.
    """
    def __init__(self, sources=None, notes=None, confidence=None):
        if type(sources) is list or sources is None:
            self.sources = sources
        else:
            self.sources = [sources]

        if type(notes) is list or notes is None:
            self.notes = notes
        else:
            self.notes = [notes]

        self.confidence = confidence

    def add_source(self, source):
        if self.sources is None:
            self.sources = [source]
        else:
            self.sources.append(source)

    def add_note(self, note):
        if self.notes is None:
            self.notes = [note]
        else:
            self.notes.append(note)

    def set_confidence(self, confidence):
        self.confidence = confidence


class Fact(Conclusion):
    """A data item that is presumed to be true about a specific subject.

    Subjects are typically a person or relationship. In contrast to the full Gedcom X, there is no
    distinction between Facts and Events. For occurrences that involve more than one Person (e.g. marriages),


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
                 sources=None, notes=None, confidence=None):
        super().__init__(sources=sources, notes=notes, confidence=confidence)
        self.fact_type = fact_type
        self.content = content
        self.date = date
        self.age = age
        if type(locations) is list or locations is None:
            self.locations = locations
        else:
            self.locations = [locations]

    def set_type(self, fact_type):
        self.fact_type = fact_type

    def set_content(self, content):
        self.content = content

    def set_date(self, date):
        self.date = date

    def set_age(self, age):
        self.age = age

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
            of "prefix", "suffix", "given", "surname", or "house"), and the values are the actual names.
        date (Date): The date range of applicability of the name.
    """
    __name_order = ["prefix", "given", "surname", "suffix", "house"]

    def __init__(self, name_type=None, name_parts=None, date=None,
                 sources=None, notes=None, confidence=None):
        super().__init__(sources=sources, notes=notes, confidence=confidence)
        self.name_type = name_type
        self.name_parts = name_parts
        self.date = date

    def __repr__(self):
        return " ".join([self.name_parts[x] for x in Name.__name_order
                        if x in self.name_parts and self.name_parts[x] is not None])

    def match_ll(self, query):
        pass


class Person(Conclusion):
    """A description of a person.

    Attributes:
        names (list of Name): The name(s) of the person.
        gender (str): The sex of the person.
        facts (list of Fact): Fact(s) regarding the person.
        identifier (uuid.uuid4): A unique internal identifier for this person.

    Args:
        names (Name or list of Name or None): The name(s) of the person
        facts (Fact or list of Fact or None): Fact(s) regarding the person.
    """
    def __init__(self, names=None, gender=None, facts=None,
                 sources=None, notes=None, confidence=None):
        super().__init__(sources=sources, notes=notes, confidence=confidence)

        if type(names) is list or names is None:
            self.names = names
        else:
            self.names = [names]

        if type(facts) is list or facts is None:
            self.facts = facts
        else:
            self.facts = [facts]

        self.gender = gender
        self.identifier = uuid.uuid4()

    def __repr__(self):
        output = ['Person({0}'.format(self.identifier)]
        if self.gender is not None:
            output.append('; gender="{0}"'.format(self.gender))
        if self.names is not None:
            output.append('; {0}="{1}"'.format(self.names[0].name_type, str(self.names[0])))
        output.append(')')
        return "".join(output)

    def __str__(self):
        pass
        # probably want something vaguely like
        #       "Anna Bobak (nee Andrec), born 1801-02-03, married 1819-01-02, died/buried 1859-06-07"

    def add_fact(self, fact):
        if self.facts is None:
            self.facts = [fact]
        else:
            self.facts.append(fact)

    def add_name(self, name):
        if self.names is None:
            self.names = [name]
        else:
            self.names.append(name)

    def set_gender(self, gender):
        self.gender = gender

    def name_match_ll(self, query_name, date):
        pass


class Relationship (Conclusion):
    """Attributes associated with a relationship between two Persons.

    Attributes:
        relationship_type (str): The type of relationship. Must be either "spouse" or "parent-child".
        facts (list of Fact): Fact(s) relating to the relationship, generally a birth/baptism or marriage.
        identifier (uuid.uuid4): A unique internal identifier for this relationship.

    Args:
        facts (Fact or list of Fact or None): Fact(s) relating to the relationship, generally a birth/baptism
            or marriage.
    """
    def __init__(self, relationship_type=None, facts=None,
                 sources=None, notes=None, confidence=None):
        super().__init__(sources=sources, notes=notes, confidence=confidence)

        if type(facts) is list or facts is None:
            self.facts = facts
        else:
            self.facts = [facts]

        self.relationship_type = relationship_type
        self.identifier = uuid.uuid4()

    def match_ll(self, query):
        pass


class Location:
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
    def __init__(self, house_number=None, alt_house_number=None, alt_village=None):
        self.house_number = house_number
        self.alt_house_number = alt_house_number
        self.alt_village = alt_village

    def __repr__(self):
        output = ['Location(']
        if self.house_number is not None:
            output.append('{}'.format(self.house_number))
        if self.alt_house_number is not None:
            output.append('/{}'.format(self.alt_house_number))
        if self.alt_village is not None:
            output.append(' {}'.format(self.alt_village))
        output.append(')')
        return "".join(output)


class Date:
    """A date or date range of a genealogical event/fact.

    Attributes:
        date (datetime.date): A datetime.date object or a list of two datetime.date objects.
            In the former case, it represents a specific day (to the stated
            confidence level). In the latter case, it represents a date range, with the
            first date representing the start and the second, the end of the rage. To represent open-ended
            ranges, use datetime.date.min or datetime.date.max. A specific year or month should be represented
            as a range (e.g. the year 1898 should be represented as the range 1898-01-01 to 1898-12-31).
        confidence (str): The confidence level of the date.

    Args:
        start_date (str): Should be an ISO-format date string (YYYY-MM-DD). If end_date is not specified,
            then this is used to represent a specific day. If end_date is specified, this represents the
            start date of the interval. If the date range is to be open-ended, then it should be
            an empty string.
        end_date (str or None): Should be an ISO-format date string (YYYY-MM-DD) representing the end date of
            the interval. If the date range is to be open-ended, then it should be passed
            an empty string.
        confidence (str or None): The confidence level of the date.
    """
    def __init__(self, start_date, end_date=None, confidence=None):
        if start_date != "":
            start = datetime.datetime.strptime(start_date, "%Y-%m-%d")
        else:
            start = datetime.date.min

        if end_date is None:
            self.date = start
        else:
            if end_date != "":
                self.date = [start, datetime.datetime.strptime(start_date, "%Y-%m-%d")]
            else:
                self.date = [start, datetime.date.max]

        self.confidence = confidence

    def match_ll(self, query):
        pass


class Duration:
    """The duration of a time interval.

    Objects of this class are typically used to represent the age of Person at the time of a particular
    Fact.

    Attributes:
        duration  (datetime.timedelta): The duration of the interval.
        precision (str): The precision of the duration. Must be one of ("year", "month", "week", "day").
            For example, a death record specifying that the age of the deceased was "4 2/3 annorum"
            should be given a precision of "month".
        confidence (str): Confidence level (accuracy) of the duration. Must be one of "normal" or "low".
            Confidence is independent of precision: the priest may have written "4 2/3 annorum" (i.e. a
            precision of "month"), but if sloppy penmanship makes it hard to tell whether the number is
            a "4" or a "9", then the confidence level is only accurate to within 5 years.
        year_day_ambiguity (bool): Indicates if there is a unit ambiguity between days and years.
            This happens for some death records where the pre-printed column heading for age is "dies
            vitae", but where a number was entered without units and there is a chance that the entered
            number represents years instead of days (or vice versa). Precision should correspond to the
            most likely unit based on other evidence in the record.

    Args:
        duration_list (list of int): The duration of the interval expressed as a list of the form
            (years, months, weeks, days), where each entry is an integer.
        precision (str or None): The precision of the duration (see Attributes above). If None, then
            the precision will be inferred from the duration_list.
    """
    def __init__(self, duration_list=None, precision=None, confidence=None, year_day_ambiguity=None):
        self.duration = datetime.timedelta(weeks=duration_list[2],
                                           days=365*duration_list[0]+30*duration_list[1]+duration_list[3])
        if precision is None:
            # find last non-zero element of reversed duration_list
            index = next(x for x, val in enumerate(reversed(duration_list)) if val > 0)
            self.precision = ["day", "week", "month", "year"][index]
        else:
            self.precision = precision

        self.confidence = confidence
        self.year_day_ambiguity = year_day_ambiguity

    def match_ll(self, query):
        pass


class Source:
    """A reference to a source description.

    Attributes:
        repository (str): Identification of repository where the record is located.
        volume (str): The repository's identifier for the volume in which the source record is located.
        page_number (int): The page number on which the record is located.
        entry_number (int): The entry number of the record.
        image_file (str): The image file of the pages on which the source record is located.
    """
    def __init__(self, repository=None, volume=None, page_number=None, entry_number=None,
                 image_file=None):
        self.repository = repository
        self.volume = volume
        self.page_number = page_number
        self.entry_number = entry_number
        self.image_file = image_file

    def __repr__(self):
        return '{}, volume {}, page {}, entry {} ({})'.format(self.repository,
                                                              self.volume,
                                                              self.page_number,
                                                              self.entry_number,
                                                              self.image_file)
