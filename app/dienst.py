"""Fachlogik: Fälle, Dokumente, Vorschläge, Entscheidungen. Jede Funktion prüft Rolle und Jobcenter.

Grundsatz: Das System entscheidet nichts. Ein Fall wird erst „prüffertig“, wenn eine angemeldete Person jede
Angabe einzeln übernommen, korrigiert oder verworfen hat. Eine Sammelübernahme gibt es nicht.
"""
import hashlib
import json
from datetime import datetime, timezone

from . import audit, auth, extraktion, regeln, synth

KENNUNG = "SYNTHETISCHES TESTDOKUMENT · Kennung SYN-"
JOBCENTER = [("JC-A", "Jobcenter Musterkreis (fiktiv)"), ("JC-B", "Jobcenter Beispielstadt (fiktiv)")]
DEMO_NUTZER = [("sb.a", "Sachbearbeitung A", "sachbearbeitung", "JC-A"),
               ("sb.b", "Sachbearbeitung B", "sachbearbeitung", "JC-B"),
               ("pruef.a", "Prüfung A", "pruefung", "JC-A"),
               ("admin", "Administration", "administration", None)]


class Verboten(Exception):
    pass


def jetzt() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def einrichten(con, demo_passwort: str) -> None:
    for jid, name in JOBCENTER:
        con.execute("INSERT OR IGNORE INTO jobcenter VALUES (?, ?)", (jid, name))
    if demo_passwort:
        for kennung, name, rolle, jc in DEMO_NUTZER:
            if not con.execute("SELECT 1 FROM benutzer WHERE kennung = ?", (kennung,)).fetchone():
                con.execute("INSERT INTO benutzer VALUES (?, ?, ?, ?, ?)",
                            (kennung, name, rolle, jc, auth.pw_hash(demo_passwort)))


def benutzer(con, kennung: str | None):
    return con.execute("SELECT * FROM benutzer WHERE kennung = ?", (kennung,)).fetchone() if kennung else None


def anmelden(con, kennung: str, passwort: str):
    b = benutzer(con, kennung)
    ok = b is not None and auth.pw_pruefen(passwort, b["pw_hash"])
    audit.eintragen(con, "anmeldung" if ok else "anmeldung_fehlgeschlagen", {"kennung": kennung}, kennung if ok else None,
                    b["jobcenter_id"] if ok else None)
    return b if ok else None


def _pruefe(b, recht: str, jobcenter_id: str | None = None) -> None:
    if b is None or not auth.darf(b["rolle"], recht):
        raise Verboten(recht)
    if jobcenter_id is not None and b["jobcenter_id"] != jobcenter_id:
        raise Verboten("anderes Jobcenter")


def dokument_annehmen(con, jobcenter_id: str, fall_id: str, dateiname: str, text: str) -> str:
    erste = text.splitlines()[0] if text else ""
    if not erste.startswith(KENNUNG):
        audit.eintragen(con, "dokument_abgewiesen", {"fall": fall_id, "datei": dateiname, "grund": "keine Kennung"},
                        jobcenter_id=jobcenter_id)
        raise ValueError("Nur synthetische Testdokumente mit Kennung werden angenommen.")
    kennung = erste.split("Kennung ", 1)[1].strip()
    sha = hashlib.sha256(text.encode()).hexdigest()
    con.execute("INSERT INTO dokument (id, fall_id, jobcenter_id, dateiname, text, sha256) VALUES (?, ?, ?, ?, ?, ?)",
                (kennung, fall_id, jobcenter_id, dateiname, text, sha))
    audit.eintragen(con, "dokument_eingang", {"fall": fall_id, "dokument": kennung, "sha256": sha},
                    jobcenter_id=jobcenter_id)
    return kennung


def demo_faelle(con, anzahl: int, startwert: int = 20261102) -> int:
    neu = 0
    for i, f in enumerate(synth.faelle(anzahl, startwert)):
        if con.execute("SELECT 1 FROM fall WHERE id = ?", (f.kennung,)).fetchone():
            continue
        jc = JOBCENTER[i % 2][0]
        con.execute("INSERT INTO fall (id, jobcenter_id, antragsart, merkmale, angelegt) VALUES (?, ?, ?, ?, ?)",
                    (f.kennung, jc, f.antragsart, json.dumps(f.merkmale), jetzt()))
        for d in f.dokumente:
            dokument_annehmen(con, jc, f.kennung, f"{d.kennung}.txt", d.text)
        neu += 1
    return neu


def faelle(con, b) -> list:
    _pruefe(b, "fall_lesen")
    return con.execute("SELECT f.*, (SELECT count(*) FROM dokument d WHERE d.fall_id = f.id) AS dokumente, "
                       "(SELECT count(*) FROM vorschlag v WHERE v.fall_id = f.id AND v.entscheidung IS NULL) AS offen, "
                       "(SELECT d.text FROM dokument d WHERE d.fall_id = f.id ORDER BY d.id LIMIT 1) AS antrag_text "
                       "FROM fall f WHERE f.jobcenter_id = ? ORDER BY f.id", (b["jobcenter_id"],)).fetchall()


def _fall(con, b, fall_id: str, recht: str = "fall_lesen"):
    f = con.execute("SELECT * FROM fall WHERE id = ?", (fall_id,)).fetchone()
    if f is None:
        raise KeyError(fall_id)
    _pruefe(b, recht, f["jobcenter_id"])
    return f


def analysieren(con, modell, konf: dict, b, fall_id: str, prompt_version: str) -> dict:
    f = _fall(con, b, fall_id, "entscheiden")
    dauer = []
    for d in con.execute("SELECT * FROM dokument WHERE fall_id = ? AND dokumentart IS NULL", (fall_id,)).fetchall():
        art, felder, sek = extraktion.auslesen(modell, konf, d["text"])
        dauer.append(sek)
        con.execute("UPDATE dokument SET dokumentart = ? WHERE id = ?", (art, d["id"]))
        for x in felder:
            con.execute("INSERT OR REPLACE INTO vorschlag (dokument_id, fall_id, jobcenter_id, feld, wert, fundstelle, "
                        "belegt, modell, prompt_version) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                        (d["id"], fall_id, f["jobcenter_id"], x["feld"], x["wert"], x["fundstelle"], int(x["belegt"]),
                         modell.modell, prompt_version))
        audit.eintragen(con, "ki_vorschlag", {"fall": fall_id, "dokument": d["id"], "sha256": d["sha256"],
                                              "dokumentart": art, "modell": modell.modell, "prompt": prompt_version,
                                              "sekunden": round(sek, 2),
                                              "regeln": konf["version"], "felder": felder}, b["kennung"], f["jobcenter_id"])
    con.execute("UPDATE fall SET status = 'in_pruefung' WHERE id = ? AND status = 'eingang'", (fall_id,))
    return {"dokumente": len(dauer), "sekunden": round(sum(dauer), 2)}


def entscheiden(con, b, vorschlag_id: int, entscheidung: str, endwert: str | None = None) -> None:
    v = con.execute("SELECT * FROM vorschlag WHERE id = ?", (vorschlag_id,)).fetchone()
    if v is None:
        raise KeyError(vorschlag_id)
    f = _fall(con, b, v["fall_id"], "entscheiden")
    if f["status"] == "prueffertig":
        raise ValueError("Fall ist bereits prüffertig.")
    if entscheidung == "uebernommen":
        if not v["belegt"]:
            raise ValueError("Unbelegte Angaben können nicht übernommen werden; bitte korrigieren oder verwerfen.")
        endwert = v["wert"]
    elif entscheidung == "korrigiert":
        if not endwert or not endwert.strip():
            raise ValueError("Für eine Korrektur ist ein Wert nötig.")
        endwert = endwert.strip()
    elif entscheidung == "verworfen":
        endwert = None
    else:
        raise ValueError(entscheidung)
    con.execute("UPDATE vorschlag SET entscheidung = ?, endwert = ?, entschieden_von = ?, entschieden_am = ? WHERE id = ?",
                (entscheidung, endwert, b["kennung"], jetzt(), vorschlag_id))
    audit.eintragen(con, "entscheidung", {"vorschlag": vorschlag_id, "fall": v["fall_id"], "feld": v["feld"],
                                          "vorschlag_wert": v["wert"], "entscheidung": entscheidung, "endwert": endwert},
                    b["kennung"], f["jobcenter_id"])


def ansicht(con, konf: dict, b, fall_id: str) -> dict:
    f = _fall(con, b, fall_id)
    docs = con.execute("SELECT * FROM dokument WHERE fall_id = ? ORDER BY id", (fall_id,)).fetchall()
    vs = con.execute("SELECT * FROM vorschlag WHERE fall_id = ? ORDER BY dokument_id, belegt, id", (fall_id,)).fetchall()
    arten = {d["dokumentart"] for d in docs if d["dokumentart"]}
    analysiert = all(d["dokumentart"] for d in docs)
    werte = {}
    for v in vs:
        art = next(d["dokumentart"] for d in docs if d["id"] == v["dokument_id"])
        if v["entscheidung"] in ("uebernommen", "korrigiert"):
            werte[(art, v["feld"])] = v["endwert"]
    # echte Dauer der KI-Auswertung, wie sie im Protokoll steht (je Dokument ein Eintrag „ki_vorschlag“)
    sek = [json.loads(z["daten"]).get("sekunden") for z in con.execute(
        "SELECT daten FROM protokoll WHERE aktion = 'ki_vorschlag' AND jobcenter_id = ? AND daten LIKE ?",
        (f["jobcenter_id"], f'%"fall": "{fall_id}"%'))]
    return {"fall": f, "merkmale": json.loads(f["merkmale"]), "dokumente": docs, "vorschlaege": vs,
            "gelesen_s": sum(sek) if sek and None not in sek else None,
            "fehlend": regeln.fehlende_unterlagen(konf, f["antragsart"], json.loads(f["merkmale"]), arten) if analysiert else None,
            "hinweise": regeln.plausibilitaet(konf, werte), "offen": sum(1 for v in vs if v["entscheidung"] is None),
            "analysiert": analysiert}


def prueffertig(con, konf: dict, b, fall_id: str) -> dict:
    a = ansicht(con, konf, b, fall_id)
    _pruefe(b, "entscheiden", a["fall"]["jobcenter_id"])
    if not a["analysiert"] or not a["vorschlaege"]:
        raise ValueError("Fall ist noch nicht ausgewertet.")
    if a["offen"]:
        raise ValueError(f"{a['offen']} Angaben sind noch nicht entschieden.")
    con.execute("UPDATE fall SET status = 'prueffertig' WHERE id = ?", (fall_id,))
    audit.eintragen(con, "prueffertig", {"fall": fall_id, "fehlend": a["fehlend"], "hinweise": a["hinweise"]},
                    b["kennung"], a["fall"]["jobcenter_id"])
    return {"fehlend": a["fehlend"], "hinweise": a["hinweise"]}


def export(con, konf: dict, b, fall_id: str) -> dict:
    a = ansicht(con, konf, b, fall_id)
    if a["fall"]["status"] != "prueffertig":
        raise ValueError("Export erst nach „prüffertig“.")
    audit.eintragen(con, "export", {"fall": fall_id}, b["kennung"], a["fall"]["jobcenter_id"])
    return {"fall": fall_id, "antragsart": a["fall"]["antragsart"], "status": "prueffertig",
            "hinweis": "Synthetische Testdaten. Bestätigte Angaben, keine Entscheidung über den Leistungsanspruch.",
            "angaben": [{"dokument": v["dokument_id"], "feld": v["feld"], "wert": v["endwert"],
                         "entscheidung": v["entscheidung"], "von": v["entschieden_von"], "am": v["entschieden_am"]}
                        for v in a["vorschlaege"] if v["entscheidung"] != "verworfen"],
            "fehlende_unterlagen": a["fehlend"], "hinweise": a["hinweise"]}
