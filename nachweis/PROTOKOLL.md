# Messprotokoll Antragsassistent, 02.11.2026

Drei Messläufe mit `python -m eval.messen`, je 40 synthetische Fälle und 15 Fragen an den Assistenten, dazu die
Tests. Alle Einzelwerte stehen in `v1-2026-11-02/`, `v2-2026-11-02/` und `v3-2026-11-02/` (`messung.json`, `lauf.log`).
Gültig ist der Stand **v3**; v1 und v2 bleiben stehen, weil v2 schlechter war und das zum Ergebnis gehört.

## Umgebung

| | |
|---|---|
| Rechner | Linux-Server (Ubuntu 24.04), NVIDIA GeForce RTX 3060 mit 12 GB (Treiber 580.173.02), Docker Compose |
| Modelle | Ollama 0.20.6 im eigenen Container; `qwen2.5:7b-instruct` (Digest 845dbda0ea48, 4,68 GB), `bge-m3` (Digest 790764642607, 1,16 GB); beide zu 100 % auf der GPU (`ollama ps`); Temperatur 0 |
| Anwendung | Python 3.12.13, Image aus diesem Repository |
| Normen | SGB II und SGB I §§ 60–67 von gesetze-im-internet.de, abgerufen 02.11.2026: 519 Absätze aus 150 Paragrafen (Prüfsummen in `normen/quelle.json`); Einbetten aller Absätze 30,6 s beim ersten Mal |
| Tests | `docker compose run --rm test`: **23 Tests grün** in 6,0 s (vor jedem Lauf) |

## Was gemessen wird

- **Suche:** 45 selbst geschriebene Alltagsfragen mit erwartetem Paragrafen (`eval/gold_suche.jsonl`). Treffer@k = Anteil der Fragen, bei denen ein erwarteter Paragraf unter den ersten k Paragrafen ist; MRR = mittlerer Kehrwert des Rangs.
- **Extraktion:** Synthetische Fälle mit bekannter Wahrheit (Generator `app/synth.py`, je Lauf ein anderer Startwert). Je Dokument: Dokumentart und Felder. „Richtig“ = fachlich gleicher Wert (Beträge auf den Cent, Namen ohne Reihenfolge). „Belegt“ = die zitierte Zeile steht wörtlich im Dokument und enthält den Wert. Gefährlich ist nur „belegt aber falsch“, denn nur belegte Angaben lassen sich übernehmen.
- **Vollständigkeit:** fehlende Nachweise nach der Unterlagenliste, berechnet aus den vom Modell bestimmten Dokumentarten, gegen die Wahrheit.
- **Assistent:** Antwort aus den gefundenen Normen; geprüft wird, ob jede genannte Fundstelle unter den Treffern ist und ob der erwartete Paragraf zitiert wird.

## Ergebnisse

### Suche (gleich in allen drei Läufen, 45 Fragen)

| Verfahren | Treffer@1 | Treffer@3 | Treffer@5 | MRR | Dauer je Frage (Median) |
|---|---|---|---|---|---|
| BM25 | 51,1 % | 71,1 % | 75,6 % | 0,606 | 0,4 ms |
| Einbettungen (bge-m3) | **77,8 %** | **91,1 %** | **93,3 %** | **0,846** | rund 110 ms |
| Kombination (RRF) | 66,7 % | 82,2 % | 82,2 % | 0,741 | rund 110 ms |

Die Kombination war schlechter als bge-m3 allein; der Assistent nutzt seit v2 deshalb nur bge-m3.

### Extraktion und Vollständigkeit

| | v1 | v2 | **v3 (gültig)** |
|---|---|---|---|
| Prompt | extraktion-v1 | v2: Feldbeschreibungen als Liste | v3: Felder und Beschreibungen je Dokumentart |
| Startwert, Fälle, Dokumente, Felder | 4711 · 40 · 127 · 394 | 2027 · 40 · 125 · 383 | 9001 · 40 · 133 · 418 |
| Dokumentart richtig | 100 % | 91,2 % | **100 %** |
| Angaben richtig | 95,2 % | 87,7 % | **95,9 %** |
| Angaben belegt | 96,2 % | 90,6 % | **96,4 %** |
| davon richtig | 98,9 % | 96,8 % | **99,3 %** |
| belegt, aber falsch | 4 | 11 | **3** |
| fehlende Nachweise richtig erkannt (Fälle) | 100 % (11 mit Lücke) | 72,5 % | **100 % (7 mit Lücke)** |
| Sekunden je Dokument, Median / 95 % / Maximum | 4,19 / 8,63 / 12,19 | 5,55 / 9,93 / 10,67 | **4,17 / 6,34 / 12,24** |

**v2 war ein Rückschritt.** Die Feldbeschreibung „name = Vor- und Nachname der antragstellenden Person“ stand für
alle Dokumente; das Modell ordnete daraufhin 11 von 36 Entgeltabrechnungen als Antrag ein („Mitarbeiter/in: …“). Die
11 „belegt aber falsch“ in v2 sind die Namen dieser falsch eingeordneten Abrechnungen. v3 gruppiert Felder und
Beschreibungen je Dokumentart und wurde auf einem neuen Startwert gemessen, den es vorher nicht gesehen hatte.

**Was in v3 noch falsch ist:**

- Bruttobetrag und Nettobetrag der Entgeltabrechnung: 68,2 % richtig. In 7 von 22 Abrechnungen gab das Modell die Beschriftung „netto“ statt des Betrags zurück. Alle 14 Angaben sind „nicht belegt“ und müssen von Hand eingetragen werden; übernommen werden kann keine.
- Arbeitgeber: 3 von 22 als „Beispiel Logistik GmbH, Personalabteilung“; belegt, aber nach der strengen Messung falsch. Das sind die einzigen 3 „belegt aber falsch“.
- Alle übrigen Felder (Name, Geburtsdatum, Personen, Monat, Mieten, Heizkosten, Wohnfläche, Kontoinhaber, Endsaldo) 100 %.

### Assistent (15 Fragen aus dem Goldsatz)

| | v1 (Kombination) | v2 und v3 (bge-m3) |
|---|---|---|
| Antworten mit Fundstelle | 13 | **15** |
| alle genannten Fundstellen unter den Treffern | 15 | **15** |
| erwarteter Paragraf zitiert | 10 | **13** |
| Sekunden je Antwort, Median / Maximum | 2,05 / 5,92 | **2,04 / 4,34** |

## Grenzen

- Synthetische Textdokumente aus Vorlagen mit Varianten; echte Nachweise (Scans, Tabellen in PDF, Handschrift) sind schwerer. Keine Texterkennung im Prototyp.
- Der Goldsatz der Suche ist selbst geschrieben, kein unabhängiger Maßstab; die Paragrafenzuordnung folgt den Überschriften der Normen.
- 40 Fälle je Lauf; Unterschiede von 1–2 Prozentpunkten zwischen Läufen sind nicht belastbar.
- Gemessen auf einer Consumer-GPU; in einem Auftrag laufen Modell und Anwendung in einem EU-Rechenzentrum.
- Die synthetischen Anschriften (`app/synth.py`) sind kein gemessenes Feld.
