from data_model import *
from graph_model import PeopleGraph
from import_records import BirthRecord


def make_person_json(given, surname, gender="m", birth_date=None):
    name_json = {"name_type": "birth", "name_parts": {"given": given, "surname": surname},
                 "standard_surname": surname, "standard_given": given, "confidence": "normal"}
    person = {"identifier": None, "gender": gender, "names": [name_json], "confidence": "normal"}
    if birth_date:
        person["facts"] = [{"fact_type": "Birth",
                            "date": [{"start": birth_date, "end": birth_date, "accuracy": 0}],
                            "confidence": "normal"}]
    return person


def make_relation_json(from_id, to_id, rel_type="parent-child"):
    return {"identifier": None, "from_id": from_id, "to_id": to_id,
            "relationship_type": rel_type, "confidence": "normal"}


class TestPeopleGraphFromJson:
    def test_construct_from_json(self):
        p1 = make_person_json("John", "Doe")
        p1["identifier"] = "aaa-111"
        p2 = make_person_json("Jane", "Doe", gender="f")
        p2["identifier"] = "bbb-222"
        rel = make_relation_json("aaa-111", "bbb-222", "parent-child")
        rel["identifier"] = "rel-1"

        graph_json = {"persons": [p1, p2], "relations": [rel]}
        pg = PeopleGraph(graph_json=graph_json)

        assert pg.graph.number_of_nodes() == 2
        assert pg.graph.number_of_edges() == 1
        assert "aaa-111" in pg.people
        assert "bbb-222" in pg.people

    def test_empty_graph(self):
        pg = PeopleGraph()
        assert pg.graph.number_of_nodes() == 0
        assert pg.graph.number_of_edges() == 0


class TestPeopleGraphAppend:
    def test_append_record(self):
        pg = PeopleGraph()
        thesaurus = {}
        source = Source(repository="TestArch", volume="V1", page_number=1, entry_number=1)
        record = BirthRecord(thesaurus, source, None, {}, {})
        record.newborn.gender = "m"
        record.set_newborn_names("Doe", "John", None)
        record.set_birth_death("06-15", "06-16", "1900", None)
        record.set_parents("Doe", "Peter", None, "Mary")

        pg.append(record)
        assert pg.graph.number_of_nodes() >= 3  # newborn + father + mother
        assert pg.graph.number_of_edges() >= 2  # parent-child edges


class TestPeopleGraphJson:
    def test_json_roundtrip(self):
        p1 = make_person_json("John", "Doe")
        p1["identifier"] = "aaa-111"
        p2 = make_person_json("Jane", "Doe", gender="f")
        p2["identifier"] = "bbb-222"
        rel = make_relation_json("aaa-111", "bbb-222", "parent-child")
        rel["identifier"] = "rel-1"

        graph_json = {"persons": [p1, p2], "relations": [rel]}
        pg1 = PeopleGraph(graph_json=graph_json)
        exported = pg1.json()
        pg2 = PeopleGraph(graph_json=exported)

        assert pg2.graph.number_of_nodes() == 2
        assert pg2.graph.number_of_edges() == 1
        assert pg2.people["aaa-111"].names[0].name_parts["given"] == "John"


class TestPeopleGraphDirectRelations:
    def test_direct_relations(self):
        p1 = make_person_json("John", "Doe")
        p1["identifier"] = "aaa-111"
        p2 = make_person_json("Jane", "Doe", gender="f")
        p2["identifier"] = "bbb-222"
        p3 = make_person_json("Jim", "Doe")
        p3["identifier"] = "ccc-333"

        rel1 = make_relation_json("aaa-111", "bbb-222", "spouse")
        rel1["identifier"] = "rel-1"
        rel2 = make_relation_json("aaa-111", "ccc-333", "parent-child")
        rel2["identifier"] = "rel-2"

        graph_json = {"persons": [p1, p2, p3], "relations": [rel1, rel2]}
        pg = PeopleGraph(graph_json=graph_json)
        relations = pg.direct_relations("aaa-111")

        assert "bbb-222" in relations["spouses"]
        assert "ccc-333" in relations["children"]
