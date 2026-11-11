# Messprotokoll Antragsassistent

Gültig ist **v4 vom 11.11.2026** mit den neuesten offenen Modellen (`qwen3.8:27b`, `qwen3-embedding:4b`). Die Läufe
v1–v3 vom 02.11.2026 mit `qwen2.5:7b-instruct` und `bge-m3` stehen unverändert darunter; v4 lief auf **denselben 40
Fällen wie v3** (Startwert 9001) mit derselben Anweisung (`extraktion-v3`) und demselben Goldsatz, ist also direkt
vergleichbar. Alle Einzelwerte: `v4-2026-11-11/messung.json`, `lauf.log`; die Modellwahl: `v4-2026-11-11/vorpruefung/`.
Alle Daten sind erfunden (synthetische Testdokumente aus `app/synth.py`).

## v4, 11.11.2026: neueste Modelle (gültig)

### Umgebung

| | |
|---|---|
| Rechner | Linux-Server (Ubuntu 24.04), NVIDIA GeForce RTX 3060 mit 12 GB, 62 GB Arbeitsspeicher, Intel Core i7-11700B (8 Kerne), Docker |
| Modelle | Ollama 0.40.16; `qwen3.8:27b` (Digest aaee06c39dcf, 17,7 GB, Q4, Apache 2.0) und `qwen3-embedding:4b` (Digest df5bd2e3c74c, 2,5 GB, Apache 2.0); Temperatur 0, Denkmodus aus (`think: false`) |
| Verteilung | `ollama ps` während des Laufs: `qwen3.8:27b` 45 % CPU / 55 % GPU (36 von 66 Schichten auf der GPU), Kontext 8192; `qwen3-embedding:4b` 100 % CPU (`EINBETTUNG_CPU=1`) |
| Neueste Generation | am 11.11.2026 auf ollama.com nachgesehen: Qwen3.8 ist die neueste Qwen-Generation (kein Qwen3.9 oder Qwen4), Ollama 0.40.16 die neueste stabile Version (09.11.2026) |
| Anwendung | Python 3.12.13, Image aus diesem Repository |
| Normen | wie v3: 519 Absätze aus 150 Paragrafen (abgerufen 02.11.2026); Einbetten aller Absätze auf dem Prozessor 705,7 s, einmalig (danach aus dem Zwischenspeicher) |
| Tests | `docker compose run --rm test`: **24 Tests grün** (`tests-2026-11-11.txt`) |
| Last | Der Lauf hielt die Sperre der GPU des Rechners; keine anderen Modellläufe gleichzeitig. Gesamtdauer 3.198,6 s |

### Ergebnis im Vergleich zu v3 (gleiche 40 Fälle, 133 Dokumente, 418 Angaben)

| | v3 (02.11.2026): qwen2.5:7b, bge-m3 | **v4 (11.11.2026): qwen3.8:27b, qwen3-embedding:4b** |
|---|---|---|
| Dokumentart richtig | 100 % (133 von 133) | **100 % (133 von 133)** |
| Angaben richtig | 95,9 % | **100 % (418 von 418)** |
| Angaben belegt | 96,4 % | **100 %** |
| davon richtig | 99,3 % | **100 %** |
| belegt, aber falsch | 3 | **0** |
| fehlende Nachweise richtig erkannt (Fälle) | 100 % (7 mit Lücke) | **100 % (7 mit Lücke)** |
| Sekunden je Dokument, Median / 95 % / Maximum | 4,17 / 6,34 / 12,24 | **13,75 / 19,06 / 23,90** |
| Suche: richtiger Paragraf an erster Stelle (Treffer@1) | 77,8 % | **88,9 %** |
| Suche: unter den ersten drei / fünf (Treffer@3 / @5) | 91,1 % / 93,3 % | **95,6 % / 95,6 %** |
| Suche: MRR, Dauer je Frage (Median) | 0,846, rund 110 ms (GPU) | **0,922, 538 ms (Prozessor)** |
| Assistent: alle genannten Fundstellen unter den Treffern | 15 von 15 | **15 von 15** |
| Assistent: erwarteter Paragraf zitiert | 13 von 15 | **13 von 15** |
| Assistent: Sekunden je Antwort, Median / Maximum | 2,04 / 4,34 | **22,67 / 38,54** |

**Was besser ist:** Alle 418 Angaben sind richtig und belegt; die 14 Beträge der Entgeltabrechnung, die v3 als
„netto“ statt als Betrag zurückgab, und die drei Arbeitgeber mit „Personalabteilung“ sind behoben, ohne dass die
Anweisung geändert wurde. Die Suche findet den richtigen Paragrafen deutlich öfter an erster Stelle.

**Was schlechter ist:** das Tempo. Das Modell ist rund viermal so groß wie qwen2.5:7b und passt auf der GPU mit 12 GB
nur zur Hälfte in den Grafikspeicher; der Rest rechnet im Arbeitsspeicher. Je Dokument dauert das Auslesen gut
dreimal so lange, eine Antwort auf eine Frage rund elfmal so lange. Auf einer GPU, auf der das ganze Modell Platz hat,
wäre es schneller; das ist **nicht gemessen**.

**Was noch falsch ist oder nicht gemessen:**

- Assistent: In 2 von 15 Antworten fehlt der erwartete Paragraf (Altersgrenze: § 7 statt § 7a; Zuschuss bei
  Arbeitsaufnahme: §§ 16e, 16i statt § 16b). Alle genannten Fundstellen stehen unter den Treffern; ob die Antworten
  inhaltlich stimmen, misst der Lauf nicht (siehe Grenzen).
- 100 % gelten für diese erfundenen Textdokumente aus Vorlagen. Echte Nachweise (Scans, Tabellen, Handschrift) sind
  schwerer; dafür fehlt im Prototyp eine Texterkennung.

### Modellwahl (Vorprüfung 11.11.2026, `v4-2026-11-11/vorpruefung/`)

**Einbettungsmodell:** alle drei Größen von qwen3-embedding auf den 45 Goldfragen, mit und ohne Aufgabenbeschreibung
vor der Frage („Instruct: … Query: …“, Empfehlung der Modellkarte), Einbettungen hier auf der GPU:

| Modell | Treffer@1 | Treffer@3 | Treffer@5 | MRR | Dauer je Frage |
|---|---|---|---|---|---|
| qwen3-embedding:0.6b mit / ohne Aufgabenbeschreibung | 71,1 % / 66,7 % | 91,1 % / 91,1 % | 93,3 % / 93,3 % | 0,801 / 0,787 | 37 / 33 ms |
| **qwen3-embedding:4b** mit / ohne | **91,1 %** / 86,7 % | **95,6 %** / 93,3 % | 95,6 % / 95,6 % | **0,933** / 0,902 | 86 / 77 ms |
| qwen3-embedding:8b mit / ohne | 91,1 % / 86,7 % | 95,6 % / 95,6 % | 97,8 % / 97,8 % | 0,939 / 0,917 | 137 / 121 ms |

Gewählt: 4b mit Aufgabenbeschreibung (so gut wie 8b an den ersten drei Stellen, halb so groß). Im Messlauf v4 liefen
die Einbettungen auf dem Prozessor; dort kam Treffer@1 auf 88,9 % statt 91,1 % (eine Frage rutschte auf Platz 2:
Rechengenauigkeit auf Prozessor und GPU unterscheidet sich geringfügig). Gültig sind die Werte von v4.

**Sprachmodell:** `qwen3.8:27b` gegen die Variante mit Mehr-Token-Vorhersage `qwen3.8:27b-mtp-q4_K_M`, je 13 Dokumente
(4 Fälle, Startwert 777): beide 13 von 13 Dokumentarten und 40 von 40 Angaben richtig; Median 13,63 s gegen 16,12 s
je Dokument. Die MTP-Variante war beim Auslesen **langsamer** (nur rund die Hälfte der vorhergesagten Token wurde
angenommen) und ist deshalb nicht gewählt.

**Speicher:** Mit beiden Modellen auf der GPU verdrängte das Einbettungsmodell (3,4 GB) das Sprachmodell; die nächste
Antwort dauerte danach 15,7 s statt weniger Sekunden, weil das Sprachmodell neu geladen wurde. Seitdem rechnet der
Prozessor die Einbettungen (`EINBETTUNG_CPU=1`); beide Modelle bleiben geladen. Preis: 538 ms statt rund 90 ms je
Suchanfrage und einmalig 705,7 s für das Einbetten der Normen.

### Grenzen (gelten für v4 wie für v1–v3)

- Synthetische Textdokumente aus Vorlagen mit Varianten; echte Nachweise (Scans, Tabellen in PDF, Handschrift) sind schwerer. Keine Texterkennung im Prototyp.
- Der Goldsatz der Suche ist selbst geschrieben, kein unabhängiger Maßstab; die Paragrafenzuordnung folgt den Überschriften der Normen.
- 40 Fälle je Lauf; Unterschiede von 1–2 Prozentpunkten zwischen Läufen sind nicht belastbar.
- Gemessen auf einer Consumer-GPU mit 12 GB, auf der `qwen3.8:27b` nur zur Hälfte Platz hat; in einem Auftrag laufen Modell und Anwendung in einem EU-Rechenzentrum, mit eigener Messung.
- Die synthetischen Anschriften (`app/synth.py`) sind kein gemessenes Feld.
- Ob die Antworten zum SGB II inhaltlich stimmen, misst der Lauf nicht; gemessen ist, ob der erwartete Paragraf unter den ersten drei Treffern steht und ob die genannten Fundstellen unter den Treffern stehen. Jede Antwort bleibt ein Entwurf. Tabellen in Normen sind beim Laden zusammengezogen.
- Die Hash-Kette ist ohne Schlüssel und ohne äußeren Anker: Sie zeigt Änderungen an einzelnen Einträgen; wer Schreibzugriff auf die Datenbank hat, kann die Kette neu berechnen.

## v1–v3, 02.11.2026: qwen2.5:7b-instruct und bge-m3 (ersetzt durch v4)
Drei Messläufe mit `python -m eval.messen`, je 40 synthetische Fälle und 15 Fragen an den Assistenten, dazu die
Tests. Alle Einzelwerte stehen in `v1-2026-11-02/`, `v2-2026-11-02/` und `v3-2026-11-02/` (`messung.json`, `lauf.log`).
Gültig ist der Stand **v3**; v1 und v2 bleiben stehen, weil v2 schlechter war und das zum Ergebnis gehört.

### Umgebung

| | |
|---|---|
| Rechner | Linux-Server (Ubuntu 24.04), NVIDIA GeForce RTX 3060 mit 12 GB (Treiber 580.173.02), Docker Compose |
| Modelle | Ollama 0.20.6 im eigenen Container; `qwen2.5:7b-instruct` (Digest 845dbda0ea48, 4,68 GB), `bge-m3` (Digest 790764642607, 1,16 GB); beide zu 100 % auf der GPU (`ollama ps`); Temperatur 0 |
| Anwendung | Python 3.12.13, Image aus diesem Repository |
| Normen | SGB II und SGB I §§ 60–67 von gesetze-im-internet.de, abgerufen 02.11.2026: 519 Absätze aus 150 Paragrafen (Prüfsummen in `normen/quelle.json`); Einbetten aller Absätze 30,6 s beim ersten Mal |
| Tests | `docker compose run --rm test`: **23 Tests grün** in 6,0 s (vor jedem Lauf) |

### Was gemessen wird

- **Suche:** 45 selbst geschriebene Alltagsfragen mit erwartetem Paragrafen (`eval/gold_suche.jsonl`). Treffer@k = Anteil der Fragen, bei denen ein erwarteter Paragraf unter den ersten k Paragrafen ist; MRR = mittlerer Kehrwert des Rangs.
- **Extraktion:** Synthetische Fälle mit bekannter Wahrheit (Generator `app/synth.py`, je Lauf ein anderer Startwert). Je Dokument: Dokumentart und Felder. „Richtig“ = fachlich gleicher Wert (Beträge auf den Cent, Namen ohne Reihenfolge). „Belegt“ = die zitierte Zeile steht wörtlich im Dokument und enthält den Wert. Gefährlich ist nur „belegt aber falsch“, denn nur belegte Angaben lassen sich übernehmen.
- **Vollständigkeit:** fehlende Nachweise nach der Unterlagenliste, berechnet aus den vom Modell bestimmten Dokumentarten, gegen die Wahrheit.
- **Assistent:** Antwort aus den gefundenen Normen; geprüft wird, ob jede genannte Fundstelle unter den Treffern ist und ob der erwartete Paragraf zitiert wird.

### Ergebnisse

#### Suche (gleich in allen drei Läufen, 45 Fragen)

| Verfahren | Treffer@1 | Treffer@3 | Treffer@5 | MRR | Dauer je Frage (Median) |
|---|---|---|---|---|---|
| BM25 | 51,1 % | 71,1 % | 75,6 % | 0,606 | 0,4 ms |
| Einbettungen (bge-m3) | **77,8 %** | **91,1 %** | **93,3 %** | **0,846** | rund 110 ms |
| Kombination (RRF) | 66,7 % | 82,2 % | 82,2 % | 0,741 | rund 110 ms |

Die Kombination war schlechter als bge-m3 allein; der Assistent nutzt seit v2 deshalb nur bge-m3.

#### Extraktion und Vollständigkeit

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

#### Assistent (15 Fragen aus dem Goldsatz)

| | v1 (Kombination) | v2 und v3 (bge-m3) |
|---|---|---|
| Antworten mit Fundstelle | 13 | **15** |
| alle genannten Fundstellen unter den Treffern | 15 | **15** |
| erwarteter Paragraf zitiert | 10 | **13** |
| Sekunden je Antwort, Median / Maximum | 2,05 / 5,92 | **2,04 / 4,34** |

