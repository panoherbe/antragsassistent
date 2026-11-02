import sqlite3

import pytest

from app import audit


def test_kette_in_ordnung(con):
    ok, n, _ = audit.pruefen(con)
    assert ok and n > 0  # Dokumenteingänge der Demo-Fälle


def test_update_und_delete_gesperrt(con):
    with pytest.raises(sqlite3.IntegrityError):
        con.execute("UPDATE protokoll SET aktion = 'x' WHERE nr = 1")
    with pytest.raises(sqlite3.IntegrityError):
        con.execute("DELETE FROM protokoll WHERE nr = 1")


def test_manipulation_wird_erkannt(con):
    # Angreifer mit Datenbankzugriff entfernt den Trigger und ändert einen alten Eintrag
    con.execute("DROP TRIGGER protokoll_nur_anhaengen_u")
    con.execute("UPDATE protokoll SET daten = '{\"fall\": \"gefaelscht\"}' WHERE nr = 3")
    ok, n, meldung = audit.pruefen(con)
    assert not ok and n == 3 and "verändert" in meldung
