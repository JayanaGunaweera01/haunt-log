"""The open model, run by Ollama on this computer. Nothing here talks to anything but localhost."""

from __future__ import annotations

import json
import os

import httpx

from hauntlog.core import SCHEMA, prompt


def host() -> str:
    h = os.environ.get("OLLAMA_HOST", "127.0.0.1:11434").strip()
    return h if h.startswith("http") else f"http://{h}"


class OllamaClient:
    """Ollama's native API with a JSON Schema in `format`, so decoding is constrained and every reply parses."""

    def __init__(self, model: str | None = None, timeout: float | None = None, transport: httpx.BaseTransport | None = None):
        self.model = model or os.environ.get("HAUNTLOG_MODEL", "gemma4:e4b")
        self.timeout = timeout or float(os.environ.get("HAUNTLOG_TIMEOUT_S", "600"))
        self.transport = transport

    def tell(self, log: str) -> dict:
        body = {"model": self.model, "stream": False, "think": False, "format": SCHEMA,
                "options": {"temperature": 0.9, "num_ctx": 16384, "num_predict": 3000},
                "messages": [{"role": "user", "content": prompt(log)}]}
        with httpx.Client(timeout=self.timeout, transport=self.transport) as c:
            r = c.post(f"{host()}/api/chat", json=body)
            r.raise_for_status()
        return json.loads(r.json()["message"]["content"])


DEMO_LOG = """2026-10-26 22:41:05 front door lock: locked (keypad, Jayana)
2026-10-26 23:30:12 living room lights: switched off
2026-10-27 01:07:44 thermostat hallway: reading 21.0 C
2026-10-27 02:14:09 hallway motion sensor: motion detected
2026-10-27 02:14:31 kitchen tap: flow started for 4 seconds
2026-10-27 02:47:03 thermostat study: reading 14.5 C
2026-10-27 03:03:33 study door contact sensor: opened
2026-10-27 03:03:40 smart speaker: playing audio, source unknown, volume 12
2026-10-27 03:33:33 front door lock: unlock attempt, no keypad entry
2026-10-27 04:12:58 hallway motion sensor: no motion
2026-10-27 06:30:00 bedroom alarm clock: rang
2026-10-27 06:30:41 coffee machine: brew started
"""


class DemoClient:
    """Canned answers for trying the app without a model. It only recognises the demo log, and it includes one
    invented event on purpose, so you can watch the app throw it out."""

    def tell(self, log: str) -> dict:
        def b(q, s, m):
            return {"log_quote": q, "scene": s, "mood": m}

        return {"title": "The Night the Study Went Cold",
                "opening": "The house settled into its bedtime hush, the doors locked, the lights out, the sleeper breathing slowly in the dark. Nothing in it was waiting. Not yet.",
                "ending": "Morning came back with its alarm and its coffee, as if nothing had happened. But the study door stayed open, and the house would not say who had left it that way.",
                "beats": [
            b("hallway motion sensor: motion detected", "The hallway had no one awake to notice, and still something walked its whole length.", "watching"),
            b("kitchen tap: flow started", "The tap ran just long enough to rinse something that had no hands.", "uneasy"),
            b("thermostat study: reading 14.5 C", "The study went cold, the way a room does when someone stops pretending to be alive.", "cold"),
            b("basement piano sensor: key pressed", "Down below, the piano answered a question nobody asked.", "restless"),  # never happened
            b("study door contact sensor: opened", "The door opened from the inside, politely, like it had always been allowed.", "restless"),
            b("smart speaker: playing audio, source unknown", "A song began that nobody had chosen, and nobody would remember.", "uneasy"),
            b("front door lock: unlock attempt, no keypad entry", "At the front door, someone who already lived here tried to come in.", "watching"),
            b("coffee machine: brew started", "By morning the house was polite again. The coffee was already warm.", "tender"),
        ]}
