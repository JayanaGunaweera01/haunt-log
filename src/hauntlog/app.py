"""The web app, served only on this computer.

    /                a list of your nights (sensor logs) and a form to add one
    /nights/<id>     the log, a button to hear what happened, past stories
    /stories/<id>    the story, each scene under the log line that proves it, the log with those lines marked
"""

from __future__ import annotations

import logging
from typing import Annotated

import httpx
from anyio import to_thread
from fastapi import FastAPI, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from jinja2 import DictLoader, Environment, select_autoescape
from markupsafe import Markup, escape

from hauntlog import core
from hauntlog.store import Store
from hauntlog.templates import TEMPLATES

log = logging.getLogger(__name__)


def highlighted(text: str, spans: list[tuple[int, int]]) -> Markup:
    """The log with each cited line marked, so you can see exactly what the story rests on."""
    out, pos = [], 0
    for n, (a, b) in enumerate(sorted(s for s in spans if s), start=1):
        if a < pos:
            continue
        out += [escape(text[pos:a]), Markup(f'<mark id="line-{n}">'), escape(text[a:b]), Markup("</mark>")]
        pos = b
    out.append(escape(text[pos:]))
    return Markup("").join(out)


def create_app(store: Store | None = None, client=None, *, model_label: str = "") -> FastAPI:
    store = store or Store()
    if client is None:
        from hauntlog.llm import OllamaClient

        client = OllamaClient()
    model_label = model_label or getattr(client, "model", "an open model")
    app = FastAPI(title="Hauntlog", docs_url=None, redoc_url=None)
    app.state.store = store
    env = Environment(loader=DictLoader(TEMPLATES), autoescape=select_autoescape(["html"]), trim_blocks=True, lstrip_blocks=True)
    env.globals.update(model_label=model_label)

    def page(name: str, status: int = 200, **ctx) -> HTMLResponse:
        return HTMLResponse(env.get_template(name).render(**ctx), status_code=status)

    @app.get("/")
    async def index(error: str = ""):
        return page("index.html", nights=store.nights(), error=error)

    @app.post("/nights")
    async def add_night(name: Annotated[str, Form()] = "", text: Annotated[str, Form()] = ""):
        if not name.strip() or len(text.split()) < 8:
            return RedirectResponse("/?error=Name the house and paste a night of sensor log.", status_code=303)
        nid = store.add_night(name=name.strip()[:80], log=text.strip())
        return RedirectResponse(f"/nights/{nid}", status_code=303)

    @app.get("/nights/{nid}")
    async def night_page(nid: int, error: str = ""):
        n = store.night(nid)
        if n is None:
            raise HTTPException(404)
        return page("night.html", n=n, stories=store.stories(nid), error=error, long=len(n["log"]) > core.MAX_LOG_CHARS)

    @app.post("/nights/{nid}/tell")
    async def tell(nid: int):
        n = store.night(nid)
        if n is None:
            raise HTTPException(404)
        try:
            raw = await to_thread.run_sync(client.tell, n["log"])
        except (httpx.HTTPError, ValueError, KeyError) as e:
            log.warning("model call failed: %s", e)
            hint = "The house did not answer. Is Ollama running, and is the model pulled? Try `ollama list`."
            return RedirectResponse(f"/nights/{nid}?error={hint}", status_code=303)
        items = core.review(raw, n["log"])
        sid = store.add_story(night_id=nid, title=core.title(raw.get("title")), items=items, dread=core.dread(items),
                             opening=core.clean_text(raw.get("opening"), 700, ""), ending=core.clean_text(raw.get("ending"), 700, ""))
        return RedirectResponse(f"/stories/{sid}", status_code=303)

    @app.get("/stories/{sid}")
    async def story_page(sid: int):
        s = store.story(sid)
        if s is None:
            raise HTTPException(404)
        n = store.night(s["night_id"])
        beats = [i for i in s["items"] if i["verified"]]
        lies = [i for i in s["items"] if not i["verified"]]
        text = core.story_text(n["name"], s["title"], s["items"], s.get("opening", ""), s.get("ending", ""))
        return page("story.html", s=s, n=n, beats=beats, lies=lies, text=text, quiet=core.QUIET,
                    log=highlighted(n["log"], [tuple(i["span"]) for i in beats]))

    return app
