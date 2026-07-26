import networkx as nx

from data_model import Person, Name, Fact, Date, Relationship
from plausibility import score_proposal, MIN_PARENT_CHILD_GAP_ERROR, MIN_PARENT_CHILD_GAP_WARNING, \
    MAX_SPOUSE_GAP_WARNING, MAX_SPOUSE_GAP_ERROR


def make_person(given="John", surname="Doe", gender="m", birth_year=None, coelebs=False):
    name = Name("birth", {"given": given, "surname": surname})
    facts = []
    if birth_year is not None:
        facts.append(Fact("Birth", date=Date("{}-01-01".format(birth_year), "{}-12-31".format(birth_year))))
    if coelebs:
        facts.append(Fact("Coelebs"))
    return Person(names=[name], gender=gender, facts=facts or None)


def add_person(graph, person):
    graph.add_node(person.identifier, person=person)
    return person.identifier


def add_relation(graph, from_id, to_id, rel_type):
    relation = Relationship(from_id, to_id, rel_type)
    graph.add_edge(from_id, to_id, relation=relation)


def test_no_warnings_clean_proposal():
    g1 = nx.DiGraph()
    g2 = nx.DiGraph()

    parent1 = make_person(birth_year=1900)
    child1 = make_person(birth_year=1925)
    pid1 = add_person(g1, parent1)
    cid1 = add_person(g1, child1)
    add_relation(g1, pid1, cid1, "parent-child")

    parent2 = make_person(birth_year=1900)
    child2 = make_person(birth_year=1925)
    pid2 = add_person(g2, parent2)
    cid2 = add_person(g2, child2)
    add_relation(g2, pid2, cid2, "parent-child")

    mapping = {pid1: pid2, cid1: cid2}
    result = score_proposal(g1, g2, mapping)

    assert result.warnings == []
    assert result.score == 1.0


def test_parent_too_young_error():
    g1 = nx.DiGraph()
    g2 = nx.DiGraph()

    parent1 = make_person(birth_year=1900)
    child1 = make_person(birth_year=1908)  # 8 year gap -> error
    pid1 = add_person(g1, parent1)
    cid1 = add_person(g1, child1)
    add_relation(g1, pid1, cid1, "parent-child")

    other = make_person(birth_year=1908)
    oid = add_person(g2, other)

    mapping = {cid1: oid}
    result = score_proposal(g1, g2, mapping)

    assert any(w.check == "parent_age_gap" and w.severity == "error" for w in result.warnings)
    assert result.score < 1.0


def test_parent_borderline_warning():
    g1 = nx.DiGraph()
    g2 = nx.DiGraph()

    parent1 = make_person(birth_year=1900)
    child1 = make_person(birth_year=1914)  # 14 year gap -> warning, not error
    pid1 = add_person(g1, parent1)
    cid1 = add_person(g1, child1)
    add_relation(g1, pid1, cid1, "parent-child")

    other = make_person(birth_year=1914)
    oid = add_person(g2, other)

    mapping = {cid1: oid}
    result = score_proposal(g1, g2, mapping)

    assert any(w.check == "parent_age_gap" and w.severity == "warning" for w in result.warnings)
    assert not any(w.check == "parent_age_gap" and w.severity == "error" for w in result.warnings)


def test_parent_unknown_dates_skipped():
    g1 = nx.DiGraph()
    g2 = nx.DiGraph()

    parent1 = make_person()  # no birth date
    child1 = make_person(birth_year=1925)
    pid1 = add_person(g1, parent1)
    cid1 = add_person(g1, child1)
    add_relation(g1, pid1, cid1, "parent-child")

    other = make_person(birth_year=1925)
    oid = add_person(g2, other)

    mapping = {cid1: oid}
    result = score_proposal(g1, g2, mapping)

    assert result.warnings == []
    assert result.score == 1.0


def test_spouse_age_gap_large_error():
    g1 = nx.DiGraph()
    g2 = nx.DiGraph()

    husband1 = make_person(gender="m", birth_year=1845)
    wife1 = make_person(gender="f", birth_year=1920)  # 75 year gap -> error
    hid1 = add_person(g1, husband1)
    wid1 = add_person(g1, wife1)
    add_relation(g1, hid1, wid1, "spouse")

    other = make_person(gender="f", birth_year=1920)
    oid = add_person(g2, other)

    mapping = {wid1: oid}
    result = score_proposal(g1, g2, mapping)

    assert any(w.check == "spouse_age_gap" and w.severity == "error" for w in result.warnings)


def test_spouse_age_gap_moderate_no_warning():
    g1 = nx.DiGraph()
    g2 = nx.DiGraph()

    husband1 = make_person(gender="m", birth_year=1880)
    wife1 = make_person(gender="f", birth_year=1925)  # 45 year gap -> below warning threshold
    hid1 = add_person(g1, husband1)
    wid1 = add_person(g1, wife1)
    add_relation(g1, hid1, wid1, "spouse")

    other = make_person(gender="f", birth_year=1925)
    oid = add_person(g2, other)

    mapping = {wid1: oid}
    result = score_proposal(g1, g2, mapping)

    assert not any(w.check == "spouse_age_gap" for w in result.warnings)
    assert result.score == 1.0


def test_coelebs_inconsistency():
    g1 = nx.DiGraph()
    g2 = nx.DiGraph()

    person1 = make_person(coelebs=True)
    pid1 = add_person(g1, person1)

    person2 = make_person()
    spouse2 = make_person(gender="f")
    pid2 = add_person(g2, person2)
    sid2 = add_person(g2, spouse2)
    add_relation(g2, pid2, sid2, "spouse")

    mapping = {pid1: pid2}
    result = score_proposal(g1, g2, mapping)

    assert any(w.check == "coelebs" for w in result.warnings)


def test_empty_mapping():
    g1 = nx.DiGraph()
    g2 = nx.DiGraph()
    result = score_proposal(g1, g2, {})

    assert result.warnings == []
    assert result.score == 1.0


def test_multiple_warnings_decrement_score():
    g1 = nx.DiGraph()
    g2 = nx.DiGraph()

    parent1 = make_person(birth_year=1900)
    child1 = make_person(birth_year=1913)  # warning-level gap
    pid1 = add_person(g1, parent1)
    cid1 = add_person(g1, child1)
    add_relation(g1, pid1, cid1, "parent-child")

    husband1 = make_person(gender="m", birth_year=1850)
    wife1 = make_person(gender="f", birth_year=1913)
    hid1 = add_person(g1, husband1)
    add_relation(g1, hid1, cid1, "spouse")

    other_child = make_person(birth_year=1913)
    oid = add_person(g2, other_child)

    mapping = {cid1: oid}
    result = score_proposal(g1, g2, mapping)

    assert len(result.warnings) >= 2
    assert result.score < 1.0 - 0.2  # more than one warning's worth of penalty


def test_score_clamping_does_not_go_negative():
    g1 = nx.DiGraph()
    g2 = nx.DiGraph()

    # Build several parent-child pairs all with impossible age gaps, mapped to distinct nodes in g2,
    # so that many "error" warnings accumulate.
    mapping = {}
    for i in range(5):
        parent = make_person(birth_year=1900)
        child = make_person(birth_year=1900 + i)  # 0-4 year gap, well below error threshold
        pid = add_person(g1, parent)
        cid = add_person(g1, child)
        add_relation(g1, pid, cid, "parent-child")

        other = make_person(birth_year=1900 + i)
        oid = add_person(g2, other)
        mapping[cid] = oid

    result = score_proposal(g1, g2, mapping)

    assert result.score == 0.0
    assert all(w.severity == "error" for w in result.warnings if w.check == "parent_age_gap")


def make_person_wide(given="John", surname="Doe", gender="m", birth_start=None, birth_end=None, coelebs=False):
    name = Name("birth", {"given": given, "surname": surname})
    facts = []
    if birth_start is not None and birth_end is not None:
        facts.append(Fact("Birth", date=Date(birth_start, birth_end)))
    if coelebs:
        facts.append(Fact("Coelebs"))
    return Person(names=[name], gender=gender, facts=facts or None)


def test_parent_child_wide_range_some_endpoints_plausible():
    """Parent birth range spans 1880-1900; child birth range spans 1920-1925.
    The tightest gap (youngest parent vs. oldest child) is 1920-1900 = 20y, which is plausible.
    But the widest gap (oldest parent vs. youngest child) is 1925-1880 = 45y.
    Since *some* endpoint combo is plausible, no warning should fire."""
    g1 = nx.DiGraph()
    g2 = nx.DiGraph()

    parent1 = make_person_wide(birth_start="1880-01-01", birth_end="1900-12-31")
    child1 = make_person_wide(birth_start="1920-01-01", birth_end="1925-12-31")
    pid1 = add_person(g1, parent1)
    cid1 = add_person(g1, child1)
    add_relation(g1, pid1, cid1, "parent-child")

    other = make_person_wide(birth_start="1920-01-01", birth_end="1925-12-31")
    oid = add_person(g2, other)

    mapping = {cid1: oid}
    result = score_proposal(g1, g2, mapping)

    assert not any(w.check == "parent_age_gap" for w in result.warnings)


def test_parent_child_wide_range_all_endpoints_implausible():
    """Parent birth range spans 1905-1910; child birth range spans 1910-1915.
    All four gaps are 0-10 years, well below 12y error threshold. Should flag error."""
    g1 = nx.DiGraph()
    g2 = nx.DiGraph()

    parent1 = make_person_wide(birth_start="1905-01-01", birth_end="1910-12-31")
    child1 = make_person_wide(birth_start="1910-01-01", birth_end="1915-12-31")
    pid1 = add_person(g1, parent1)
    cid1 = add_person(g1, child1)
    add_relation(g1, pid1, cid1, "parent-child")

    other = make_person_wide(birth_start="1910-01-01", birth_end="1915-12-31")
    oid = add_person(g2, other)

    mapping = {cid1: oid}
    result = score_proposal(g1, g2, mapping)

    assert any(w.check == "parent_age_gap" and w.severity == "error" for w in result.warnings)


def test_parent_child_wide_range_spans_warning_threshold():
    """Parent birth 1895-1905; child birth 1915-1925.
    Gaps: min = 1915-1905 = 10y (error), max = 1925-1895 = 30y (plausible).
    Since some endpoints are plausible, no warning should fire."""
    g1 = nx.DiGraph()
    g2 = nx.DiGraph()

    parent1 = make_person_wide(birth_start="1895-01-01", birth_end="1905-12-31")
    child1 = make_person_wide(birth_start="1915-01-01", birth_end="1925-12-31")
    pid1 = add_person(g1, parent1)
    cid1 = add_person(g1, child1)
    add_relation(g1, pid1, cid1, "parent-child")

    other = make_person_wide(birth_start="1915-01-01", birth_end="1925-12-31")
    oid = add_person(g2, other)

    mapping = {cid1: oid}
    result = score_proposal(g1, g2, mapping)

    assert not any(w.check == "parent_age_gap" for w in result.warnings)


def test_spouse_wide_range_some_endpoints_plausible():
    """Husband birth 1870-1890; wife birth 1920-1930.
    Gaps: min = 1920-1890 = 30y (plausible), max = 1930-1870 = 60y.
    Since some endpoints are within the plausible range, no warning should fire."""
    g1 = nx.DiGraph()
    g2 = nx.DiGraph()

    husband1 = make_person_wide(gender="m", birth_start="1870-01-01", birth_end="1890-12-31")
    wife1 = make_person_wide(gender="f", birth_start="1920-01-01", birth_end="1930-12-31")
    hid1 = add_person(g1, husband1)
    wid1 = add_person(g1, wife1)
    add_relation(g1, hid1, wid1, "spouse")

    other = make_person_wide(gender="f", birth_start="1920-01-01", birth_end="1930-12-31")
    oid = add_person(g2, other)

    mapping = {wid1: oid}
    result = score_proposal(g1, g2, mapping)

    assert not any(w.check == "spouse_age_gap" for w in result.warnings)


def test_spouse_wide_range_all_endpoints_implausible():
    """Husband birth 1835-1845; wife birth 1920-1930.
    All gaps: 75-95 years, all above 70y error threshold. Should flag error."""
    g1 = nx.DiGraph()
    g2 = nx.DiGraph()

    husband1 = make_person_wide(gender="m", birth_start="1835-01-01", birth_end="1845-12-31")
    wife1 = make_person_wide(gender="f", birth_start="1920-01-01", birth_end="1930-12-31")
    hid1 = add_person(g1, husband1)
    wid1 = add_person(g1, wife1)
    add_relation(g1, hid1, wid1, "spouse")

    other = make_person_wide(gender="f", birth_start="1920-01-01", birth_end="1930-12-31")
    oid = add_person(g2, other)

    mapping = {wid1: oid}
    result = score_proposal(g1, g2, mapping)

    assert any(w.check == "spouse_age_gap" and w.severity == "error" for w in result.warnings)


def test_spouse_wide_range_spans_warning_threshold():
    """Husband birth 1880-1895; wife birth 1920-1930.
    Gaps: 25-60y. Some < 50y (plausible), some > 50y. No warning should fire."""
    g1 = nx.DiGraph()
    g2 = nx.DiGraph()

    husband1 = make_person_wide(gender="m", birth_start="1880-01-01", birth_end="1895-12-31")
    wife1 = make_person_wide(gender="f", birth_start="1920-01-01", birth_end="1930-12-31")
    hid1 = add_person(g1, husband1)
    wid1 = add_person(g1, wife1)
    add_relation(g1, hid1, wid1, "spouse")

    other = make_person_wide(gender="f", birth_start="1920-01-01", birth_end="1930-12-31")
    oid = add_person(g2, other)

    mapping = {wid1: oid}
    result = score_proposal(g1, g2, mapping)

    assert not any(w.check == "spouse_age_gap" for w in result.warnings)
