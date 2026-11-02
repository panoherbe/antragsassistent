"""Lädt SGB II und SGB I als XML von gesetze-im-internet.de und schreibt normen.jsonl (ein Eintrag je Absatz).

Gesetzestexte sind amtliche Werke (§ 5 UrhG) und frei nutzbar. Die Rohdatei wird vor dem Einlesen mit SHA-256
abgelegt; normen.jsonl nennt Quelle, Abrufdatum und Prüfsumme.

    python -m normen.laden            # schreibt normen/normen.jsonl und normen/quelle.json
"""
import hashlib
import io
import json
import re
import sys
import zipfile
import xml.etree.ElementTree as ET
from datetime import date
from pathlib import Path

import httpx

HIER = Path(__file__).resolve().parent
QUELLEN = {"SGB II": "https://www.gesetze-im-internet.de/sgb_2/xml.zip",
           "SGB I": "https://www.gesetze-im-internet.de/sgb_1/xml.zip"}
# aus dem SGB I nur die Mitwirkungspflichten (§§ 60 bis 67), die bei der Antragsbearbeitung gebraucht werden
AUSWAHL = {"SGB I": lambda nr: 60 <= nr <= 67}


def _text(el) -> str:
    return " ".join("".join(el.itertext()).split())


def absaetze(xml: bytes, gesetz: str):
    for norm in ET.fromstring(xml).iter("norm"):
        meta = norm.find("metadaten")
        enbez = meta.findtext("enbez") if meta is not None else None
        if not enbez or not enbez.startswith("§"):
            continue
        m = re.match(r"§\s*(\d+)([a-z]?)", enbez)
        if not m or (gesetz in AUSWAHL and not AUSWAHL[gesetz](int(m.group(1)))):
            continue
        titel = _text(meta.find("titel")) if meta.find("titel") is not None else ""
        if titel in ("(weggefallen)", "") and norm.find(".//Content") is None:
            continue
        content = norm.find(".//textdaten/text/Content")
        if content is None:
            continue
        ps = [_text(p) for p in content.findall("P")] or [_text(content)]
        for i, p in enumerate([p for p in ps if p], 1):
            mabs = re.match(r"\((\d+[a-z]?)\)", p)
            yield {"id": f"{gesetz} {enbez} Abs. {mabs.group(1) if mabs else i}", "gesetz": gesetz,
                   "paragraf": f"{gesetz} § {m.group(1)}{m.group(2)}", "titel": titel, "text": p}


def main() -> None:
    quelle, zeilen = {"abgerufen": date.today().isoformat(), "dateien": {}}, []
    roh = HIER / "roh"
    roh.mkdir(exist_ok=True)
    for gesetz, url in QUELLEN.items():
        daten = httpx.get(url, timeout=60, follow_redirects=True).content
        sha = hashlib.sha256(daten).hexdigest()
        (roh / f"{sha}.zip").write_bytes(daten)  # Rohdatei zuerst ablegen, dann lesen
        quelle["dateien"][gesetz] = {"url": url, "sha256": sha, "bytes": len(daten)}
        with zipfile.ZipFile(io.BytesIO(daten)) as z:
            xml = z.read(next(n for n in z.namelist() if n.endswith(".xml")))
        zeilen += list(absaetze(xml, gesetz))
    with open(HIER / "normen.jsonl", "w", encoding="utf-8") as f:
        for z in zeilen:
            f.write(json.dumps(z, ensure_ascii=False) + "\n")
    (HIER / "quelle.json").write_text(json.dumps(quelle, ensure_ascii=False, indent=2))
    print(f"{len(zeilen)} Absätze aus {len({z['paragraf'] for z in zeilen})} Paragrafen", file=sys.stderr)


if __name__ == "__main__":
    main()
