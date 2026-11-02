"""Dokumentart bestimmen und Angaben mit Fundstelle auslesen; jede Angabe wird gegen den Dokumenttext geprüft.

Das Modell liefert je Feld einen Wert und die Zeile, aus der er stammt. „Belegt“ ist eine Angabe nur, wenn diese Zeile
wörtlich im Dokument steht und den Wert enthält. Unbelegte Angaben bleiben sichtbar, sind aber markiert und müssen
von Hand eingetragen werden. Das Modell entscheidet nichts; es macht Vorschläge.
"""
import re

BETRAGSFELDER = {"brutto", "netto", "kaltmiete", "nebenkosten", "heizkosten", "endsaldo"}
ZAHLFELDER = {"personen_bg", "wohnflaeche"}
ZAHL = re.compile(r"-?\d{1,3}(?:\.\d{3})+(?:,\d{1,2})?|-?\d+(?:[.,]\d{1,2})?")

SYSTEM = (
    "Du liest synthetische Testdokumente aus der Antragsbearbeitung eines Jobcenters. Bestimme die Dokumentart und "
    "lies die verlangten Felder aus. Regeln: Erfinde nichts. Gib zu jedem Feld als 'fundstelle' die vollständige "
    "Zeile aus dem Dokument zurück, in der der Wert steht, buchstabengetreu kopiert. Steht ein Feld nicht im "
    "Dokument, setze wert und fundstelle auf leere Zeichenketten. 'wert' enthält nur den Wert, nie die Beschriftung. "
    "Lies nur die Felder der bestimmten Dokumentart. Format der Werte: Beträge als Zahl mit Punkt und "
    "zwei Nachkommastellen ohne Währung (z. B. 1234.50), Datum als TT.MM.JJJJ, Namen als 'Vorname Nachname', "
    "Monat als 'Monatsname JJJJ', Anzahl und Wohnfläche als ganze Zahl."
)


def schema(konf: dict) -> dict:
    alle = sorted({f for fs in konf["felder"].values() for f in fs})
    return {
        "type": "object",
        "properties": {
            "dokumentart": {"type": "string", "enum": sorted(konf["felder"]) + ["sonstiges"]},
            "felder": {"type": "array", "items": {
                "type": "object",
                "properties": {"feld": {"type": "string", "enum": alle}, "wert": {"type": "string"},
                               "fundstelle": {"type": "string"}},
                "required": ["feld", "wert", "fundstelle"]}},
        },
        "required": ["dokumentart", "felder"],
    }


def anweisung(konf: dict, text: str) -> str:
    """Dokumentarten mit ihren Feldern und deren Bedeutung, je Dokumentart gruppiert (Prompt extraktion-v3)."""
    besch = konf.get("beschreibung", {})
    teile = []
    for art, fs in konf["felder"].items():
        felder = "; ".join(f"{f} = {besch[f]}" if f in besch else f for f in fs)
        teile.append(f"- {art}: {konf['dokumentarten'][art]}. Felder: {felder}")
    return "Mögliche Dokumentarten und ihre Felder:\n" + "\n".join(teile) + f"\n\nDokument:\n<<<\n{text}\n>>>"


def _norm(s: str) -> str:
    return " ".join(str(s).split()).casefold()


def betrag(s: str) -> float | None:
    s = str(s).replace("€", "").replace("EUR", "").replace("Euro", "").strip()
    m = ZAHL.search(s)
    if not m:
        return None
    z = m.group(0)
    if "," in z:  # deutsches Format
        z = z.replace(".", "").replace(",", ".")
    elif re.fullmatch(r"-?\d{1,3}(?:\.\d{3})+", z):
        z = z.replace(".", "")
    try:
        return float(z)
    except ValueError:
        return None


def gleich(feld: str, a: str, b: str) -> bool:
    """Fachlich gleicher Wert (für Belegprüfung und Messung)."""
    if feld in BETRAGSFELDER or feld in ZAHLFELDER:
        x, y = betrag(a), betrag(b)
        return x is not None and y is not None and abs(x - y) < 0.005
    if feld in {"name", "kontoinhaber"}:
        return sorted(_norm(a).replace(",", " ").split()) == sorted(_norm(b).replace(",", " ").split())
    return _norm(a) == _norm(b)


def belegt(feld: str, wert: str, fundstelle: str, dokument: str) -> bool:
    if not wert or not fundstelle or _norm(fundstelle) not in _norm(dokument):
        return False
    if feld in BETRAGSFELDER or feld in ZAHLFELDER:
        return any(gleich(feld, wert, z) for z in ZAHL.findall(fundstelle))
    if feld in {"name", "kontoinhaber"}:
        return all(t in _norm(fundstelle) for t in _norm(wert).split())
    return _norm(wert) in _norm(fundstelle)


def auslesen(modell, konf: dict, text: str) -> tuple[str, list[dict], float]:
    """(dokumentart, [{feld, wert, fundstelle, belegt}], Sekunden)."""
    roh, dauer = modell.json_antwort(SYSTEM, anweisung(konf, text), schema(konf))
    art = roh.get("dokumentart", "sonstiges")
    erlaubt = konf["felder"].get(art, [])
    gesehen, felder = set(), []
    for f in roh.get("felder", []):
        if f.get("feld") in erlaubt and f["feld"] not in gesehen:
            gesehen.add(f["feld"])
            wert = str(f.get("wert", "")).strip()
            if f["feld"] in BETRAGSFELDER and betrag(wert) is not None:
                wert = f"{betrag(wert):.2f}"
            felder.append({"feld": f["feld"], "wert": wert, "fundstelle": str(f.get("fundstelle", "")).strip(),
                           "belegt": belegt(f["feld"], wert, str(f.get("fundstelle", "")), text)})
    for fehlt in [f for f in erlaubt if f not in gesehen]:
        felder.append({"feld": fehlt, "wert": "", "fundstelle": "", "belegt": False})
    return art, felder, dauer
