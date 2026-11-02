from fastapi.testclient import TestClient

from app.main import app

c = TestClient(app)


def test_ohne_anmeldung():
    assert c.get("/api/faelle").status_code == 403
    assert c.get("/", follow_redirects=False).headers["location"] == "/anmelden"


def test_anmeldung_und_rollen():
    c.cookies.clear()
    r = c.post("/anmelden", data={"kennung": "sb.a", "passwort": "falsch"}, follow_redirects=False)
    assert r.status_code == 200 and "fehlgeschlagen" in r.text
    r = c.post("/anmelden", data={"kennung": "admin", "passwort": "nur-fuer-tests"}, follow_redirects=False)
    assert r.headers["location"] == "/protokoll"
    assert c.get("/api/faelle").status_code == 403          # Administration sieht keine Fälle
    assert c.get("/api/protokoll/pruefen").json()["in_ordnung"]
    assert c.get("/openapi.json").status_code == 200
