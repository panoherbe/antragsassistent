"""Messlauf: Suche, Extraktion, Vollständigkeitsprüfung und Assistent gegen synthetische Wahrheit und Goldsatz.

    python -m eval.messen --faelle 40 --ausgabe nachweis/<datum>

Schreibt messung.json (alle Einzelwerte) und eine Zusammenfassung auf stdout. Der Goldsatz eval/gold_suche.jsonl
ist selbst geschrieben (Alltagsfragen → erwarteter Paragraf), also kein unabhängiger Maßstab.
"""
import argparse
import json
import platform
import statistics
import subprocess
import time
from pathlib import Path

import httpx

from app import assistent, config, extraktion, regeln, suche, synth
from app.llm import Sprachmodell


def quantil(werte, q):
    w = sorted(werte)
    return round(w[min(len(w) - 1, int(q * len(w)))], 2) if w else None


def suche_messen(normen, modell, gold):
    out = {}
    for verfahren in ("bm25", "dicht", "hybrid"):
        treffer, rr, dauer, zeilen = {1: 0, 3: 0, 5: 0}, [], [], []
        for g in gold:
            t = time.perf_counter()
            liste = [x["paragraf"] for x in normen.suchen(g["frage"], verfahren, modell, k=5)]
            dauer.append(time.perf_counter() - t)
            platz = next((i + 1 for i, p in enumerate(liste) if p in g["paragrafen"]), None)
            for k in treffer:
                treffer[k] += bool(platz and platz <= k)
            rr.append(1 / platz if platz else 0)
            zeilen.append({"frage": g["frage"], "erwartet": g["paragrafen"], "gefunden": liste, "platz": platz})
        n = len(gold)
        out[verfahren] = {"n": n, **{f"treffer@{k}": round(v / n, 3) for k, v in treffer.items()},
                          "mrr": round(sum(rr) / n, 3), "ms_median": round(statistics.median(dauer) * 1000, 1),
                          "einzeln": zeilen}
    return out


def extraktion_messen(modell, konf, faelle):
    felder, arten, dauer, voll = [], [], [], []
    for f in faelle:
        vorhergesagt = set()
        for d in f.dokumente:
            art, aus, sek = extraktion.auslesen(modell, konf, d.text)
            dauer.append(sek)
            arten.append({"dokument": d.kennung, "wahr": d.art, "vorhergesagt": art})
            vorhergesagt.add(art)
            for x in aus:
                w = d.wahr.get(x["feld"])
                felder.append({"dokument": d.kennung, "feld": x["feld"], "wahr": w, "wert": x["wert"],
                               "richtig": w is not None and extraktion.gleich(x["feld"], x["wert"], w),
                               "belegt": x["belegt"], "fundstelle": x["fundstelle"]})
        voll.append({"fall": f.kennung, "wahr": f.fehlend,
                     "gefunden": regeln.fehlende_unterlagen(konf, f.antragsart, f.merkmale, vorhergesagt)})
    n = len(felder)
    richtig = sum(x["richtig"] for x in felder)
    belegt = [x for x in felder if x["belegt"]]
    return {
        "faelle": len(faelle), "dokumente": len(arten), "felder": n,
        "dokumentart_richtig": round(sum(a["wahr"] == a["vorhergesagt"] for a in arten) / len(arten), 3),
        "feld_richtig": round(richtig / n, 3),
        "belegt_anteil": round(len(belegt) / n, 3),
        "belegt_und_richtig": round(sum(x["richtig"] for x in belegt) / max(1, len(belegt)), 3),
        "belegt_aber_falsch": sum(not x["richtig"] for x in belegt),
        "unbelegt_aber_richtig": sum(x["richtig"] and not x["belegt"] for x in felder),
        "vollstaendigkeit_richtig": round(sum(v["wahr"] == v["gefunden"] for v in voll) / len(voll), 3),
        "faelle_mit_fehlendem_nachweis": sum(bool(v["wahr"]) for v in voll),
        "sekunden_je_dokument": {"median": quantil(dauer, .5), "p95": quantil(dauer, .95), "max": round(max(dauer), 2)},
        "je_feld": {feld: round(sum(x["richtig"] for x in felder if x["feld"] == feld) /
                                max(1, sum(1 for x in felder if x["feld"] == feld)), 3)
                    for feld in sorted({x["feld"] for x in felder})},
        "fehler": [x for x in felder if not x["richtig"]][:40], "arten": arten, "vollstaendigkeit": voll,
    }


def assistent_messen(normen, modell, gold, n):
    zeilen = [assistent.beantworten(g["frage"], normen, modell) | {"erwartet": g["paragrafen"]} for g in gold[:n]]
    for z in zeilen:
        z["erwartet_zitiert"] = bool(set(z["erwartet"]) & set(z["zitate"]))
        z["quellen"] = [q["paragraf"] for q in z["quellen"]]
    s = [z["sekunden"] for z in zeilen]
    return {"n": len(zeilen), "sekunden": {"median": quantil(s, .5), "p95": quantil(s, .95), "max": max(s)},
            "mit_zitat": sum(not z["ohne_zitat"] for z in zeilen),
            "zitate_alle_belegt": sum(not z["unbelegt"] for z in zeilen),
            "erwarteter_paragraf_zitiert": sum(z["erwartet_zitiert"] for z in zeilen), "einzeln": zeilen}


def umgebung(e):
    tags = httpx.get(f"{e.ollama_url}/api/tags", timeout=30).json()["models"]
    gpu = subprocess.run(["sh", "-c", "nvidia-smi --query-gpu=name,memory.total --format=csv,noheader 2>/dev/null"],
                         capture_output=True, text=True).stdout.strip()
    version = httpx.get(f"{e.ollama_url}/api/version", timeout=30).json().get("version")
    return {"python": platform.python_version(), "ollama": version, "gpu": gpu or "über Ollama-Container",
            "modelle": {m["name"]: {"digest": m["digest"][:12], "groesse_gb": round(m["size"] / 1e9, 2)} for m in tags}}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--faelle", type=int, default=40)
    ap.add_argument("--startwert", type=int, default=4711, help="anderer Startwert als die Demo-Fälle")
    ap.add_argument("--assistent", type=int, default=12)
    ap.add_argument("--ausgabe", type=Path, required=True)
    a = ap.parse_args()
    e = config.laden()
    modell = Sprachmodell(e.ollama_url, e.sprachmodell, e.einbettungsmodell, einbettung_cpu=e.einbettung_cpu)
    konf = regeln.laden(e.unterlagen_konfiguration)
    normen = suche.Normen(e.normen)
    gold = [json.loads(z) for z in (config.BASIS / "eval" / "gold_suche.jsonl").read_text().splitlines() if z.strip()]
    a.ausgabe.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    modell.json_antwort("Antworte mit {}.", "ok", {"type": "object"})  # Modell laden, nicht mitmessen
    t = time.perf_counter()
    normen.vektoren_laden(modell, Path(e.datenbank).parent / "normen_vektoren.json")
    erg = {"prompt": e.prompt_version, "startwert": a.startwert, "umgebung": umgebung(e),
           "einbettung_cpu": e.einbettung_cpu, "normen": {"absaetze": len(normen.absaetze),
                                               "paragrafen": len({x["paragraf"] for x in normen.absaetze}),
                                               "einbetten_sekunden": round(time.perf_counter() - t, 1)}}
    erg["suche"] = suche_messen(normen, modell, gold)
    erg["extraktion"] = extraktion_messen(modell, konf, synth.faelle(a.faelle, a.startwert))
    erg["assistent"] = assistent_messen(normen, modell, gold, a.assistent)
    erg["laufzeit_sekunden"] = round(time.time() - t0, 1)
    (a.ausgabe / "messung.json").write_text(json.dumps(erg, ensure_ascii=False, indent=1))
    kurz = {k: {kk: vv for kk, vv in v.items() if kk not in ("einzeln",)} for k, v in erg["suche"].items()}
    print(json.dumps({"suche": kurz, "extraktion": {k: v for k, v in erg["extraktion"].items()
                                                    if k not in ("fehler", "arten", "vollstaendigkeit")},
                      "assistent": {k: v for k, v in erg["assistent"].items() if k != "einzeln"},
                      "prompt": erg["prompt"], "startwert": erg["startwert"], "normen": erg["normen"], "umgebung": erg["umgebung"], "laufzeit": erg["laufzeit_sekunden"]},
                     ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
