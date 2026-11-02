import pytest

from app import dienst
from conftest import Orakel


@pytest.fixture
def fall(con, konf, nutzer):
    f = con.execute("SELECT f.id FROM fall f WHERE jobcenter_id = 'JC-A' AND EXISTS "
                    "(SELECT 1 FROM dokument d WHERE d.fall_id = f.id AND d.text LIKE '%Abrechnungsmonat%') LIMIT 1").fetchone()["id"]
    dienst.analysieren(con, Orakel(), konf, nutzer["sb.a"], f, "test")
    return f


def test_kein_statuswechsel_ohne_bestaetigung(con, konf, nutzer, fall):
    with pytest.raises(ValueError, match="noch nicht entschieden"):
        dienst.prueffertig(con, konf, nutzer["sb.a"], fall)
    with pytest.raises(ValueError, match="Export erst"):
        dienst.export(con, konf, nutzer["sb.a"], fall)


def test_unbelegt_nicht_uebernehmbar(con, nutzer, fall):
    v = con.execute("SELECT * FROM vorschlag WHERE fall_id = ? AND feld = 'netto'", (fall,)).fetchone()
    assert v["belegt"] == 0  # das Orakel liefert hier absichtlich eine falsche Fundstelle
    with pytest.raises(ValueError, match="Unbelegte"):
        dienst.entscheiden(con, nutzer["sb.a"], v["id"], "uebernommen")
    with pytest.raises(ValueError, match="Wert nötig"):
        dienst.entscheiden(con, nutzer["sb.a"], v["id"], "korrigiert", " ")


def test_ablauf_bis_export(con, konf, nutzer, fall):
    for v in con.execute("SELECT * FROM vorschlag WHERE fall_id = ?", (fall,)).fetchall():
        if v["belegt"]:
            dienst.entscheiden(con, nutzer["sb.a"], v["id"], "uebernommen")
        else:
            dienst.entscheiden(con, nutzer["sb.a"], v["id"], "korrigiert", "1000.00")
    ergebnis = dienst.prueffertig(con, konf, nutzer["sb.a"], fall)
    assert isinstance(ergebnis["fehlend"], list)
    ex = dienst.export(con, konf, nutzer["sb.a"], fall)
    assert ex["status"] == "prueffertig" and all(a["von"] == "sb.a" for a in ex["angaben"])
    with pytest.raises(ValueError, match="bereits"):
        v = con.execute("SELECT id FROM vorschlag WHERE fall_id = ? LIMIT 1", (fall,)).fetchone()
        dienst.entscheiden(con, nutzer["sb.a"], v["id"], "verworfen")
    aktionen = [z["aktion"] for z in con.execute("SELECT aktion FROM protokoll WHERE daten LIKE ?", (f"%{fall}%",))]
    assert {"ki_vorschlag", "entscheidung", "prueffertig", "export"} <= set(aktionen)
