"""`hauntlog`: start the app on this computer only (127.0.0.1), after checking the model is there."""

from __future__ import annotations

import argparse
import shutil
import sys
import tempfile
from pathlib import Path

import httpx


def model_problem(model: str) -> str | None:
    from hauntlog.llm import host

    try:
        names = {m["name"] for m in httpx.get(f"{host()}/api/tags", timeout=3).json().get("models", [])}
    except (httpx.HTTPError, ValueError):
        return f"Ollama is not answering at {host()}. Install it from https://ollama.com and run `ollama serve`."
    if model not in names and f"{model}:latest" not in names:
        return f"{model} is not pulled. Run: ollama pull {model}"
    return None


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(prog="hauntlog", description="A local ghost story generator for your smart home's sensor log.")
    ap.add_argument("--port", type=int, default=8666)
    ap.add_argument("--host", default="127.0.0.1", help="127.0.0.1 keeps it to this computer (the default)")
    ap.add_argument("--demo", action="store_true", help="a sample night and canned answers, no model needed")
    args = ap.parse_args(argv)

    import uvicorn

    from hauntlog.app import create_app
    from hauntlog.llm import DEMO_LOG, DemoClient, OllamaClient
    from hauntlog.store import Store

    if args.demo:
        home = Path(tempfile.gettempdir()) / "hauntlog-demo"
        shutil.rmtree(home, ignore_errors=True)
        store = Store(home)
        store.add_night(name="The house on Hollow Street", log=DEMO_LOG)
        app = create_app(store, DemoClient(), model_label="canned demo answers, no model loaded")
    else:
        client = OllamaClient()
        if problem := model_problem(client.model):
            print(f"  ! {problem}", file=sys.stderr)
        store = Store()
        app = create_app(store, client)
    print(f"\n  Hauntlog is running on this computer only: http://localhost:{args.port}/")
    print(f"  Your records: {store.home}   (copy to keep, delete to forget)\n")
    uvicorn.run(app, host=args.host, port=args.port, log_level="warning")


if __name__ == "__main__":
    main()
