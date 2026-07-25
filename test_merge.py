import pytest
import networkx as nx
from data_model import *
from graph_model import PeopleGraph
import comparison
from birth_merge import node_match, edge_match, sanity_check


def make_person_with_names(given, surname, gender="m", birth_date=None, std_given=None, std_surname=None):
    name = Name("birth", {"given": given, "surname": surname}, thesaurus=None)
    if std_given:
        name.standard_given = std_given
    if std_surname:
        name.standard_surname = std_surname
    facts = []
    if birth_date:
        facts.append(Fact("Birth", date=birth_date))
    return Person(names=[name], gender=gender, facts=facts or None)


def make_person_json(identifier, given, surname, gender="m", birth_date=None):
    name_json = {"name_type": "birth", "name_parts": {"given": given, "surname": surname},
                 "standard_surname": surname, "standard_given": given, "confidence": "normal"}
    person = {"identifier": identifier, "gender": gender, "names": [name_json], "confidence": "normal"}
    if birth_date:
        person["facts"] = [{"fact_type": "Birth",
                            "date": [{"start": birth_date, "end": birth_date, "accuracy": 0}],
                            "confidence": "normal"}]
    return person


def make_relation_json(identifier, from_id, to_id, rel_type="parent-child"):
    return {"identifier": identifier, "from_id": from_id, "to_id": to_id,
            "relationship_type": rel_type, "confidence": "normal"}


def build_test_graph():
    """Build a small PeopleGraph with parent→child→child structure."""
    graph_json = {
        "persons": [
            make_person_json("p1", "John", "Doe", "m"),
            make_person_json("p2", "Jane", "Doe", "f"),
            make_person_json("p3", "Jim", "Doe", "m"),
        ],
        "relations": [
            make_relation_json("r1", "p1", "p2", "parent-child"),
            make_relation_json("r2", "p1", "p3", "parent-child"),
        ]
    }
    return PeopleGraph(graph_json=graph_json)


# --- Person.merge() ---

class TestPersonMerge:
    def test_basic_merge(self):
        p1 = make_person_with_names("John", "Doe", "m", birth_date=Date("1900-01-01"),
                                    std_given="John", std_surname="Doe")
        p2 = make_person_with_names("John", "Doe", "m", birth_date=Date("1900-01-01"),
                                    std_given="John", std_surname="Doe")

        merged, rel1, rel2 = p1.merge(p2)

        assert p1.merged is True
        assert p2.merged is True
        assert merged.merged is False
        assert merged.gender == "m"
        assert len(merged.names) == 2
        assert rel1.relationship_type == "merged-into"
        assert rel2.relationship_type == "merged-into"
        assert rel1.from_id == p1.identifier
        assert rel2.from_id == p2.identifier

    def test_merge_birth_dates_intersect(self):
        p1 = make_person_with_names("John", "Doe", "m",
                                    birth_date=Date("1900-01-01", "1900-12-31"))
        p2 = make_person_with_names("John", "Doe", "m",
                                    birth_date=Date("1900-06-01", "1901-06-01"))

        merged, _, _ = p1.merge(p2)
        facts = merged.get_facts()
        assert "Birth" in facts
        # Intersection of [Jan 1 1900, Dec 31 1900] and [Jun 1 1900, Jun 1 1901]
        # should be [Jun 1 1900, Dec 31 1900]
        assert len(facts["Birth"]) == 1
        assert facts["Birth"][0].date[0].start == Date("1900-06-01").start
        assert facts["Birth"][0].date[0].end == Date("1900-12-31").end

    def test_merge_gender_conflict(self):
        p1 = make_person_with_names("John", "Doe", "m")
        p2 = make_person_with_names("John", "Doe", "f")

        merged, _, _ = p1.merge(p2)
        assert merged.gender is None

    def test_merge_already_merged_raises(self):
        p1 = make_person_with_names("John", "Doe", "m")
        p2 = make_person_with_names("John", "Doe", "m")
        p1.merge(p2)

        p3 = make_person_with_names("Jim", "Doe", "m")
        with pytest.raises(ValueError):
            p1.merge(p3)

    def test_merge_low_confidence_propagates(self):
        p1 = make_person_with_names("John", "Doe", "m")
        p1.confidence = "low"
        p2 = make_person_with_names("John", "Doe", "m")

        merged, _, _ = p1.merge(p2)
        assert merged.confidence == "low"


# --- Relationship.merge() ---

class TestRelationshipMerge:
    def test_basic_merge(self):
        r1 = Relationship("a", "b", "parent-child",
                          sources=Source(repository="Arch1", volume="V1"))
        r2 = Relationship("a", "b", "parent-child",
                          sources=Source(repository="Arch2", volume="V2"))

        merged = r1.merge(r2)
        assert merged.relationship_type == "parent-child"
        assert merged.from_id == "a"
        assert merged.to_id == "b"
        assert len(merged.sources) == 2

    def test_merge_different_types_raises(self):
        r1 = Relationship("a", "b", "parent-child")
        r2 = Relationship("a", "b", "spouse")
        with pytest.raises(ValueError):
            r1.merge(r2)

    def test_merge_different_from_ids_raises(self):
        r1 = Relationship("a", "b", "parent-child")
        r2 = Relationship("x", "b", "parent-child")
        with pytest.raises(ValueError):
            r1.merge(r2)

    def test_merge_low_confidence(self):
        r1 = Relationship("a", "b", "parent-child")
        r2 = Relationship("a", "b", "parent-child", confidence="low")
        merged = r1.merge(r2)
        assert merged.confidence == "low"


# --- birth_merge callbacks ---

class TestBirthMergeCallbacks:
    def _make_nx_graph_with_person(self, pid, given, surname, gender="m"):
        g = nx.DiGraph()
        person = make_person_with_names(given, surname, gender)
        g.add_node(pid, person=person)
        return g

    def test_node_match_same_person(self):
        g1 = self._make_nx_graph_with_person("a", "John", "Doe", "m")
        g2 = self._make_nx_graph_with_person("x", "John", "Doe", "m")
        assert node_match(g1, g2, "a", "x") is True

    def test_node_match_different_gender(self):
        g1 = self._make_nx_graph_with_person("a", "John", "Doe", "m")
        g2 = self._make_nx_graph_with_person("x", "John", "Doe", "f")
        assert node_match(g1, g2, "a", "x") is False

    def test_edge_match_same_type(self):
        g1 = nx.DiGraph()
        g1.add_edge("a", "b", relation=Relationship("a", "b", "parent-child"))
        g2 = nx.DiGraph()
        g2.add_edge("x", "y", relation=Relationship("x", "y", "parent-child"))
        assert edge_match(g1, g2, "a", "b", "x", "y") is True

    def test_edge_match_different_type(self):
        g1 = nx.DiGraph()
        g1.add_edge("a", "b", relation=Relationship("a", "b", "parent-child"))
        g2 = nx.DiGraph()
        g2.add_edge("x", "y", relation=Relationship("x", "y", "spouse"))
        assert edge_match(g1, g2, "a", "b", "x", "y") is False


# --- sanity_check ---

class TestSanityCheck:
    def test_valid_graph(self):
        pg = build_test_graph()
        sanity_check(pg.graph)  # should not raise

    def test_invalid_graph_raises(self):
        g = nx.DiGraph()
        g.add_node("orphan")  # no "person" attribute
        with pytest.raises(KeyError):
            sanity_check(g)
