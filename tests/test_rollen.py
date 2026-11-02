import pytest

from app import dienst


def test_mandantentrennung(con, nutzer):
    eigene = {f["jobcenter_id"] for f in dienst.faelle(con, nutzer["sb.a"])}
    assert eigene == {"JC-A"}
    fremd = con.execute("SELECT id FROM fall WHERE jobcenter_id = 'JC-B' LIMIT 1").fetchone()["id"]
    with pytest.raises(dienst.Verboten):
        dienst.ansicht(con, {}, nutzer["sb.a"], fremd)


def test_pruefung_entscheidet_nicht(con, konf, nutzer):
    fall = con.execute("SELECT id FROM fall WHERE jobcenter_id = 'JC-A' LIMIT 1").fetchone()["id"]
    with pytest.raises(dienst.Verboten):
        dienst.analysieren(con, None, konf, nutzer["pruef.a"], fall, "v")


def test_administration_sieht_keine_faelle(con, nutzer):
    with pytest.raises(dienst.Verboten):
        dienst.faelle(con, nutzer["admin"])


def test_falsches_passwort(con):
    assert dienst.anmelden(con, "sb.a", "falsch") is None
    assert dienst.anmelden(con, "sb.a", "pw")["kennung"] == "sb.a"
