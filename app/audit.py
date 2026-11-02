"""Prüfprotokoll: nur erweiterbar, jeder Eintrag sichert per SHA-256 den vorigen (Hash-Kette).

Eine nachträgliche Änderung an irgendeinem Eintrag fällt bei `pruefen()` auf, weil sein Hash oder der Verweis des
Nachfolgers nicht mehr stimmt. Zusätzlich verbieten Trigger in der Datenbank UPDATE und DELETE.
"""
import hashlib
import json
import sqlite3
import threading
from datetime import datetime, timezone

START = "0" * 64
_sperre = threading.Lock()


def _hash(vorgaenger: str, nr: int, zeit: str, benutzer, jobcenter_id, aktion: str, daten: str) -> str:
    roh = json.dumps([vorgaenger, nr, zeit, benutzer, jobcenter_id, aktion, daten], ensure_ascii=False)
    return hashlib.sha256(roh.encode("utf-8")).hexdigest()


def eintragen(con: sqlite3.Connection, aktion: str, daten: dict, benutzer: str | None = None,
              jobcenter_id: str | None = None) -> str:
    with _sperre:
        letzter = con.execute("SELECT nr, hash FROM protokoll ORDER BY nr DESC LIMIT 1").fetchone()
        nr = (letzter["nr"] + 1) if letzter else 1
        vorgaenger = letzter["hash"] if letzter else START
        zeit = datetime.now(timezone.utc).isoformat(timespec="milliseconds")
        roh = json.dumps(daten, ensure_ascii=False, sort_keys=True)
        h = _hash(vorgaenger, nr, zeit, benutzer, jobcenter_id, aktion, roh)
        con.execute("INSERT INTO protokoll (nr, zeit, benutzer, jobcenter_id, aktion, daten, vorgaenger, hash) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?, ?)", (nr, zeit, benutzer, jobcenter_id, aktion, roh, vorgaenger, h))
        return h


def pruefen(con: sqlite3.Connection) -> tuple[bool, int, str]:
    """(in Ordnung, Anzahl geprüfter Einträge, Meldung)."""
    vorgaenger, n = START, 0
    for z in con.execute("SELECT * FROM protokoll ORDER BY nr"):
        n += 1
        if z["nr"] != n:
            return False, n, f"Lücke vor Eintrag {z['nr']}"
        if z["vorgaenger"] != vorgaenger:
            return False, n, f"Eintrag {z['nr']}: Verweis auf den Vorgänger stimmt nicht"
        if _hash(z["vorgaenger"], z["nr"], z["zeit"], z["benutzer"], z["jobcenter_id"], z["aktion"], z["daten"]) != z["hash"]:
            return False, n, f"Eintrag {z['nr']}: Inhalt wurde verändert"
        vorgaenger = z["hash"]
    return True, n, f"{n} Einträge, Kette vollständig"
