"""Weboberfläche und REST-Schnittstelle (OpenAPI unter /docs). Start: uvicorn app.main:app"""
import os
from pathlib import Path

from fastapi import FastAPI, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from . import assistent, audit, auth, config, db, dienst, regeln, suche
from .llm import Sprachmodell

E = config.laden()
CON = db.verbinden(E.datenbank)
KONF = regeln.laden(E.unterlagen_konfiguration)
MODELL = Sprachmodell(E.ollama_url, E.sprachmodell, E.einbettungsmodell)
NORMEN = suche.Normen(E.normen) if E.normen.exists() else None
dienst.einrichten(CON, E.demo_passwort)
if os.environ.get("DEMO_FAELLE"):
    dienst.demo_faelle(CON, int(os.environ["DEMO_FAELLE"]))

HIER = Path(__file__).resolve().parent
app = FastAPI(title="Antragsassistent (Prototyp)", version="0.1.0",
              description="KI-assistierte Antragsbearbeitung mit synthetischen Daten. Das System entscheidet nichts.")
app.mount("/static", StaticFiles(directory=HIER / "static"), name="static")
seiten = Jinja2Templates(directory=HIER / "templates")
COOKIE = "sitzung"


def wer(request: Request):
    return dienst.benutzer(CON, auth.sitzung_lesen(request.cookies.get(COOKIE), E.sitzungsschluessel))


def zeigen(request: Request, vorlage: str, **kw):
    return seiten.TemplateResponse(request, vorlage, {"b": wer(request), "modell": E.sprachmodell, **kw})


@app.exception_handler(dienst.Verboten)
def verboten(request: Request, exc):
    if request.url.path.startswith("/api/"):
        return JSONResponse({"fehler": "keine Berechtigung"}, status_code=403)
    if wer(request) is None:
        return RedirectResponse("/anmelden", status_code=303)
    return HTMLResponse("Keine Berechtigung für diese Seite.", status_code=403)


@app.get("/gesund")
def gesund():
    return {"ok": True, "normen": len(NORMEN.absaetze) if NORMEN else 0}


@app.get("/anmelden", response_class=HTMLResponse)
def anmelden_seite(request: Request):
    return zeigen(request, "anmelden.html", fehler=None)


@app.post("/anmelden")
def anmelden(request: Request, kennung: str = Form(...), passwort: str = Form(...)):
    b = dienst.anmelden(CON, kennung, passwort)
    if b is None:
        return zeigen(request, "anmelden.html", fehler="Anmeldung fehlgeschlagen.")
    ziel = "/protokoll" if b["rolle"] == "administration" else "/"
    r = RedirectResponse(ziel, status_code=303)
    r.set_cookie(COOKIE, auth.sitzung_ausstellen(b["kennung"], E.sitzungsschluessel), httponly=True, samesite="strict")
    return r


@app.get("/abmelden")
def abmelden():
    r = RedirectResponse("/anmelden", status_code=303)
    r.delete_cookie(COOKIE)
    return r


@app.get("/", response_class=HTMLResponse)
def start(request: Request):
    return zeigen(request, "faelle.html", faelle=dienst.faelle(CON, wer(request)))


@app.get("/fall/{fall_id}", response_class=HTMLResponse)
def fall(request: Request, fall_id: str, meldung: str | None = None):
    try:
        a = dienst.ansicht(CON, KONF, wer(request), fall_id)
    except KeyError:
        raise HTTPException(404)
    return zeigen(request, "fall.html", a=a, konf=KONF, meldung=meldung,
                  darf_entscheiden=auth.darf(wer(request)["rolle"], "entscheiden"))


def _zurueck(fall_id: str, meldung: str = ""):
    return RedirectResponse(f"/fall/{fall_id}" + (f"?meldung={meldung}" if meldung else ""), status_code=303)


@app.post("/fall/{fall_id}/analysieren")
def analysieren(request: Request, fall_id: str):
    r = dienst.analysieren(CON, MODELL, KONF, wer(request), fall_id, E.prompt_version)
    return _zurueck(fall_id, f"{r['dokumente']} Dokumente in {r['sekunden']} s ausgewertet")


@app.post("/vorschlag/{vid}")
def entscheidung(request: Request, vid: int, fall_id: str = Form(...), entscheidung: str = Form(...),
                 endwert: str = Form("")):
    try:
        dienst.entscheiden(CON, wer(request), vid, entscheidung, endwert)
    except ValueError as e:
        return _zurueck(fall_id, str(e))
    return _zurueck(fall_id)


@app.post("/fall/{fall_id}/prueffertig")
def prueffertig(request: Request, fall_id: str):
    try:
        dienst.prueffertig(CON, KONF, wer(request), fall_id)
    except ValueError as e:
        return _zurueck(fall_id, str(e))
    return _zurueck(fall_id, "Fall ist prüffertig")


@app.get("/assistent", response_class=HTMLResponse)
def assistent_seite(request: Request, frage: str | None = None):
    b = wer(request)
    dienst._pruefe(b, "assistent")
    ergebnis = None
    if frage:
        ergebnis = assistent.beantworten(frage, NORMEN, MODELL)
        audit.eintragen(CON, "assistent_frage", {"frage": frage, "zitate": ergebnis["zitate"],
                                                 "unbelegt": ergebnis["unbelegt"], "modell": E.sprachmodell},
                        b["kennung"], b["jobcenter_id"])
    return zeigen(request, "assistent.html", frage=frage or "", e=ergebnis)


@app.get("/protokoll", response_class=HTMLResponse)
def protokoll(request: Request):
    b = wer(request)
    dienst._pruefe(b, "kette_pruefen")
    zeilen = []
    if auth.darf(b["rolle"], "protokoll_lesen"):
        zeilen = CON.execute("SELECT * FROM protokoll WHERE jobcenter_id = ? ORDER BY nr DESC LIMIT 200",
                             (b["jobcenter_id"],)).fetchall()
    return zeigen(request, "protokoll.html", kette=audit.pruefen(CON), zeilen=zeilen)


# --- REST ------------------------------------------------------------------------------------------------------------
@app.get("/api/faelle")
def api_faelle(request: Request):
    return [dict(f) for f in dienst.faelle(CON, wer(request))]


@app.get("/api/faelle/{fall_id}/export")
def api_export(request: Request, fall_id: str):
    try:
        return dienst.export(CON, KONF, wer(request), fall_id)
    except ValueError as e:
        return JSONResponse({"fehler": str(e)}, status_code=409)


@app.get("/api/protokoll/pruefen")
def api_kette(request: Request):
    dienst._pruefe(wer(request), "kette_pruefen")
    ok, n, text = audit.pruefen(CON)
    return {"in_ordnung": ok, "eintraege": n, "meldung": text}
