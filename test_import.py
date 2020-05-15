from unittest.mock import patch
from import_records import *

TEST_UUID_COUNT = 0


def mock_uuid():
    global TEST_UUID_COUNT
    TEST_UUID_COUNT += 1
    return str(TEST_UUID_COUNT)


@patch('uuid.uuid4', mock_uuid)
def probe():
    global TEST_UUID_COUNT
    TEST_UUID_COUNT = 0
    record = DeathRecord(age=Duration(duration_list=[20, 0, 0, 0], year_day_ambiguity=False), thesaurus={},
                         source=None, location=None, notes={}, confidence={})
    record.set_birth_death("12-30", "1901-01-02", "1900", None)
    serialization = record.json()
    print(serialization)


class TestDeath:
    @patch('uuid.uuid4', mock_uuid)
    def test_source(self):
        global TEST_UUID_COUNT
        TEST_UUID_COUNT = 0

        record_json = DeathRecord(age=Duration(duration_list=[0, 0, 0, 0], year_day_ambiguity=False), thesaurus={},
                                  source=Source(repository="NARA", volume="XYZ123", page_number=456, entry_number=7),
                                  location=None, notes={}, confidence={}).json()

        assert record_json == {'people': [{'identifier': '1', 'gender': None,
                                           'sources': [{'repository': 'NARA', 'volume': 'XYZ123', 'page_number': 456,
                                                        'entry_number': 7, 'image_file': None}],
                                           'confidence': 'normal'}], 'relations': []}

    @patch('uuid.uuid4', mock_uuid)
    def test_decedent_name(self):
        global TEST_UUID_COUNT

        TEST_UUID_COUNT = 0
        record = DeathRecord(age=Duration(duration_list=[23, 0, 0, 0], year_day_ambiguity=False),
                             thesaurus={},
                             source=None,
                             location=None,
                             notes={},
                             confidence={})

        record.decedent.gender = "m"
        record.set_decedent_names("Doe (Dodo)", "Robert (Bob)", True, None)

        assert record.json() == {'people': [{'identifier': '1', 'gender': 'm',
                                             'names': [{'name_type': 'birth',
                                                        'name_parts':
                                                            {'surname': 'Doe', 'house_name': 'Dodo', 'given': 'Robert'},
                                                        'standard_surname': None, 'standard_given': None,
                                                        'confidence': 'normal'},
                                                       {'name_type': 'also_known_as',
                                                        'name_parts':
                                                            {'surname': 'Doe', 'house_name': 'Dodo', 'given': 'Bob'},
                                                        'standard_surname': None, 'standard_given': None,
                                                        'confidence': 'normal'}], 'confidence': 'normal'}],
                                 'relations': []}

        TEST_UUID_COUNT = 0
        record = DeathRecord(age=Duration(duration_list=[23, 0, 0, 0], year_day_ambiguity=False),
                             thesaurus={},
                             source=None,
                             location=None,
                             notes={},
                             confidence={})

        record.decedent.gender = "f"
        record.set_decedent_names("Doe", "Jane", True, "Smith")

        assert record.json() == {'people': [{'identifier': '1', 'gender': 'f',
                                             'names': [{'name_type': 'birth',
                                                        'name_parts':
                                                            {'surname': 'Smith', 'given': 'Jane'},
                                                        'standard_surname': None, 'standard_given': None,
                                                        'confidence': 'normal'},
                                                       {'name_type': 'married',
                                                        'name_parts':
                                                            {'surname': 'Doe', 'given': 'Jane'},
                                                        'standard_surname': None, 'standard_given': None,
                                                        'confidence': 'normal'}], 'confidence': 'normal'}],
                                 'relations': []}

        TEST_UUID_COUNT = 0
        record = DeathRecord(age=Duration(duration_list=[23, 0, 0, 0], year_day_ambiguity=False),
                             thesaurus={},
                             source=None,
                             location=None,
                             notes={},
                             confidence={})

        record.decedent.gender = "f"
        record.set_decedent_names("Doe", "Jane", None, None)

        assert record.json() == {'people': [{'identifier': '1', 'gender': 'f',
                                             'names': [{'name_type': 'unknown',
                                                        'name_parts':
                                                            {'surname': 'Doe', 'given': 'Jane'},
                                                        'standard_surname': None, 'standard_given': None,
                                                        'confidence': 'normal'}], 'confidence': 'normal'}],
                                 'relations': []}

        TEST_UUID_COUNT = 0
        record = DeathRecord(age=Duration(duration_list=[12, 0, 0, 0], year_day_ambiguity=False), thesaurus={},
                             source=None, location=None, notes={}, confidence={})

        record.decedent.gender = "f"
        record.set_decedent_names("Doe", "Jane", None, None)

        assert record.json() == {'people': [{'identifier': '1', 'gender': 'f',
                                             'names': [{'name_type': 'birth',
                                                        'name_parts':
                                                            {'surname': 'Doe', 'given': 'Jane'},
                                                        'standard_surname': None, 'standard_given': None,
                                                        'confidence': 'normal'}], 'confidence': 'normal'}],
                                 'relations': []}

    @patch('uuid.uuid4', mock_uuid)
    def test_birth_death(self):
        global TEST_UUID_COUNT

        TEST_UUID_COUNT = 0
        record = DeathRecord(age=Duration(duration_list=[20, 0, 0, 0], year_day_ambiguity=False), thesaurus={},
                             source=None, location=None, notes={}, confidence={})
        record.set_birth_death("12-30", "1901-01-02", "1900", None)
        assert record.json() == {'people': [{'identifier': '1', 'gender': None,
                                             'facts': [{'fact_type': 'Death', 'content': None,
                                                        'age': {'duration': [20, 0, 0, 0], 'confidence': 'normal',
                                                                'precision': 'year', 'year_day_ambiguity': 'False'},
                                                        'date': {'start': '1900-12-30', 'end': '1900-12-30',
                                                                 'confidence': 'normal'},
                                                        'confidence': 'normal'},
                                                       {'fact_type': 'Burial', 'content': None,
                                                        'age': {'duration': [20, 0, 0, 0], 'confidence': 'normal',
                                                                'precision': 'year', 'year_day_ambiguity': 'False'},
                                                        'date': {'start': '1901-01-02', 'end': '1901-01-02',
                                                                 'confidence': 'normal'}, 'confidence': 'normal'},
                                                       {'fact_type': 'Birth', 'content': None,
                                                        'date': {'start': '1880-01-05', 'end': '1881-01-03',
                                                                 'confidence': 'calculated',
                                                                 'notes': ['Birth date calculated from actual or estimated death date.']},
                                                        'confidence': 'normal'}],
                                             'confidence': 'normal'}],
                                 'relations': []}


if __name__ == "__main__":
    probe()
