"""Suche in den Normen (SGB II, SGB I §§ 60–67): BM25, Einbettungen (bge-m3) und beides kombiniert (RRF).

Treffer werden je Paragraf zusammengefasst; ausgegeben wird der beste Absatz je Paragraf.
"""
import hashlib
import json
import math
import re
from collections import Counter
from pathlib import Path

STOPP = set("""der die das den dem des ein eine einer eines einem einen und oder nicht nur auch ist sind wird werden
wurde wenn als bei für fur von vom zu zur zum im in an auf aus mit nach über unter vor durch bis so wie was wer
welche welcher welches wann ich mein meine man es sie er sich hat haben habe kann können muss müssen darf soll
gilt gelten dass daß ob noch schon etwa zum sowie""".split())


def woerter(text: str) -> list[str]:
    out = []
    for w in re.findall(r"[a-zäöüß0-9]+", text.casefold()):
        if w in STOPP or len(w) < 2:
            continue
        for endung in ("ungen", "ung", "en", "er", "es", "e", "n", "s"):
            if len(w) > len(endung) + 3 and w.endswith(endung):
                w = w[: -len(endung)]
                break
        out.append(w)
    return out


class Normen:
    def __init__(self, pfad: Path):
        self.absaetze = [json.loads(z) for z in pfad.read_text(encoding="utf-8").splitlines() if z.strip()]
        self._dok = [woerter(f"{a['titel']} {a['titel']} {a['text']}") for a in self.absaetze]
        self._tf = [Counter(d) for d in self._dok]
        n = len(self._dok)
        df = Counter(w for d in self._dok for w in set(d))
        self._idf = {w: math.log(1 + (n - c + 0.5) / (c + 0.5)) for w, c in df.items()}
        self._avg = sum(map(len, self._dok)) / n
        self._vek = None

    # --- BM25 ---------------------------------------------------------------------------------------------------
    def bm25(self, frage: str) -> list[float]:
        q, k1, b = woerter(frage), 1.5, 0.75
        return [sum(self._idf.get(w, 0) * tf[w] * (k1 + 1) / (tf[w] + k1 * (1 - b + b * len(d) / self._avg))
                    for w in q if w in tf) for d, tf in zip(self._dok, self._tf)]

    # --- Einbettungen ---------------------------------------------------------------------------------------------
    def vektoren_laden(self, modell, cache: Path) -> None:
        schluessel = hashlib.sha256((modell.einbettungsmodell + "".join(a["text"] for a in self.absaetze)).encode()).hexdigest()
        if cache.exists():
            gespeichert = json.loads(cache.read_text())
            if gespeichert.get("schluessel") == schluessel:
                self._vek = gespeichert["vektoren"]
                return
        texte = [f"{a['paragraf']} {a['titel']}: {a['text']}" for a in self.absaetze]
        self._vek = []
        for i in range(0, len(texte), 32):
            self._vek += [_einheit(v) for v in modell.einbetten(texte[i:i + 32])]
        cache.write_text(json.dumps({"schluessel": schluessel, "vektoren": self._vek}))

    def dicht(self, frage: str, modell) -> list[float]:
        q = _einheit(modell.einbetten([frage])[0])
        return [sum(a * b for a, b in zip(q, v)) for v in self._vek]

    # --- Ergebnis je Paragraf -------------------------------------------------------------------------------------
    def _rang(self, werte: list[float]) -> list[int]:
        return sorted(range(len(werte)), key=lambda i: -werte[i])

    def suchen(self, frage: str, verfahren: str = "hybrid", modell=None, k: int = 5) -> list[dict]:
        if verfahren == "bm25":
            reihen = [self._rang(self.bm25(frage))]
        elif verfahren == "dicht":
            reihen = [self._rang(self.dicht(frage, modell))]
        else:
            reihen = [self._rang(self.bm25(frage)), self._rang(self.dicht(frage, modell))]
        rrf = Counter()
        for reihe in reihen:
            for platz, i in enumerate(reihe[:200]):
                rrf[i] += 1 / (60 + platz + 1)
        out, gesehen = [], set()
        for i, wert in rrf.most_common():
            a = self.absaetze[i]
            if a["paragraf"] not in gesehen:
                gesehen.add(a["paragraf"])
                out.append({**a, "wert": round(wert, 5)})
            if len(out) == k:
                break
        return out


def _einheit(v: list[float]) -> list[float]:
    n = math.sqrt(sum(x * x for x in v)) or 1.0
    return [x / n for x in v]
