# Antragsassistent (Prototyp)

KI-assistierte Antragsbearbeitung im SGB II, gebaut als lauffähiger Prototyp: Dokumente eines Antrags auswerten,
Angaben **mit Fundstelle** vorschlagen, fehlende Nachweise finden, Fragen zum SGB II mit Paragrafenangabe
beantworten. **Das System entscheidet nichts.** Jede Angabe übernimmt, korrigiert oder verwirft eine angemeldete
Person; erst dann wird ein Fall „prüffertig“. Alles wird in einem manipulationssicheren Prüfprotokoll festgehalten.

**Nur synthetische Daten.** Der Prototyp verarbeitet keine echten Personen- oder Sozialdaten und nimmt nur
Dokumente an, die als synthetisches Testdokument gekennzeichnet sind. Lizenz: Apache 2.0.

## Gemessen am 02.11.2026

40 synthetische Fälle (133 Dokumente, 418 Angaben), offenes Modell auf einer GPU mit 12 GB:

| | |
|---|---|
| Dokumentart richtig bestimmt | 100 % |
| Angaben richtig | 95,9 % |
| belegte Angaben (Fundstelle geprüft), davon richtig | 96,4 %, davon 99,3 % |
| fehlende Nachweise richtig erkannt | 100 % der Fälle |
| Dauer je Dokument (Median / 95 %) | 4,2 s / 6,3 s |
| Suche: erwarteter Paragraf unter den ersten 3 (45 Fragen) | 91,1 % |
| Assistent: alle genannten Fundstellen unter den Treffern | 15 von 15 Antworten |
| Tests | 23 grün |

Messweg, alle drei Messläufe (auch der schlechtere) und die verbleibenden Fehler: [`nachweis/PROTOKOLL.md`](nachweis/PROTOKOLL.md).

## Was er kann

| Baustein | Umsetzung |
|---|---|
| Eingang | Dokumente nur mit Kennung `SYN-…` (sonst abgewiesen und protokolliert), SHA-256 je Dokument |
| Dokumentart und Angaben | offenes Sprachmodell (lokal über Ollama) liest Dokumentart und Felder in ein festes JSON-Schema (strukturierte Ausgabe) |
| Fundstellenprüfung | eine Angabe gilt nur als **belegt**, wenn die zitierte Zeile wörtlich im Dokument steht und den Wert enthält; unbelegte Angaben können nicht übernommen, nur von Hand eingetragen werden |
| Unterlagenliste und Plausibilität | feste Regeln ohne KI in `konfiguration/unterlagen.yaml` (Beispielkonfiguration), lesbar und änderbar ohne Programmierung; Ausdrücke werden nicht frei ausgewertet |
| Menschliche Letztentscheidung | Entscheidung je Angabe, keine Sammelübernahme; Status „prüffertig“ erst, wenn nichts mehr offen ist; Export nur danach |
| Fragen zum SGB II | Suche in SGB II und SGB I §§ 60–67 (bge-m3; BM25 und die Kombination sind gemessen und schwächer), Antwort nur aus den gefundenen Normen, jede genannte Fundstelle wird gegen die Treffer geprüft |
| Rollen | Sachbearbeitung (entscheidet), Prüfung (liest Fälle und Protokoll, entscheidet nicht), Administration (prüft nur die Protokollkette, sieht keine Fallinhalte) |
| Mandanten | jede fachliche Tabelle trägt die Jobcenter-Kennung; fremde Fälle sind gesperrt |
| Prüfprotokoll | nur erweiterbar (Datenbank-Trigger), Hash-Kette über alle Einträge; jede Änderung fällt bei der Prüfung auf; Modell, Prompt-Version und Regelversion je Vorschlag |
| Schnittstelle | REST mit OpenAPI (`/docs`, `/openapi.json`), Export als JSON |

**Bewusst nicht umgesetzt:** Berechnung des Leistungsanspruchs, Bescheide, Zahlungen, Anbindung an Fachverfahren
oder DMS, Texterkennung gescannter Papierdokumente (die synthetischen Dokumente sind Text), Anmeldung über
OpenID Connect/SAML, Betrieb mit echten Daten.

## Wo was läuft

| Teil | Ort |
|---|---|
| Sprachmodell `qwen2.5:7b-instruct` (Apache 2.0) und Einbettungsmodell `bge-m3` (MIT) | eigener Ollama-Container auf demselben Rechner, GPU; kein Aufruf eines Cloud-Dienstes |
| Anwendung (FastAPI, SQLite) | Container, lauscht nur auf `127.0.0.1` |
| Gesetzestexte | einmalig von gesetze-im-internet.de geladen (`normen/laden.py`), Prüfsumme in `normen/quelle.json` |

Das Modell ist über `OLLAMA_URL`, `SPRACHMODELL` und `EINBETTUNGSMODELL` austauschbar, etwa gegen einen
Modelldienst mit Verarbeitung in der EU. Kein anderer Teil des Codes spricht mit einem Modell (`app/llm.py`).

## Start

Voraussetzung: Docker mit Compose, für flüssige Antworten eine NVIDIA-GPU mit 8 GB oder mehr (gemessen: RTX 3060,
12 GB).

```bash
echo "DEMO_PASSWORT=$(openssl rand -hex 8)" > .env      # Passwort der Demo-Kennungen
docker compose up -d
docker compose exec ollama ollama pull qwen2.5:7b-instruct
docker compose exec ollama ollama pull bge-m3
# Oberfläche: http://127.0.0.1:8420  (Kennungen sb.a, sb.b, pruef.a, admin; Passwort aus .env)
```

Beim Start legt die Anwendung 20 synthetische Fälle für zwei fiktive Jobcenter an (`DEMO_FAELLE`).

```bash
docker compose run --rm test                                          # 23 Tests, ohne Modell
docker compose run --rm app python -m normen.laden                    # Gesetzestexte neu laden
docker compose run --rm app python -m eval.messen --ausgabe nachweis/neu   # Messlauf
```

## Aufbau

```
app/synth.py        Generator synthetischer Fälle (Antrag, Entgeltabrechnung, Mietbescheinigung, Kontoauszug)
app/extraktion.py   Dokumentart, Felder, Fundstellenprüfung
app/regeln.py       Unterlagenliste und Plausibilitätsregeln aus YAML
app/suche.py        BM25, Einbettungen, Kombination (Reciprocal Rank Fusion), alle drei gemessen
app/assistent.py    Antworten mit geprüften Fundstellen
app/dienst.py       Fachlogik mit Rollen- und Mandantenprüfung
app/audit.py        Prüfprotokoll mit Hash-Kette
app/main.py         Oberfläche und REST
eval/               Goldsatz (selbst geschrieben) und Messlauf
nachweis/           Messprotokolle
```

## Grenzen

Ein Prototyp, kein Produkt. Die synthetischen Dokumente sind Textdateien mit variierenden Vorlagen; echte
Nachweise (Scans, Handschrift, Tabellen in PDFs) sind schwerer. Die Unterlagenliste ist ein Beispiel und fachlich
nicht abgestimmt. Der Goldsatz für die Suche ist selbst geschrieben. Antworten des Assistenten sind Entwürfe, keine
Rechtsauskunft. Eine Einordnung nach der EU-KI-Verordnung (Anhang III Nr. 5 Buchst. a, Art. 6 Abs. 3) ist für einen
echten Einsatz nötig; der Prototyp ist so gebaut, dass Protokollierung, menschliche Aufsicht und Nachvollziehbarkeit
von Anfang an vorhanden sind.
