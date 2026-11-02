"""Anmeldung und Rollenmodell.

Rollen (minimale Rechte):
  sachbearbeitung  sieht die Fälle des eigenen Jobcenters, entscheidet über Vorschläge, setzt „prüffertig“
  pruefung         sieht Fälle und Prüfprotokoll des eigenen Jobcenters, entscheidet nichts
  administration   prüft die Protokollkette, sieht keine Fallinhalte

Passwörter: PBKDF2-SHA256 mit Salz. Sitzung: HMAC-signiertes Cookie mit Ablaufzeit.
"""
import base64
import hashlib
import hmac
import json
import os
import time

RECHTE = {
    "fall_lesen": {"sachbearbeitung", "pruefung"},
    "entscheiden": {"sachbearbeitung"},
    "protokoll_lesen": {"pruefung"},
    "kette_pruefen": {"pruefung", "administration"},
    "assistent": {"sachbearbeitung", "pruefung"},
}
SITZUNG_SEKUNDEN = 8 * 3600


def darf(rolle: str, recht: str) -> bool:
    return rolle in RECHTE[recht]


def pw_hash(passwort: str, salz: bytes | None = None) -> str:
    salz = salz or os.urandom(16)
    h = hashlib.pbkdf2_hmac("sha256", passwort.encode(), salz, 200_000)
    return f"pbkdf2${salz.hex()}${h.hex()}"


def pw_pruefen(passwort: str, gespeichert: str) -> bool:
    _, salz, h = gespeichert.split("$")
    return hmac.compare_digest(pw_hash(passwort, bytes.fromhex(salz)).split("$")[2], h)


def sitzung_ausstellen(kennung: str, schluessel: str) -> str:
    nutzlast = base64.urlsafe_b64encode(json.dumps({"k": kennung, "b": int(time.time()) + SITZUNG_SEKUNDEN}).encode())
    sig = hmac.new(schluessel.encode(), nutzlast, hashlib.sha256).hexdigest()
    return f"{nutzlast.decode()}.{sig}"


def sitzung_lesen(wert: str | None, schluessel: str) -> str | None:
    if not wert or "." not in wert:
        return None
    nutzlast, sig = wert.rsplit(".", 1)
    if not hmac.compare_digest(hmac.new(schluessel.encode(), nutzlast.encode(), hashlib.sha256).hexdigest(), sig):
        return None
    daten = json.loads(base64.urlsafe_b64decode(nutzlast))
    return daten["k"] if daten["b"] > time.time() else None
