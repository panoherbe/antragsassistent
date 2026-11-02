import pytest

from app import config, suche

PFAD = config.BASIS / "normen" / "normen.jsonl"


@pytest.mark.skipif(not PFAD.exists(), reason="normen.jsonl fehlt (python -m normen.laden)")
def test_bm25_findet_unterkunft():
    n = suche.Normen(PFAD)
    treffer = [t["paragraf"] for t in n.suchen("Bedarfe für Unterkunft und Heizung", "bm25", k=3)]
    assert "SGB II § 22" in treffer
