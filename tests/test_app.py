import json

import httpx
from fastapi.testclient import TestClient

from hauntlog.app import create_app
from hauntlog.llm import DEMO_LOG, DemoClient, OllamaClient
from hauntlog.store import Store


def make(tmp_path, client=None):
    store = Store(tmp_path)
    return TestClient(create_app(store, client or DemoClient(), model_label="test")), store


def add_night(web):
    r = web.post("/nights", data={"name": "Hollow Street", "text": DEMO_LOG}, follow_redirects=False)
    assert r.status_code == 303
    return r.headers["location"]


def test_the_whole_flow_add_tell_read_and_see_the_lie(tmp_path):
    web, _ = make(tmp_path)
    assert "What happened while you slept" in web.get("/").text
    url = add_night(web)
    r = web.post(f"{url}/tell", follow_redirects=False)
    page = web.get(r.headers["location"]).text
    assert "The Night the Study Went Cold" in page and "bedtime hush" in page and "02:14" in page and "03:33" in page
    assert "<mark id=\"line-1\">2026-10-27 02:14:09 hallway motion sensor: motion detected</mark>" in page
    assert "The house lied" in page and "basement piano sensor: key pressed" in page and "Dread" in page
    assert "The Night the Study Went Cold" in web.get(url).text


def test_a_model_cannot_haunt_a_quiet_log(tmp_path):
    class Liar:
        def tell(self, log):
            return {"title": "Doom", "beats": [{"log_quote": "the ghost of grandmother appeared", "scene": "Boo.", "mood": "cold"}]}

    web, _ = make(tmp_path, Liar())
    r = web.post(f"{add_night(web)}/tell", follow_redirects=False)
    page = web.get(r.headers["location"]).text
    assert "Nothing stirred" in page and "Boo." not in page and "The house lied" in page


def test_validation_and_model_failure_are_explained(tmp_path):
    class Down:
        def tell(self, log):
            raise httpx.ConnectError("refused")

    web, _ = make(tmp_path, Down())
    assert "Name the house" in web.post("/nights", data={"name": "", "text": "short"}).text
    assert "Is Ollama running" in web.post(f"{add_night(web)}/tell").text
    assert web.get("/stories/999").status_code == 404


def test_log_text_is_escaped(tmp_path):
    web, _ = make(tmp_path)
    r = web.post("/nights", data={"name": "<b>x</b>", "text": "02:00 <script>alert(1)</script> sensor says hello to the empty hallway"},
                 follow_redirects=False)
    page = web.get(r.headers["location"]).text
    assert "<script>alert(1)</script>" not in page and "&lt;script&gt;" in page


def test_the_ollama_request_is_local_schema_constrained_and_parsed():
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["url"], seen["body"] = str(request.url), json.loads(request.content)
        return httpx.Response(200, json={"message": {"content": json.dumps({"title": "T", "beats": []})}})

    out = OllamaClient("m", transport=httpx.MockTransport(handler)).tell(DEMO_LOG)
    assert out == {"title": "T", "beats": []}
    assert seen["url"].startswith("http://127.0.0.1:11434/") and seen["body"]["think"] is False
    assert seen["body"]["format"]["required"] == ["title", "opening", "beats", "ending"] and "hallway motion sensor" in seen["body"]["messages"][0]["content"]
