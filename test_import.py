from import_records import *


def probe():
    record = DeathRecord(age=Duration(duration_list=[23, 0, 0, 0], year_day_ambiguity=False), thesaurus={},
                         source=None, location=None, notes={}, confidence={})
    record.decedent.gender = "f"
    record.set_decedent_names("Doe", "Jane", None, None)
    names = record.json()["people"][0]["names"]
    print(names)


class TestDeath:
    def test_source(self):
        record = DeathRecord(age=Duration(duration_list=[0, 0, 0, 0], year_day_ambiguity=False), thesaurus={},
                             source=Source(repository="NARA", volume="XYZ123", page_number=456, entry_number=7),
                             location=None, notes={}, confidence={})
        record_part = record.json()["people"][0]["sources"][0]
        assert record_part == {'repository': 'NARA', 'volume': 'XYZ123', 'page_number': 456,
                               'entry_number': 7, 'image_file': None}

    def test_decedent_name(self):
        record = DeathRecord(age=Duration(duration_list=[23, 0, 0, 0], year_day_ambiguity=False), thesaurus={},
                             source=None, location=None, notes={}, confidence={})
        record.decedent.gender = "m"
        record.set_decedent_names("Doe (Dodo)", "Robert (Bob)", True, None)
        names = record.json()["people"][0]["names"]
        assert names == [{'name_type': 'birth',
                          'name_parts': {'surname': 'Doe', 'house_name': 'Dodo', 'given': 'Robert'},
                          'standard_surname': None, 'standard_given': None, 'confidence': 'normal'},
                         {'name_type': 'also_known_as',
                          'name_parts': {'surname': 'Doe', 'house_name': 'Dodo', 'given': 'Bob'},
                          'standard_surname': None, 'standard_given': None, 'confidence': 'normal'}]

        record = DeathRecord(age=Duration(duration_list=[23, 0, 0, 0], year_day_ambiguity=False), thesaurus={},
                             source=None, location=None, notes={}, confidence={})
        record.decedent.gender = "f"
        record.set_decedent_names("Doe", "Jane", True, "Smith")
        names = record.json()["people"][0]["names"]
        assert names == [{'name_type': 'birth',
                          'name_parts': {'surname': 'Smith', 'given': 'Jane'}, 'standard_surname': None,
                          'standard_given': None, 'confidence': 'normal'},
                         {'name_type': 'married', 'name_parts': {'surname': 'Doe', 'given': 'Jane'},
                          'standard_surname': None, 'standard_given': None, 'confidence': 'normal'}]

        record = DeathRecord(age=Duration(duration_list=[23, 0, 0, 0], year_day_ambiguity=False), thesaurus={},
                             source=None, location=None, notes={}, confidence={})
        record.decedent.gender = "f"
        record.set_decedent_names("Doe", "Jane", None, None)
        names = record.json()["people"][0]["names"]
        assert names == [{'name_type': 'birth', 'name_parts': {'given': 'Jane'},
                          'standard_surname': None, 'standard_given': None, 'confidence': 'normal'},
                         {'name_type': 'unknown', 'name_parts': {'surname': 'Doe', 'given': 'Jane'},
                          'standard_surname': None, 'standard_given': None, 'confidence': 'normal'}]

        record = DeathRecord(age=Duration(duration_list=[12, 0, 0, 0], year_day_ambiguity=False), thesaurus={},
                             source=None, location=None, notes={}, confidence={})
        record.decedent.gender = "f"
        record.set_decedent_names("Doe", "Jane", None, None)
        names = record.json()["people"][0]["names"]
        assert names == [{'name_type': 'birth', 'name_parts': {'surname': 'Doe', 'given': 'Jane'},
                          'standard_surname': None, 'standard_given': None, 'confidence': 'normal'}]

    def test_birth_death(self):
        record = DeathRecord(age=Duration(duration_list=[20, 0, 0, 0], year_day_ambiguity=False), thesaurus={},
                             source=None, location=None, notes={}, confidence={})
        record.set_birth_death("12-30", "1901-01-02", "1900", None)
        facts = record.json()["people"][0]["facts"]
        assert facts == [{'fact_type': 'Death', 'content': None,
                          'age': {'duration': [20, 0, 0, 0], 'confidence': 'normal',
                                  'precision': 'year', 'year_day_ambiguity': 'False'},
                          'date': {'start': '1900-12-30', 'end': '1900-12-30', 'confidence': 'normal'},
                          'confidence': 'normal'},
                         {'fact_type': 'Burial', 'content': None,
                          'age': {'duration': [20, 0, 0, 0], 'confidence': 'normal',
                                  'precision': 'year', 'year_day_ambiguity': 'False'},
                          'date': {'start': '1901-01-02', 'end': '1901-01-02', 'confidence': 'normal'},
                          'confidence': 'normal'},
                         {'fact_type': 'Birth', 'content': None,
                          'date': {'start': '1880-01-05', 'end': '1881-01-03', 'confidence': 'calculated',
                                   'notes': ['Birth date calculated from actual or estimated death date.']},
                          'confidence': 'normal'}]


if __name__ == "__main__":
    probe()
