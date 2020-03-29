"""Module containing classes that define a genealogical data model.

This model is loosely based on a Gedcom X conceptual model, but has greatly simplified and modified.
The primary differences are as follows:

- There are no Events, only Facts
- The Date model has been modified
- The Name class has been grossly simplified
- The Source model has been modified
- Locations are house-number-centric
- Agents are not implemented

"""

import datetime


class Conclusion:
    """Abstract class for a basic genealogical data item.

    Attributes:
        sources (list of Source): Sources related to this conclusion.
        notes (list of str): Notes about this conclusion.
        confidence (str): A confidence level for this conclusion.
    """
    def __init__(self, sources=None, notes=None, confidence=None):
        self.sources = sources
        self.notes = notes
        self.confidence = confidence


class Fact(Conclusion):
    """A data item that is presumed to be true about a specific subject.

    Subjects are typically a person or relationship. In contrast to the full Gedcom X, there is no
    distinction between Facts and Events. For occurrences that involve more than one Person (e.g. marriages),


    Attributes:
        fact_type (str): The type of Fact. Should correspond to one of the Gedcom X Known Fact Types.
        date (Date): The date or date range associated with the fact. Date ranges are used to
            denote precision (e.g. an event that took place in 1862 but for which we do not have a recorded
            month or year should have a Date that spans the range 1862-01-01 to 1862-12-31). Issues related
            to accuracy (e.g. handwriting issues, possible typos) should be indicated through
            Conclusion.confidence.
        age (Duration): The age of the individual at the time of the Fact.
        locations (Location): The house number(s) (and possibly an alternate village) associated with this
            Fact took place.
    """
    def __init__(self, fact_type=None, date=None, age=None, locations=None,
                 sources=None, notes=None, confidence=None):
        super().__init__(sources=sources, notes=notes, confidence=confidence)
        self.fact_type = fact_type
        self.date = date
        self.age = age
        self.locations = locations


class Name (Conclusion):
    """Defines a name of a person.

    Attributes:
        name_type (str): Name type, one of "birth", "married", "also_known_as", etc.
        name_parts (dict): Identified name parts. Keys are used to identify the name part (must be one
            of "prefix", "suffix", "given", or "surname"), and the values are the actual names.
        date (Date): The date range of applicability of the name.
    """
    def __init__(self, name_type=None, name_parts=None, date=None,
                 sources=None, notes=None, confidence=None):
        super().__init__(sources=sources, notes=notes, confidence=confidence)
        self.name_type = name_type
        self.name_parts = name_parts
        self.date = date

    def match_ll(self, query):
        pass


class Person (Conclusion):
    """A description of a person.

    Attributes:
        names (list of Name): The names of the person.
        gender (str): The sex of the person.
        facts (list of Fact): Facts regarding the person.
    """
    def __init__(self, names=None, gender=None, facts=None,
                 sources=None, notes=None, confidence=None):
        super().__init__(sources=sources, notes=notes, confidence=confidence)
        self.names = names
        self.gender = gender
        self.facts = facts

    def name_match_ll(self, query_name, date):
        pass


class Relationship (Conclusion):
    """Attributes associated with a relationship between two Persons.

    Attributes:
        relationship_type (str): The type of relationship. Must be either "spouse" or "parent-child".
        facts (list of Fact): Fact(s) relating to the relationship, generally a birth/baptism or marriage.
    """
    def __init__(self, relationship_type=None, facts=None,
                 sources=None, notes=None, confidence=None):
        super().__init__(sources=sources, notes=notes, confidence=confidence)
        self.relationship_type = relationship_type
        self.facts = facts

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
        end_date (str): Should be an ISO-format date string (YYYY-MM-DD) representing the end date of
            the interval. If the date range is to be open-ended, then it should be passed
            an empty string.
        confidence (str): The confidence level of the date.
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
        precision (int): The precision of the duration in units of days. For example, should be 30
            for intervals specified to within one month (e.g. a death record specifying that the age
            of the deceased was "10 2/12 annorum").
        confidence (str): Confidence level (accuracy) of the duration. Must be one of "normal" or "low".
            Confidence is independent of precision: the priest may have indicated the age to within one
            month, but sloppy penmanship makes it hard to tell if he wrote a "4" or a "9".
        year_day_ambiguity (bool): Indicates if there is a unit ambiguity between days and years.
            This happens for some death records where the pre-printed column heading for age is "dies
            vitae", but where a number was entered without units and there is a chance that the entered
            number represents years instead of days (or vice versa). Precision should correspond to the
            most likely unit based on other evidence in the record.

    Args:
        duration_list (list of int): The duration of the interval expressed as a list of the form
            (years, months, weeks, days), where each entry is an integer.
    """
    def __init__(self, duration_list=None, precision=None, confidence=None, year_day_ambiguity=None):
        self.duration = datetime.timedelta(weeks=duration_list[2],
                                           days=365*duration_list[0]+30*duration_list[1]+duration_list[3])
        self.precision = precision
        self.confidence = confidence
        self.year_day_ambiguity = year_day_ambiguity

    def match_ll(self, query):
        pass


class Source(object):
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
