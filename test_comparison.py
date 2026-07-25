from datetime import timedelta
from data_model import *
from comparison import (compare_name_part, compare_fullname, name_match,
                        date_overlap, datelist_overlap, birth_death_match,
                        person_mismatch, compare_person,
                        compare_location, location_match)


# --- helpers ---

def make_person(given, surname, gender="m", birth_date=None, death_date=None,
                name_type="birth", thesaurus=None, std_given=None, std_surname=None):
    name = Name(name_type=name_type, name_parts={"given": given, "surname": surname},
                thesaurus=thesaurus)
    if std_given:
        name.standard_given = std_given
    if std_surname:
        name.standard_surname = std_surname
    facts = []
    if birth_date:
        facts.append(Fact("Birth", date=birth_date))
    if death_date:
        facts.append(Fact("Death", date=death_date))
    return Person(names=[name], gender=gender, facts=facts or None)


def make_location(house_number=None, alt_house_number=None, alt_village=None):
    return Location(house_number=house_number, alt_house_number=alt_house_number,
                    alt_village=alt_village)


# --- compare_name_part ---

class TestCompareNamePart:
    def test_standardized_match(self):
        n1 = Name("birth", {"given": "Jon", "surname": "Doe"}, thesaurus=None)
        n2 = Name("birth", {"given": "John", "surname": "Doe"}, thesaurus=None)
        n1.standard_given = "John"
        n2.standard_given = "John"
        assert compare_name_part(n1, n2, "given") is True

    def test_standardized_mismatch(self):
        n1 = Name("birth", {"given": "Jon", "surname": "Smith"}, thesaurus=None)
        n2 = Name("birth", {"given": "John", "surname": "Doe"}, thesaurus=None)
        n1.standard_surname = "Smith"
        n2.standard_surname = "Doe"
        assert compare_name_part(n1, n2, "surname") is False

    def test_missing_standardized_returns_none(self):
        n1 = Name("birth", {"given": "Jon"}, thesaurus=None)
        n2 = Name("birth", {"given": "John"}, thesaurus=None)
        assert compare_name_part(n1, n2, "given") is None

    def test_invalid_part_raises(self):
        n1 = Name("birth", {"given": "Jon"}, thesaurus=None)
        n2 = Name("birth", {"given": "John"}, thesaurus=None)
        import pytest
        with pytest.raises(ValueError):
            compare_name_part(n1, n2, "prefix")


# --- compare_fullname ---

class TestCompareFullname:
    def test_both_match(self):
        n1 = Name("birth", {"given": "John", "surname": "Doe"})
        n1.standard_given = "John"
        n1.standard_surname = "Doe"
        n2 = Name("birth", {"given": "John", "surname": "Doe"})
        n2.standard_given = "John"
        n2.standard_surname = "Doe"
        assert compare_fullname(n1, n2) is True

    def test_given_mismatches(self):
        n1 = Name("birth", {"given": "John", "surname": "Doe"})
        n1.standard_given = "John"
        n1.standard_surname = "Doe"
        n2 = Name("birth", {"given": "Jane", "surname": "Doe"})
        n2.standard_given = "Jane"
        n2.standard_surname = "Doe"
        assert compare_fullname(n1, n2) is False

    def test_surname_mismatch_disqualify(self):
        n1 = Name("birth", {"given": "John", "surname": "Doe"})
        n1.standard_given = "John"
        n1.standard_surname = "Doe"
        n2 = Name("birth", {"given": "John", "surname": "Smith"})
        n2.standard_given = "John"
        n2.standard_surname = "Smith"
        assert compare_fullname(n1, n2, disqualify_surname_mismatch=True) is False

    def test_surname_mismatch_no_disqualify(self):
        n1 = Name("birth", {"given": "John", "surname": "Doe"})
        n1.standard_given = "John"
        n1.standard_surname = "Doe"
        n2 = Name("birth", {"given": "John", "surname": "Smith"})
        n2.standard_given = "John"
        n2.standard_surname = "Smith"
        # given matches, surname mismatches but not disqualifying → inconclusive
        result = compare_fullname(n1, n2, disqualify_surname_mismatch=False)
        assert result is None

    def test_inconclusive_when_missing_standardized(self):
        n1 = Name("birth", {"given": "John"})
        n2 = Name("birth", {"given": "John"})
        result = compare_fullname(n1, n2)
        assert result is None


# --- name_match ---

class TestNameMatch:
    def test_birth_name_mismatch(self):
        p1 = make_person("John", "Doe", std_given="John", std_surname="Doe")
        p2 = make_person("John", "Smith", std_given="John", std_surname="Smith")
        matches, comparisons = name_match(p1.get_names(), p2.get_names())
        assert matches == -1

    def test_identical_persons(self):
        p1 = make_person("John", "Doe", std_given="John", std_surname="Doe")
        p2 = make_person("John", "Doe", std_given="John", std_surname="Doe")
        matches, comparisons = name_match(p1.get_names(), p2.get_names())
        assert matches >= 1
        assert comparisons >= 1

    def test_married_name_cross_comparison(self):
        p1 = make_person("John", "Doe", std_given="John", std_surname="Doe")
        p2 = make_person("John", "Doe", gender="f",
                         name_type="married", std_given="John", std_surname="Doe")
        matches, comparisons = name_match(p1.get_names(), p2.get_names())
        # birth vs married cross-comparison should find both given and surname match
        assert matches >= 1


# --- date_overlap ---

class TestDateOverlap:
    def test_overlapping(self):
        d1 = Date("1900-01-01", "1900-12-31")
        d2 = Date("1900-06-01", "1901-06-01")
        assert date_overlap(d1, d2) is True

    def test_non_overlapping(self):
        d1 = Date("1900-01-01", "1900-06-01")
        d2 = Date("1901-01-01", "1901-06-01")
        assert date_overlap(d1, d2) is False

    def test_exact_same(self):
        d1 = Date("1900-06-15")
        d2 = Date("1900-06-15")
        assert date_overlap(d1, d2) is True

    def test_adjacent_with_accuracy(self):
        d1 = Date("1900-01-01", accuracy=timedelta(days=10))
        d2 = Date("1900-01-10", accuracy=timedelta(days=10))
        assert date_overlap(d1, d2) is True


# --- datelist_overlap ---

class TestDatelistOverlap:
    def test_one_overlaps(self):
        dl1 = [Date("1900-01-01", "1903-01-01")]
        dl2 = [Date("1902-06-01", "1902-12-31")]
        assert datelist_overlap(dl1, dl2) is True

    def test_none_overlap(self):
        dl1 = [Date("1900-01-01")]
        dl2 = [Date("1910-01-01")]
        assert datelist_overlap(dl1, dl2) is False


# --- birth_death_match ---

class TestBirthDeathMatch:
    def test_matching(self):
        p1 = make_person("A", "B", birth_date=Date("1900-01-01", "1900-12-31"),
                         death_date=Date("1970-01-01", "1970-12-31"))
        p2 = make_person("C", "D", birth_date=Date("1900-06-01", "1901-06-01"),
                         death_date=Date("1970-06-01", "1971-06-01"))
        matches, comparisons = birth_death_match(p1, p2)
        assert matches == 4

    def test_mismatching_birth(self):
        p1 = make_person("A", "B", birth_date=Date("1900-01-01"))
        p2 = make_person("C", "D", birth_date=Date("1950-01-01"))
        matches, comparisons = birth_death_match(p1, p2)
        assert matches == -1

    def test_partial_data(self):
        p1 = make_person("A", "B", birth_date=Date("1900-01-01", "1900-12-31"))
        p2 = make_person("C", "D", birth_date=Date("1900-06-01", "1901-06-01"))
        matches, comparisons = birth_death_match(p1, p2)
        assert matches == 1
        assert comparisons == 1

    def test_no_dates(self):
        p1 = make_person("A", "B")
        p2 = make_person("C", "D")
        matches, comparisons = birth_death_match(p1, p2)
        assert matches == 0
        assert comparisons == 0


# --- person_mismatch ---

class TestPersonMismatch:
    def test_identical_persons_not_mismatch(self):
        p1 = make_person("John", "Doe", "m",
                         birth_date=Date("1900-01-01"),
                         std_given="John", std_surname="Doe")
        p2 = make_person("John", "Doe", "m",
                         birth_date=Date("1900-01-01"),
                         std_given="John", std_surname="Doe")
        assert person_mismatch(p1, p2) is False

    def test_gender_mismatch(self):
        p1 = make_person("John", "Doe", "m")
        p2 = make_person("John", "Doe", "f")
        assert person_mismatch(p1, p2) is True

    def test_stillbirth_mismatch(self):
        p1 = make_person("John", "Doe", "m")
        p1.add_fact(Fact("Stillbirth"))
        p2 = make_person("John", "Doe", "m")
        assert person_mismatch(p1, p2) is True

    def test_name_mismatch(self):
        p1 = make_person("John", "Doe", "m", std_given="John", std_surname="Doe")
        p2 = make_person("Jane", "Smith", "f", std_given="Jane", std_surname="Smith")
        assert person_mismatch(p1, p2) is True

    def test_date_mismatch(self):
        p1 = make_person("John", "Doe", "m",
                         birth_date=Date("1900-01-01"),
                         std_given="John", std_surname="Doe")
        p2 = make_person("John", "Doe", "m",
                         birth_date=Date("1950-01-01"),
                         std_given="John", std_surname="Doe")
        assert person_mismatch(p1, p2) is True


# --- compare_location ---

class TestCompareLocation:
    def test_same_house_number(self):
        loc1 = make_location(house_number="123")
        loc2 = make_location(house_number="123")
        assert compare_location(loc1, loc2) is True

    def test_alt_matches_primary(self):
        loc1 = make_location(house_number="123")
        loc2 = make_location(alt_house_number="123")
        assert compare_location(loc1, loc2) is True

    def test_different_village(self):
        loc1 = make_location(house_number="123", alt_village="VillageA")
        loc2 = make_location(house_number="123", alt_village="VillageB")
        assert compare_location(loc1, loc2) is False

    def test_no_match(self):
        loc1 = make_location(house_number="123")
        loc2 = make_location(house_number="456")
        assert compare_location(loc1, loc2) is False


# --- location_match ---

class TestLocationMatch:
    def test_matching(self):
        locs1 = [make_location(house_number="123")]
        locs2 = [make_location(house_number="123")]
        assert location_match(locs1, locs2) == 1

    def test_no_match(self):
        locs1 = [make_location(house_number="123")]
        locs2 = [make_location(house_number="456")]
        assert location_match(locs1, locs2) == 0

    def test_empty_lists(self):
        assert location_match([], []) == 0
        assert location_match(None, []) == 0
