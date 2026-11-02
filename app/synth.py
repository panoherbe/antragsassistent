"""Generator für synthetische Fälle: Antrag plus Nachweise als Text, mit bekannter Wahrheit.

Keine echten Personen, keine echten Sozialdaten. Namen werden zufällig aus häufigen Vor- und Nachnamen kombiniert,
Anschriften sind erfunden („Musterweg“), Kontonummern sind ungültig (Prüfziffer 00). Jedes Dokument trägt im Kopf
den Vermerk SYNTHETISCHES TESTDOKUMENT und eine Kennung SYN-…; die Anwendung nimmt nur Dokumente mit Kennung an.

Die Vorlagen variieren Beschriftungen, Zahlenformate und Reihenfolge, damit die Extraktion nicht an einer festen
Schablone hängt. Deterministisch: gleicher Startwert, gleiche Fälle.
"""
import random
from dataclasses import dataclass, field

VORNAMEN = ["Anna", "Jonas", "Leonie", "Mehmet", "Sofia", "Lukas", "Elif", "Paul", "Marie", "Tobias", "Aylin",
            "Felix", "Hannah", "Daniel", "Olga", "Ben", "Clara", "Yusuf", "Lea", "Stefan", "Ivana", "Noah"]
NACHNAMEN = ["Becker", "Schulz", "Yilmaz", "Hoffmann", "Krüger", "Wagner", "Nowak", "Schmitt", "Kaya", "Lange",
             "Fischer", "Weber", "Popescu", "Braun", "Wolf", "Kowalski", "Richter", "Neumann", "Demir", "Klein"]
ARBEITGEBER = ["Beispiel Logistik GmbH", "Musterbau KG", "Probe Gastro GmbH", "Fiktiv Pflege gGmbH",
               "Testhandel Süd GmbH", "Demo Reinigung GmbH & Co. KG", "Muster Service AG"]
MONATE = ["Januar", "Februar", "März", "April", "Mai", "Juni", "Juli", "August", "September", "Oktober",
          "November", "Dezember"]
ORTE = ["10115 Musterstadt", "20095 Beispielheim", "80331 Probedorf", "50667 Testhausen"]


@dataclass
class Dokument:
    kennung: str
    art: str
    text: str
    wahr: dict


@dataclass
class Fall:
    kennung: str
    antragsart: str
    merkmale: dict
    dokumente: list[Dokument] = field(default_factory=list)
    fehlend: list[str] = field(default_factory=list)


def euro(r: random.Random, wert: float) -> str:
    s = f"{wert:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return r.choice([f"{s} €", f"{s} EUR", f"EUR {s}", s + " Euro"])


def kopf(kennung: str, titel: str) -> str:
    return f"SYNTHETISCHES TESTDOKUMENT · Kennung {kennung}\n{titel}\n" + "=" * len(titel) + "\n"


def _antrag(r, k, person, merkmale, art) -> Dokument:
    geb = f"{r.randint(1, 28):02d}.{r.randint(1, 12):02d}.{r.randint(1960, 2004)}"
    zeilen = [
        ("Name, Vorname" if r.random() < .5 else "Antragstellende Person", f"{person[1]}, {person[0]}"),
        (r.choice(["Geburtsdatum", "geboren am", "Geb.-Datum"]), geb),
        ("Anschrift", f"Musterweg {r.randint(1, 120)}, {r.choice(ORTE)}"),
        (r.choice(["Personen in der Bedarfsgemeinschaft", "Anzahl Personen BG", "Mitglieder der Bedarfsgemeinschaft (Anzahl)"]),
         str(merkmale["personen"])),
        ("Erwerbstätigkeit", "ja" if merkmale["erwerbstaetig"] else "nein"),
        ("Wohnung zur Miete", "ja" if merkmale["miete"] else "nein"),
    ]
    rest = zeilen[3:]
    r.shuffle(rest)
    zeilen = zeilen[:3] + rest
    text = kopf(k, art) + "\n".join(f"{a}: {b}" for a, b in zeilen)
    text += "\n\nIch versichere, dass meine Angaben vollständig sind. (synthetisch, keine Unterschrift)\n"
    return Dokument(k, "antrag", text, {"name": f"{person[0]} {person[1]}", "geburtsdatum": geb,
                                         "personen_bg": str(merkmale["personen"])})


def _lohn(r, k, person) -> Dokument:
    brutto = round(r.uniform(900, 3200), 2)
    netto = round(brutto * r.uniform(0.68, 0.82), 2)
    monat = f"{r.choice(MONATE)} 2026"
    ag = r.choice(ARBEITGEBER)
    posten = [("Grundvergütung", brutto * .9), ("Zuschläge", brutto * .1)]
    text = kopf(k, r.choice(["Entgeltabrechnung", "Lohn- und Gehaltsabrechnung", "Verdienstabrechnung"]))
    text += f"Arbeitgeber: {ag}\n" if r.random() < .6 else f"{ag}, Personalabteilung\n"
    text += f"Mitarbeiter/in: {person[0]} {person[1]}\nAbrechnungsmonat: {monat}\n\n"
    for name, w in posten:
        text += f"  {name:<28}{euro(r, w)}\n"
    text += f"{r.choice(['Gesamtbrutto', 'Brutto gesamt', 'Bruttobezüge'])}: {euro(r, brutto)}\n"
    text += f"  Steuern und Sozialabgaben  {euro(r, brutto - netto)}\n"
    text += f"{r.choice(['Nettoverdienst', 'Auszahlungsbetrag netto', 'Netto'])}: {euro(r, netto)}\n"
    return Dokument(k, "lohnabrechnung", text, {"arbeitgeber": ag, "monat": monat,
                                                "brutto": f"{brutto:.2f}", "netto": f"{netto:.2f}"})


def _miete(r, k, person) -> Dokument:
    kalt, nk, hk = round(r.uniform(300, 760), 2), round(r.uniform(60, 220), 2), round(r.uniform(40, 150), 2)
    qm = r.randint(30, 92)
    zeilen = [(r.choice(["Grundmiete (kalt)", "Nettokaltmiete", "Kaltmiete"]), euro(r, kalt)),
              (r.choice(["Betriebskostenvorauszahlung", "Nebenkosten (ohne Heizung)", "kalte Betriebskosten"]), euro(r, nk)),
              (r.choice(["Heizkostenvorauszahlung", "Heizkosten", "Heizung und Warmwasser"]), euro(r, hk))]
    r.shuffle(zeilen)
    text = kopf(k, r.choice(["Mietbescheinigung", "Bescheinigung des Vermieters"]))
    text += f"Mieter/in: {person[0]} {person[1]}, Musterweg {r.randint(1, 120)}\n"
    text += f"Wohnfläche: {qm} m²\n\nMonatliche Zahlungen:\n" + "\n".join(f"- {a}: {b}" for a, b in zeilen)
    text += f"\nGesamtmiete: {euro(r, kalt + nk + hk)}\n\nVermieter: Muster Wohnungsbau eG (fiktiv)\n"
    return Dokument(k, "mietbescheinigung", text, {"kaltmiete": f"{kalt:.2f}", "nebenkosten": f"{nk:.2f}",
                                                   "heizkosten": f"{hk:.2f}", "wohnflaeche": str(qm)})


def _konto(r, k, person) -> Dokument:
    saldo = round(r.uniform(-200, 1500), 2)
    inhaber = f"{person[0]} {person[1]}"
    text = kopf(k, "Kontoauszug")
    text += f"Kontoinhaber: {inhaber}\nIBAN: DE00 0000 0000 {r.randint(1000, 9999)} {r.randint(1000, 9999)} 00 (ungültig, synthetisch)\n\n"
    for _ in range(r.randint(3, 6)):
        text += f"{r.randint(1, 28):02d}.{r.randint(1, 12):02d}.  {r.choice(['Lastschrift Strom', 'Kartenzahlung Markt', 'Gutschrift', 'Dauerauftrag'])}  {euro(r, r.uniform(5, 400))}\n"
    text += f"\n{r.choice(['Neuer Kontostand', 'Saldo neu', 'Endsaldo'])}: {euro(r, saldo)}\n"
    return Dokument(k, "kontoauszug", text, {"kontoinhaber": inhaber, "endsaldo": f"{saldo:.2f}"})


def fall_erzeugen(r: random.Random, nr: int, fehlquote: float = 0.25) -> Fall:
    person = (r.choice(VORNAMEN), r.choice(NACHNAMEN))
    merkmale = {"erwerbstaetig": r.random() < .55, "miete": r.random() < .85, "personen": r.randint(1, 5)}
    art = r.choice(["Weiterbewilligungsantrag", "Veränderungsmitteilung"])
    f = Fall(f"SYN-F{nr:04d}", art, merkmale)
    k = lambda i: f"SYN-F{nr:04d}-D{i}"  # noqa: E731
    docs = [_antrag(r, k(1), person, merkmale, art), _konto(r, k(2), person)]
    if merkmale["erwerbstaetig"]:
        docs.append(_lohn(r, k(3), person))
    if merkmale["miete"]:
        docs.append(_miete(r, k(4), person))
    # ein Nachweis fehlt (nie der Antrag selbst): das soll die Vollständigkeitsprüfung finden
    if len(docs) > 2 and r.random() < fehlquote:
        weg = r.choice(docs[1:])
        docs.remove(weg)
        f.fehlend.append(weg.art)
    f.dokumente = docs
    return f


def faelle(n: int, startwert: int = 20261102) -> list[Fall]:
    r = random.Random(startwert)
    return [fall_erzeugen(r, i + 1) for i in range(n)]
