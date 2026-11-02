"""Feste Regeln ohne KI: Vollständigkeit der Unterlagen und Plausibilität, gelesen aus konfiguration/unterlagen.yaml.

Ausdrücke haben genau die Form `<art>.<feld> <op> <art>.<feld>|<zahl>` mit op in <=, >=, <, >, ==. Es wird nichts
ausgewertet, was nicht in diese Form passt (kein eval).
"""
import re
from pathlib import Path

import yaml

AUSDRUCK = re.compile(r"^\s*(\w+)\.(\w+)\s*(<=|>=|==|<|>)\s*(?:(\w+)\.(\w+)|(-?\d+(?:\.\d+)?))\s*$")


def laden(pfad: Path) -> dict:
    konf = yaml.safe_load(pfad.read_text(encoding="utf-8"))
    for r in konf["regeln"]:
        if not AUSDRUCK.match(r["pruefe"]):
            raise ValueError(f"Regel {r['id']}: Ausdruck nicht erlaubt: {r['pruefe']}")
    return konf


def fehlende_unterlagen(konf: dict, antragsart: str, merkmale: dict, vorhandene_arten: set[str]) -> list[str]:
    fehlend = []
    for p in konf["pflicht"][antragsart]:
        noetig = merkmale.get(p["wenn"]) if "wenn" in p else True
        if noetig and p["art"] not in vorhandene_arten:
            fehlend.append(p["art"])
    return fehlend


def _zahl(s: str):
    try:
        return float(s)
    except (TypeError, ValueError):
        return None


def plausibilitaet(konf: dict, werte: dict[tuple[str, str], str]) -> list[dict]:
    """werte: {(dokumentart, feld): bestätigter Wert}. Regeln mit fehlenden Werten werden übersprungen."""
    hinweise = []
    for r in konf["regeln"]:
        a, f, op, a2, f2, lit = AUSDRUCK.match(r["pruefe"]).groups()
        links = werte.get((a, f))
        rechts = lit if lit is not None else werte.get((a2, f2))
        if links is None or rechts is None:
            continue
        if op == "==":
            ok = " ".join(str(links).split()).casefold() == " ".join(str(rechts).split()).casefold()
        else:
            x, y = _zahl(links), _zahl(rechts)
            if x is None or y is None:
                ok = False
            else:
                ok = {"<=": x <= y, ">=": x >= y, "<": x < y, ">": x > y}[op]
        if not ok:
            hinweise.append({"regel": r["id"], "text": r["text"]})
    return hinweise
