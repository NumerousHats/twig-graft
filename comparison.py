from data_model import *


def compare_date(date1, date2):
    """Compare two Date objects.

    This function is a total mess and not usable as it is currently written.

    For degenerate ranges (i.e. start == end), the situation is trivial: the Dates are either the same,
    or one is before the other. For non-degenerate ranges, there seem to be 11 possibilities for how
    they could relate to each other. If the ranges match exactly or are non-overlapping, then the
    situation is again similar to the degenerate case. For the remaining 8 possibilities, classifying them into
    "before" or "after" is not at all simple, and it's not clear what this function should return.

    Perhaps this should be split into multiple functions: one to determine whether there is overlap, one to determine
    if there is strict equality or ordering, and one to determine the direction of "asymmetric overhang".

    Args:
        date1 (Date): The first Date to compare.
        date2 (Date): The second Date to compare.

    Returns:
        Good question.
    """
    if type(date1) is not Date or type(date2) is not Date:
        raise TypeError("arguments to compare_data must be Date objects")

    # TODO this needs to be seriously re-thunk
    if date1.start == date2.start and date1.end == date2.end:
        return 0
    if date1.start < date2.start:
        if date1.end < date2.start:
            return 2
        else:
            return 1
    else:
        pass


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
        for name1 in names1list:
            comp = compare_fullname(name1, birth2)
            comparisons += 1
            if comp:
                matches += 1
            elif comp is False:
                return -1, 0

    if birth2:
        for name2 in names2list:
            comp = compare_fullname(birth1, name2)
            comparisons += 1
            if comp:
                matches += 1
            elif comp is False:
                return -1, 0

    return matches, comparisons


def compare_person(person1: Person, person2: Person):
    """Determine if two Person objects could be the same person-in-real-life.
    """
    logger = logging.getLogger(__name__)
    matches = 0
    comparisons = 0
    logger.debug("comparing %s to %s", person1, person2)

    if person1.has_fact("Stillbirth") or person2.has_fact("Stillbirth"):
        logger.debug("Stillbirth")
        return 0, None

    if person1.gender != person2.gender:
        logger.debug("Gender mismatch")
        return 0, None

    name_matches, name_comparisons = name_match(person1.get_names(), person2.get_names())
    if name_matches == -1:
        logger.debug("Name mismatch")
        return 0, None
    matches += name_matches
    comparisons += name_comparisons

    return matches, comparisons

    # TODO points of comparison: lifespan, marital status, associated house numbers
