import os
import sys
import tempfile
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
os.environ.setdefault("DATENVERZEICHNIS", tempfile.mkdtemp(prefix="antragsassistent-test-"))
os.environ.setdefault("DEMO_PASSWORT", "nur-fuer-tests")

from app import config, db, dienst, extraktion, regeln, synth  # noqa: E402


class Orakel:
    """Ersatz für das Sprachmodell: kennt die Wahrheit der synthetischen Dokumente und sucht die passende Zeile.
    `falsch` nennt Felder, für die es absichtlich eine nicht vorhandene Fundstelle liefert."""
    modell = "orakel"

    def __init__(self, n=12, falsch=("netto",)):
        self.wahr = {d.kennung: d for f in synth.faelle(n) for d in f.dokumente}
        self.falsch = set(falsch)

    def json_antwort(self, system, nutzer, schema):
        kennung = nutzer.split("Kennung ", 1)[1].split()[0]
        d = self.wahr[kennung]
        felder = []
        for feld, wert in d.wahr.items():
            zeile = next((z for z in d.text.splitlines() if extraktion.belegt(feld, wert, z, d.text)), "")
            if feld in self.falsch:
                zeile = f"{feld}: 9999,99 €"
            felder.append({"feld": feld, "wert": wert, "fundstelle": zeile})
        return {"dokumentart": d.art, "felder": felder}, 0.0


@pytest.fixture
def con(tmp_path):
    c = db.verbinden(tmp_path / "t.sqlite3")
    dienst.einrichten(c, "pw")
    dienst.demo_faelle(c, 12)
    return c


@pytest.fixture
def konf():
    return regeln.laden(config.BASIS / "konfiguration" / "unterlagen.yaml")


@pytest.fixture
def nutzer(con):
    return {k: dienst.benutzer(con, k) for k in ("sb.a", "sb.b", "pruef.a", "admin")}
