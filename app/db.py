"""SQLite-Schema. Jede Tabelle mit fachlichem Inhalt trägt die Jobcenter-Kennung (Mandantentrennung)."""
import sqlite3
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS jobcenter (
    id    TEXT PRIMARY KEY,
    name  TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS benutzer (
    kennung      TEXT PRIMARY KEY,
    anzeigename  TEXT NOT NULL,
    rolle        TEXT NOT NULL CHECK (rolle IN ('sachbearbeitung', 'pruefung', 'administration')),
    jobcenter_id TEXT REFERENCES jobcenter(id),
    pw_hash      TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS fall (
    id           TEXT PRIMARY KEY,
    jobcenter_id TEXT NOT NULL REFERENCES jobcenter(id),
    antragsart   TEXT NOT NULL,
    merkmale     TEXT NOT NULL,          -- JSON: Angaben aus dem Antrag, die die Unterlagenliste steuern
    status       TEXT NOT NULL DEFAULT 'eingang'
                 CHECK (status IN ('eingang', 'in_pruefung', 'prueffertig')),
    angelegt     TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS dokument (
    id           TEXT PRIMARY KEY,
    fall_id      TEXT NOT NULL REFERENCES fall(id),
    jobcenter_id TEXT NOT NULL REFERENCES jobcenter(id),
    dateiname    TEXT NOT NULL,
    text         TEXT NOT NULL,
    sha256       TEXT NOT NULL,
    dokumentart  TEXT                     -- vom Modell vorgeschlagen, NULL bis zur Analyse
);
CREATE TABLE IF NOT EXISTS vorschlag (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    dokument_id  TEXT NOT NULL REFERENCES dokument(id),
    fall_id      TEXT NOT NULL REFERENCES fall(id),
    jobcenter_id TEXT NOT NULL REFERENCES jobcenter(id),
    feld         TEXT NOT NULL,
    wert         TEXT,
    fundstelle   TEXT,
    belegt       INTEGER NOT NULL,        -- 1 = Fundstelle steht wörtlich im Dokument und enthält den Wert
    modell       TEXT NOT NULL,
    prompt_version TEXT NOT NULL,
    entscheidung TEXT CHECK (entscheidung IN ('uebernommen', 'korrigiert', 'verworfen')),
    endwert      TEXT,
    entschieden_von TEXT REFERENCES benutzer(kennung),
    entschieden_am  TEXT,
    UNIQUE (dokument_id, feld)
);
CREATE TABLE IF NOT EXISTS protokoll (
    nr           INTEGER PRIMARY KEY,
    zeit         TEXT NOT NULL,
    benutzer     TEXT,
    jobcenter_id TEXT,
    aktion       TEXT NOT NULL,
    daten        TEXT NOT NULL,           -- JSON
    vorgaenger   TEXT NOT NULL,           -- Hash des vorigen Eintrags
    hash         TEXT NOT NULL
);
CREATE TRIGGER IF NOT EXISTS protokoll_nur_anhaengen_u BEFORE UPDATE ON protokoll
BEGIN SELECT RAISE(ABORT, 'Protokoll ist nur erweiterbar'); END;
CREATE TRIGGER IF NOT EXISTS protokoll_nur_anhaengen_d BEFORE DELETE ON protokoll
BEGIN SELECT RAISE(ABORT, 'Protokoll ist nur erweiterbar'); END;
"""


def verbinden(pfad: Path | str) -> sqlite3.Connection:
    con = sqlite3.connect(pfad, check_same_thread=False, isolation_level=None)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys = ON")
    con.execute("PRAGMA journal_mode = WAL")
    con.executescript(SCHEMA)
    return con
