"""Anzeige für Menschen: Feldnamen, Beträge, Status und Protokolleinträge in Alltagsdeutsch.

Nur Darstellung. Gespeichert und exportiert werden weiter die technischen Werte (z. B. Betrag „1234.50“).
"""
import json
import re

from markupsafe import Markup, escape

FELD = {
    "name": "Name", "geburtsdatum": "Geburtsdatum", "personen_bg": "Personen in der Bedarfsgemeinschaft",
    "arbeitgeber": "Arbeitgeber", "monat": "Abrechnungsmonat", "brutto": "Bruttolohn", "netto": "Nettolohn",
    "kaltmiete": "Kaltmiete", "nebenkosten": "Nebenkosten", "heizkosten": "Heizkosten", "wohnflaeche": "Wohnfläche",
    "kontoinhaber": "Kontoinhaber/in", "endsaldo": "Kontostand am Ende",
}
DOKUMENT = {"antrag": "Antrag", "lohnabrechnung": "Lohnabrechnung", "mietbescheinigung": "Mietbescheinigung",
            "kontoauszug": "Kontoauszug", "sonstiges": "Sonstiges Dokument"}
STATUS = {"eingang": "Neu", "in_pruefung": "In Bearbeitung", "prueffertig": "Fertig zur Prüfung"}
ROLLE = {"sachbearbeitung": "Sachbearbeitung", "pruefung": "Prüfung", "administration": "Administration"}
ENTSCHEIDUNG = {"uebernommen": "übernommen", "korrigiert": "korrigiert", "verworfen": "verworfen"}
BETRAG = {"brutto", "netto", "kaltmiete", "nebenkosten", "heizkosten", "endsaldo"}
ZITAT = re.compile(r"\[(SGB I{1,2}) §\s*(\d+[a-z]?)([^\]]*)\]")


def feld(f: str) -> str:
    return FELD.get(f, f)


def wert(f: str, w) -> str:
    """„1234.50“ → „1.234,50 €“, „54“ (Wohnfläche) → „54 m²“; sonst unverändert."""
    if w in (None, ""):
        return "–"
    w = str(w)
    if f in BETRAG and re.fullmatch(r"-?\d+(\.\d+)?", w):
        s = f"{float(w):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        return f"{s} €"
    if f == "wohnflaeche" and w.isdigit():
        return f"{w} m²"
    return w


def person(text: str | None) -> str:
    """Name der antragstellenden Person aus dem Antrag („Popescu, Ivana“ → „Ivana Popescu“)."""
    m = re.search(r"^(?:Name, Vorname|Antragstellende Person):\s*(.+)$", text or "", re.M)
    if not m:
        return "Antrag"
    teile = [t.strip() for t in m.group(1).split(",")]
    return " ".join(reversed(teile)) if len(teile) == 2 else m.group(1).strip()


def zeilen(text: str, fundstellen: list[str]) -> list[dict]:
    """Dokumentzeilen ohne Kopfzeile; markiert sind Zeilen, die eine geprüfte Fundstelle enthalten."""
    def norm(s):
        return " ".join(s.split()).casefold()
    fund = [norm(f) for f in fundstellen if f]
    out = []
    for z in text.splitlines()[1:]:
        if z.strip() and set(z.strip()) == {"="}:
            continue
        out.append({"text": z, "markiert": bool(z.strip()) and any(f in norm(z) for f in fund)})
    return out


def kopf(text: str) -> str:
    return text.splitlines()[0] if text else ""


def zitate(antwort: str) -> Markup:
    """Antworttext als HTML: Fundstellen „[SGB II § 41 …]“ werden zu hervorgehobenen Marken (Text vorher maskiert)."""
    teile, start = [], 0
    for m in ZITAT.finditer(antwort):
        teile.append(escape(antwort[start:m.start()]))
        teile.append(Markup('<span class="zitat">{} § {}{}</span>').format(m.group(1), m.group(2), m.group(3)))
        start = m.end()
    teile.append(escape(antwort[start:]))
    return Markup("").join(teile)


def protokoll(aktion: str, daten: str) -> str:
    """Ein Protokolleintrag als Satz."""
    try:
        d = json.loads(daten)
    except ValueError:
        d = {}
    if aktion == "entscheidung":
        was = ENTSCHEIDUNG.get(d.get("entscheidung"), d.get("entscheidung"))
        zusatz = f" auf {wert(d.get('feld', ''), d.get('endwert'))}" if d.get("entscheidung") == "korrigiert" else ""
        return f"„{feld(d.get('feld', ''))}“ {was}{zusatz} ({d.get('fall', '')})"
    if aktion == "ki_vorschlag":
        return (f"KI-Vorschlag: {DOKUMENT.get(d.get('dokumentart'), d.get('dokumentart'))} {d.get('dokument', '')}, "
                f"{len(d.get('felder', []))} Angaben · Modell {d.get('modell', '')} · Regeln {d.get('regeln', '')}")
    texte = {"prueffertig": f"Fall {d.get('fall', '')} fertig zur Prüfung",
             "export": f"Ergebnis von {d.get('fall', '')} exportiert",
             "assistent_frage": f"Frage zum SGB II: „{d.get('frage', '')}“",
             "dokument_eingang": f"Nachweis {d.get('dokument', '')} eingegangen",
             "dokument_abgewiesen": f"Dokument abgewiesen: {d.get('grund', '')}",
             "anmeldung": "Anmeldung", "anmeldung_fehlgeschlagen": "Anmeldung fehlgeschlagen"}
    return texte.get(aktion, aktion)


def zeit(iso: str) -> str:
    """„2026-11-11T15:03:12.123+00:00“ → „11.11.2026, 15:03 UTC“."""
    m = re.match(r"(\d{4})-(\d\d)-(\d\d)T(\d\d):(\d\d)", iso or "")
    return f"{m[3]}.{m[2]}.{m[1]}, {m[4]}:{m[5]} UTC" if m else iso


def dauer(sekunden: float) -> str:
    """12.3 → „12 Sekunden“, 95 → „1 Minute 35 Sekunden“."""
    s = round(sekunden)
    if s < 60:
        return f"{s} Sekunden"
    m, s = divmod(s, 60)
    return f"{m} {'Minute' if m == 1 else 'Minuten'} {s} Sekunden" if s else f"{m} {'Minute' if m == 1 else 'Minuten'}"
