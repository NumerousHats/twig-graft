from data_model import *


class TestDateDuration:
    def test_subtract(self):
        date = Date("1900-01-01")
        duration = Duration([1, 0, 0, 0])
        assert subtract(date, duration)[0].json() == {"start": "1898-01-02", "end": "1899-01-01", "accuracy": 10}


class TestFact:
    def test_fact_repr(self):
        fact = Fact("Birth", Date("1900-01-01"))
        assert fact.json() == {"fact_type": "Birth",
                               "date": [{'start': '1900-01-01', 'end': '1900-01-01', "accuracy": 0}],
                               'confidence': 'normal'}
