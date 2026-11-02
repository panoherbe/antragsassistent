import pytest

from app import regeln, synth


def test_vollstaendigkeit_gegen_wahrheit(konf):
    faelle = synth.faelle(300, startwert=7)
    assert sum(1 for f in faelle if f.fehlend) > 30
    for f in faelle:
        arten = {d.art for d in f.dokumente}
        assert regeln.fehlende_unterlagen(konf, f.antragsart, f.merkmale, arten) == f.fehlend


def test_plausibilitaet(konf):
    h = regeln.plausibilitaet(konf, {("lohnabrechnung", "netto"): "2000.00", ("lohnabrechnung", "brutto"): "1500.00",
                                     ("antrag", "name"): "Anna Becker", ("kontoauszug", "kontoinhaber"): "anna  becker"})
    assert [x["regel"] for x in h] == ["netto_hoechstens_brutto"]


def test_kein_freier_ausdruck(tmp_path, konf):
    p = tmp_path / "k.yaml"
    p.write_text("version: x\nregeln:\n  - {id: boese, text: x, pruefe: \"__import__('os').system('id')\"}\n")
    with pytest.raises(ValueError):
        regeln.laden(p)
