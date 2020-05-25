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


def thing_match(thing1, thing2, total_count, total_comp):
    if thing1 is None or thing2 is None:
        return 0, total_count, total_comp

    if thing1 == thing2:
        return 1, total_count+1, total_comp+1
    else:
        return None, total_count, total_comp+1


def compare_person(person1: Person, person2: Person):
    """Calculate the posterior probability that two Person objects are the same person-in-real-life.
    """
    matches = 0
    comparisons = 0

    val, matches, comparisons = thing_match(person1.gender, person2.gender, matches, comparisons)
    if val is None:
        return 0

    birth_name1 = [x for x in person1.names if x.name_type == "birth"][0]
    birth_name2 = [x for x in person2.names if x.name_type == "birth"][0]

    val, matches, comparisons = thing_match(birth_name1.standard_given,
                                            birth_name2.standard_given, matches, comparisons)
    if val is None:
        return 0

    val, matches, comparisons = thing_match(birth_name1.standard_surname,
                                            birth_name2.standard_surname, matches, comparisons)
    if val is None:
        return 0

    # deal with "unknown" name type

    # points of comparison: gender, names, lifespan, marital status, associated house numbers
