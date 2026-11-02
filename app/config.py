"""Einstellungen aus Umgebungsvariablen. Keine Geheimnisse im Code."""
import os
from dataclasses import dataclass
from pathlib import Path

BASIS = Path(__file__).resolve().parent.parent


@dataclass(frozen=True)
class Einstellungen:
    datenbank: Path
    ollama_url: str
    sprachmodell: str
    einbettungsmodell: str
    sitzungsschluessel: str
    demo_passwort: str
    normen: Path
    unterlagen_konfiguration: Path
    prompt_version: str = "extraktion-v3"


def laden() -> Einstellungen:
    daten = Path(os.environ.get("DATENVERZEICHNIS", BASIS / "daten"))
    daten.mkdir(parents=True, exist_ok=True)
    schluessel = os.environ.get("SITZUNGSSCHLUESSEL")
    if not schluessel:
        datei = daten / ".sitzungsschluessel"
        if not datei.exists():
            datei.write_text(os.urandom(32).hex())
            datei.chmod(0o600)
        schluessel = datei.read_text().strip()
    return Einstellungen(
        datenbank=daten / "antragsassistent.sqlite3",
        ollama_url=os.environ.get("OLLAMA_URL", "http://localhost:11434"),
        sprachmodell=os.environ.get("SPRACHMODELL", "qwen2.5:7b-instruct"),
        einbettungsmodell=os.environ.get("EINBETTUNGSMODELL", "bge-m3"),
        sitzungsschluessel=schluessel,
        demo_passwort=os.environ.get("DEMO_PASSWORT", ""),
        normen=Path(os.environ.get("NORMEN", BASIS / "normen" / "normen.jsonl")),
        unterlagen_konfiguration=BASIS / "konfiguration" / "unterlagen.yaml",
    )
