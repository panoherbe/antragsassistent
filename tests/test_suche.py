import pytest

from app import config, suche

PFAD = config.BASIS / "normen" / "normen.jsonl"


@pytest.mark.skipif(not PFAD.exists(), reason="normen.jsonl fehlt (python -m normen.laden)")
def test_bm25_findet_unterkunft():
    n = suche.Normen(PFAD)
    treffer = [t["paragraf"] for t in n.suchen("Bedarfe für Unterkunft und Heizung", "bm25", k=3)]
    assert "SGB II § 22" in treffer


class Einbettung:
    """Ersatz für bge-m3: ein kleiner Vektor aus Wortzählungen; zählt die Aufrufe."""
    einbettungsmodell = "test"

    def __init__(self):
        self.aufrufe = 0

    def einbetten(self, texte):
        self.aufrufe += 1
        return [[t.count("Unterkunft") + 1.0, t.count("Heizung") + 1.0, 1.0] for t in texte]


@pytest.mark.skipif(not PFAD.exists(), reason="normen.jsonl fehlt (python -m normen.laden)")
def test_dichte_suche_laedt_einbettungen_beim_ersten_bedarf(tmp_path):
    # Die Weboberfläche ruft die dichte Suche ohne vorheriges vektoren_laden auf (Fehler bis 03.11.2026: HTTP 500)
    n, m = suche.Normen(PFAD), Einbettung()
    n.vektoren_bereit(m, tmp_path / "vektoren.json")
    aufrufe = m.aufrufe
    n.vektoren_bereit(m, tmp_path / "vektoren.json")
    assert m.aufrufe == aufrufe
    assert len(n.suchen("Unterkunft und Heizung", "dicht", m, k=3)) == 3
