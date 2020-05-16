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


