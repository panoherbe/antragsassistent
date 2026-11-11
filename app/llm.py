"""Zugriff auf das Sprachmodell über die HTTP-Schnittstelle von Ollama (lokal, offenes Modell).

Austauschbar: Jeder Dienst mit derselben Schnittstelle (etwa ein Modell bei einem Anbieter in der EU hinter einem
kompatiblen Proxy) kann über OLLAMA_URL eingesetzt werden. Es gibt keinen Aufruf außerhalb dieser Datei.

"think": False schaltet den Denkmodus ab, den qwen3.8 sonst für jede Anfrage einschaltet: Auslesen und kurze Antworten
brauchen ihn nicht, und er kostet ein Vielfaches der Zeit. Modelle ohne Denkmodus ignorieren den Schalter.
"""
import json
import time

import httpx


class Sprachmodell:
    def __init__(self, url: str, modell: str, einbettung: str, zeitlimit: float = 600, einbettung_cpu: bool = False):
        self.url, self.modell, self.einbettungsmodell = url.rstrip("/"), modell, einbettung
        # Auf einer GPU mit 12 GB füllt das Sprachmodell den Speicher; lädt dann das Einbettungsmodell auf die GPU,
        # verdrängt es das Sprachmodell, und jede Frage muss es neu laden (beobachtet 11.11.2026, nachweis/PROTOKOLL.md).
        # EINBETTUNG_CPU=1 rechnet die Einbettungen auf dem Prozessor; beide Modelle bleiben geladen.
        self.einbettung_optionen = {"num_gpu": 0} if einbettung_cpu else {}
        self.client = httpx.Client(timeout=zeitlimit)

    def json_antwort(self, system: str, nutzer: str, schema: dict) -> tuple[dict, float]:
        """Antwort im vorgegebenen JSON-Schema (strukturierte Ausgabe), dazu die Dauer in Sekunden."""
        t = time.perf_counter()
        r = self.client.post(f"{self.url}/api/chat", json={
            "model": self.modell, "stream": False, "format": schema, "think": False,
            "options": {"temperature": 0, "num_ctx": 8192},
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": nutzer}]})
        r.raise_for_status()
        return json.loads(r.json()["message"]["content"]), time.perf_counter() - t

    def text_antwort(self, system: str, nutzer: str) -> tuple[str, float]:
        t = time.perf_counter()
        r = self.client.post(f"{self.url}/api/chat", json={
            "model": self.modell, "stream": False, "think": False, "options": {"temperature": 0, "num_ctx": 8192},
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": nutzer}]})
        r.raise_for_status()
        return r.json()["message"]["content"], time.perf_counter() - t

    def einbetten(self, texte: list[str]) -> list[list[float]]:
        r = self.client.post(f"{self.url}/api/embed", json={"model": self.einbettungsmodell, "input": texte,
                                                            "options": self.einbettung_optionen})
        r.raise_for_status()
        return r.json()["embeddings"]
