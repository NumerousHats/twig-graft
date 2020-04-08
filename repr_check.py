from data_model import *


def main():
    source = Source(repository="repository", volume="vol", page_number=183,
                    entry_number=6, image_file="blah.jpg")
    print(repr(source))
    print("\n")

    duration = Duration([1, 2, 3, 4], year_day_ambiguity=True)
    print(repr(duration))
    print("\n")

    location = Location(house_number=158, alt_house_number=2, alt_village="Nowhere")
    print(repr(location))
    print("\n")

    name = Name(name_type="birth", name_parts={"given": "Bob", "surname": "Melnyk"}, sources=source,
                notes=["Note #1", "Note #2"], confidence="none whatsoever")
    print(repr(name))
    print("\n")

    fact1 = Fact(fact_type="death", date=Date("1854-01-02"), age=duration, locations=location)
    print(repr(fact1))
    print("\n")

    fact2 = Fact(fact_type="birth", date=Date("1851-01-02", "1852-01-02"), locations=location)

    person = Person(names=name, gender="f", facts=[fact1, fact2], sources=source,
                    notes="No way.", confidence="uh huh")
    print(repr(person))


if __name__ == "__main__":
    main()
