import re

import pytest

from app import dienst, synth


def test_kennung_und_keine_echte_iban():
    for f in synth.faelle(50):
        for d in f.dokumente:
            assert d.text.startswith(dienst.KENNUNG)
            assert not re.search(r"DE(?!00)\d{2}", d.text)


def test_dokument_ohne_kennung_abgewiesen(con):
    with pytest.raises(ValueError):
        dienst.dokument_annehmen(con, "JC-A", "SYN-F0001", "echt.txt", "Lohnabrechnung Max Mustermann ...")
    assert con.execute("SELECT count(*) FROM protokoll WHERE aktion = 'dokument_abgewiesen'").fetchone()[0] == 1


def test_deterministisch():
    assert [d.text for d in synth.faelle(3)[0].dokumente] == [d.text for d in synth.faelle(3)[0].dokumente]
