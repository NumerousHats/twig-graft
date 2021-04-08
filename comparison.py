import math
from data_model import *


def thing_match(thing1, thing2, total_count, total_comp, increment=1.0):
    if thing1 is None or thing2 is None:
        return None, total_count, total_comp

    if thing1 == thing2:
        return True, total_count+increment, total_comp+1
    else:
        return False, total_count, total_comp+1


def compare_name_part(name1: Name, name2: Name, part: str):
    if not name1 or not name2:
        return None

    if part == "given":
        standard1 = name1.standard_given
        standard2 = name2.standard_given
    elif part == "surname":
        standard1 = name1.standard_surname
        standard2 = name2.standard_surname
    else:
        raise ValueError

    raw1 = name1.name_parts.get(part)
    raw2 = name2.name_parts.get(part)

    if standard1 and standard2:
        if standard1 == standard2:
            return True
        else:
            return False
    else:
        # TODO do fuzzy matches on raw names
        return None


def compare_fullname(name1: Name, name2: Name, disqualify_surname_mismatch=False):
    """Compare both given and surname for a pair of Names.

    Args:
        name1: The first Name
        name2: The second Name
        disqualify_surname_mismatch: if True, cause surname mismatch to return False

    Returns:
        True if there is a match on both name parts, False if it is impossible that the two Names belong to the
        same person-in-real-life, and None otherwise.

    """
    matches = 0
    given_comp = compare_name_part(name1, name2, "given")
    surname_comp = compare_name_part(name1, name2, "surname")

    if given_comp is not None:
        if given_comp:
            matches += 1
        else:
            return False

    if surname_comp is not None:
        if disqualify_surname_mismatch and not surname_comp:
            return False
        if surname_comp:
            matches += 1

    if matches == 2:
        return True
    else:
        return None


def name_match(names1, names2):
    matches = 0
    comparisons = 0

    if not names1 or not names2:
        return 0, 0

    birth1 = names1.pop("birth", [None])[0]
    birth2 = names2.pop("birth", [None])[0]

    if birth1 and birth2:
        comp = compare_fullname(birth1, birth2, disqualify_surname_mismatch=True)
        comparisons += 1
        if comp:
            matches += 1
        elif comp is False:
            return -1, 0

    names1list = [item for sublist in [names1[k] for k in ("married", "unknown") if k in names1] for item in sublist]
    names2list = [item for sublist in [names2[k] for k in ("married", "unknown") if k in names2] for item in sublist]

    for name1 in names1list:
        for name2 in names2list:
            comp = compare_fullname(name1, name2)
            comparisons += 1
            if comp:
                matches += 1
            elif comp is False:
                return -1, 0

    if birth1:
        for name2 in names2list:
            comp = compare_fullname(birth1, name2)
            comparisons += 1
            if comp:
                matches += 1
            elif comp is False:
                return -1, 0

    if birth2:
        for name1 in names1list:
            comp = compare_fullname(name1, birth2)
            comparisons += 1
            if comp:
                matches += 1
            elif comp is False:
                return -1, 0

    return matches, comparisons


def date_overlap(date1: Date, date2: Date):
    """Determine if two Date objects could possibly represent the same event, i.e. their intervals have
        a non-empty intersection.
    """

    return date1.start - date1.accuracy <= date2.end + date2.accuracy and \
           date2.start - date2.accuracy <= date1.end + date1.accuracy


def datelist_overlap(datelist1, datelist2):
    """Determine if two lists of Date objects could possibly represent the same event, i.e. at least one interval
        in datelist1 has a non-empty intersection with at least one interval in datelist2."""

    for date1 in datelist1:
        for date2 in datelist2:
            if date_overlap(date1, date2):
                return True

    return False


def earliest(datelist):
    out = Date("2020-01-01")
    for date in datelist:
        if date.start < out.start:
            out = date
    return out


def latest(datelist):
    out = Date("1492-01-01")
    for date in datelist:
        if date.end > out.end:
            out = date
    return out


def birth_death_match(person1: Person, person2: Person):
    birth1 = person1.birth_date()
    birth2 = person2.birth_date()
    death1 = person1.death_date()
    death2 = person2.death_date()

    comparisons = 0
    matches = 0

    if birth1 and birth2:
        comparisons += 1
        if datelist_overlap(birth1, birth2):
            matches += 1
        else:
            return -1, 0

    if death1 and death2:
        comparisons += 1
        if datelist_overlap(death1, death2):
            matches += 1
        else:
            return -1, 0

    if birth1 and death2:
        comparisons += 1
        if earliest(birth1).is_before(latest(death2)):
            matches += 1
        else:
            return -1, 0

    if birth2 and death1:
        comparisons += 1
        if earliest(birth2).is_before(latest(death1)):
            matches += 1
        else:
            return -1, 0

    return matches, comparisons


def compare_location(loc1: Location, loc2: Location):
    """Examine two Locations for possible consistency.

    Returns:
        True if the locations are consistent, False if it is impossible that the two are the same.
    """
    if loc1.alt_village != loc2.alt_village:
        return False

    matching_values = [value for value in [loc1.house_number, loc1.alt_house_number] if value in
                                                                         [loc2.house_number, loc2.alt_house_number]
                                                                         and value is not None]
    if matching_values:
        return True
    else:
        return False


def location_match(locations1, locations2):
    """Examine two lists of locations for consistency.
    """
    matches = 0

    if locations1 and locations2:
        for loc1 in locations1:
            for loc2 in locations2:
                if location_match(loc1, loc2):
                    matches += 1

    return matches


def compare_person(person1, person2, graph=None):
    """Determine if two Person objects could be the same person-in-real-life in the context of a relationship graph.
    """
    logger = logging.getLogger(__name__)
    logger.debug("comparing %s to %s", person1, person2)

    if person1.has_fact("Stillbirth") or person2.has_fact("Stillbirth"):
        logger.debug("Stillbirth")
        return 0, None, None

    if person1.gender != person2.gender:
        logger.debug("Gender mismatch")
        return 0, None, None

    name_matches, name_comparisons = name_match(person1.get_names(), person2.get_names())
    if name_matches == -1:
        logger.debug("Name mismatch")
        return 0, None, None

    date_matches, date_comparisons = birth_death_match(person1, person2)
    if date_matches == -1:
        logger.debug("Date mismatch")
        return 0, None, None

    if person1.has_fact("Coelebs"):
        if graph:
            relations = graph.direct_relations(person2.identifier)
        else:
            relations = {}
        names = person2.get_names()
        if "spouses" in relations or "married" in names:
            logger.debug("Inconsistent marital status for %s and %s", person1, person2)
            return 0, None, None

    if person2.has_fact("Coelebs"):
        relations = graph.direct_relations(person1.identifier)
        names = person1.get_names()
        if "spouses" in relations or "married" in names:
            logger.debug("Inconsistent marital status for %s and %s", person1, person2)
            return 0, None, None

    return name_matches, date_matches, location_match(person1.get_locations(), person2.get_locations())


def person_mismatch(person1, person2):
    """Return True if two Person objects cannot be the same person-in-real-life.
    """
    logger = logging.getLogger(__name__)
    logger.debug("comparing %s to %s for mismatch", person1, person2)

    if person1.has_fact("Stillbirth") or person2.has_fact("Stillbirth"):
        logger.debug("Stillbirth")
        return True

    if person1.gender != person2.gender:
        logger.debug("Gender mismatch")
        return True

    name_matches, name_comparisons = name_match(person1.get_names(), person2.get_names())
    if name_matches == -1:
        logger.debug("Name mismatch")
        return True

    date_matches, date_comparisons = birth_death_match(person1, person2)
    if date_matches == -1:
        logger.debug("Date mismatch")
        return True

    return False
