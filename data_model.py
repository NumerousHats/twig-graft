"""Module containing classes that define a genealogical data model.

This model is a greatly simplified and somewhat modified version of Gedcom X. The primary differences are
as follows:

- There are no Events, only Facts
- The Date model has been modified
- The Name class has been grossly simplified
- The Source model has been modified
- Agents and Locations are not implemented

"""


class Conclusion:
    """Abstract class for a basic genealogical data item.

    Attributes:
        sources (list of Source): Sources related to this conclusion.
        notes (list of str): Notes about this conclusion.
        confidence (str): A confidence level for this conclusion.

    """

    def __init__(self, sources, notes, confidence):
        self.sources = sources
        self.notes = notes
        self.confidence = confidence


class Fact(Conclusion):
    """A data item that is presumed to be true about a specific subject.

    Subjects are typically a person or relationship. In contrast to the full Gedcom X, there is no
    distinction between Facts and Events.

    Attributes:
        fact_type (str): The type of Fact. Should correspond to one of the Gedcom X Known Fact Types.
        date (Date): The date or date range associated with the fact. Date ranges are used to denote uncertainties.
        age (Duration): The age of the individual at the time of the Fact.
        cause (str): A cause associated with the Fact (typically a cause of death).
        house_number (str): The house number where this Fact took place.
    """

    def __init__(self, fact_type, sources, date=None, age=None, cause=None, house_number=None,
                 notes=None, confidence=None):
        super().__init__(sources, notes, confidence)
        self.fact_type = fact_type
        self.date = date


class Name (Conclusion):
    """Defines a name of a person.

    Attributes:
        name_type (str): Name type, one of "birth", "married", "also_known_as", etc.
        name_parts (dict): Identified name parts. Keys are used to identify the name part (must be one
            of "prefix", "suffix", "given", or "surname"), and the values are the actual names.
        date (Date): The date range of applicability of the name.

    """

    def match_ll(self, query):
        pass


class Person (Conclusion):
    """A description of a person.

    Attributes:
        names (list of Name): The names of the person.
        gender (str): The sex of the person.
        facts (list of Fact): Facts regarding the person.

    """

    def name_match_ll(self, query_name, date):
        pass


class Relationship (Conclusion):
    """Attributes associated with a relationship between two Persons.

    Attributes:
        relationship_type (str): The type of relationship. Must be either "spouse" or "parent-child".
        facts (list of Fact): Fact(s) relating to the relationship, generally a birth/baptism or marriage.

    """

    def match_ll(self, query):
        pass


class Date:
    """A date or date range of a genealogical event/fact.

    date (datetime.date): A datetime.date object or a list of two datetime.date objects (or None,
        see below). In the former case, it represents a specific day (to the stated
        confidence level). In the latter case, it represents a date range, with the
        first date representing the start and the second, the end of the rage. If the first
        list item is None, then the range is open-ended from below. If the second list item is None,
        then the range is open-ended from above.  Specific years or months should be represented as
        a range (e.g. date = ["1898-01-01"; end_date ="1898-12-31"]).
    confidence (str): The confidence level of the date.

    """

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

    """

    def match_ll(self, query):
        pass


class Source(object):
    """A reference to a source description.

    Attributes:
        repository (str): Identification of repository where the record is located.
        volume (str): The repository's identifier for the volume in which the source record is located.
        page_number (int): The page number on which the record is located.
        entry_number (int): The entry number of the record.
        image_file_name (str): The image file of the pages on which the source record is located.

    """
    def __init__(self, repository=None, volume=None, page_number=None, entry_number=None,
                 image_file_name=None):
        pass
