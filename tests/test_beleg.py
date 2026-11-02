from app.extraktion import belegt, betrag, gleich

DOK = "Arbeitgeber: Musterbau KG\nGesamtbrutto: 2.345,67 €\nNettoverdienst: EUR 1.800,10\nName, Vorname: Becker, Anna"


def test_betrag():
    assert betrag("2.345,67 €") == 2345.67 and betrag("1234.50") == 1234.5 and betrag("-150,00 EUR") == -150.0


def test_beleg_richtig():
    assert belegt("brutto", "2345.67", "Gesamtbrutto: 2.345,67 €", DOK)
    assert belegt("name", "Anna Becker", "Name, Vorname: Becker, Anna", DOK)


def test_beleg_falsch():
    assert not belegt("brutto", "2345.67", "Gesamtbrutto: 2.345,76 €", DOK)    # Zeile steht nicht im Dokument
    assert not belegt("netto", "2345.67", "Nettoverdienst: EUR 1.800,10", DOK)  # Wert passt nicht zur Zeile
    assert not belegt("arbeitgeber", "Musterbau KG", "", DOK)


def test_gleich():
    assert gleich("name", "Anna Becker", "Becker, Anna") and not gleich("netto", "1800.10", "1800.01")
