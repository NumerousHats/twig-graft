from data_model import *


class TestDateDuration:
    def test_subtract(self):
        date = Date("1900-01-01")
        duration = Duration([1, 0, 0, 0])
        assert subtract(date, duration).json_dict() == {"start": "1898-01-02", "end": "1899-01-01",
                                                        "confidence": "calculated"}

        assert subtract(date, duration).json_dict() == {"start": "1898-01-02", "end": "1899-01-01",
                                                        "confidence": "calculated"}


class TestFact:
    def test_fact_repr(self):
        fact = Fact("Birth", Date("1900-01-01"))
        assert fact.json_dict() == {"fact_type": "Birth",
                                    "date": [{'start': '1900-01-01', 'end': '1900-01-01',
                                              'confidence': 'normal'}],
                                    'confidence': 'normal'}
