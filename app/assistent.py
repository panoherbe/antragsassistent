"""Fragen zu SGB II beantworten, nur aus gefundenen Normen und mit Fundstellen. Ein KI-Entwurf, keine Rechtsauskunft.

Jede Antwort wird geprüft: Nennt sie einen Paragrafen, der nicht unter den gefundenen Normen ist, wird sie als
„Zitat nicht belegt“ markiert.
"""
import re

SYSTEM = (
    "Du unterstützt Sachbearbeitende in einem kommunalen Jobcenter. Antworte auf Deutsch, knapp (höchstens 6 Sätze), "
    "ausschließlich auf Grundlage der mitgelieferten Normen. Belege jede Aussage mit der Fundstelle in eckigen "
    "Klammern genau in der Form [SGB II § 22] bzw. [SGB I § 60]. Reichen die Normen nicht aus, sage das. Triff keine "
    "Entscheidung im Einzelfall."
)
ZITAT = re.compile(r"\[(SGB I{1,2}) §\s*(\d+[a-z]?)[^\]]*\]")


def beantworten(frage: str, normen, modell, k: int = 5, verfahren: str = "dicht") -> dict:
    # "dicht" (bge-m3) traf im Messlauf vom 02.11.2026 besser als BM25 und die Kombination (nachweis/)
    treffer = normen.suchen(frage, verfahren, modell, k=k)
    kontext = "\n\n".join(f"[{t['paragraf']}] {t['titel']}\n{t['text']}" for t in treffer)
    antwort, dauer = modell.text_antwort(SYSTEM, f"Normen:\n{kontext}\n\nFrage: {frage}")
    gefunden = {t["paragraf"] for t in treffer}
    zitate = {f"{g} § {n}" for g, n in ZITAT.findall(antwort)}
    return {"frage": frage, "antwort": antwort, "quellen": treffer, "zitate": sorted(zitate),
            "unbelegt": sorted(zitate - gefunden), "ohne_zitat": not zitate, "sekunden": round(dauer, 2)}
