"""The rules. A model reads a night of smart-home sensor logs and *proposes* haunted moments; this module
decides which of them count.

1. **A haunting must be in the log.** Every beat quotes a log line, and the quote must be found in the log
   (ignoring case, punctuation and line breaks). If it is not, the beat is dropped as invented. The house
   cannot haunt itself with events that never happened.
2. **Silence is not a haunting.** A quiet night is told as a quiet night. The model is never asked to fill it.
3. **The model never writes a time or a number.** Times and readings come from the verified log line, copied
   by code. A scene or title containing a digit is replaced.
4. **Dread is computed, not declared.** The dread meter comes from the verified lines (night hours, doors,
   motion, cold), so it cannot be inflated by a dramatic model.
"""

from __future__ import annotations

import math
import re
import unicodedata
from typing import Any

MOODS = ("uneasy", "watching", "cold", "restless", "tender")
MIN_QUOTE_WORDS = 3
MAX_LOG_CHARS = 24000
MAX_BEATS = 14
DEFAULT_TITLE = "The Night Shift"
DEFAULT_SCENE = "Something in the house noticed, and said nothing."
QUIET = "Nothing stirred. The sensors kept watch all night and found only the dark, which is not a haunting."

SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "title": {"type": "string"},
        "opening": {"type": "string"},
        "ending": {"type": "string"},
        "beats": {"type": "array", "items": {
            "type": "object",
            "properties": {
                "log_quote": {"type": "string"},
                "scene": {"type": "string"},
                "mood": {"type": "string", "enum": list(MOODS)},
            },
            "required": ["log_quote", "scene", "mood"],
            "additionalProperties": False}},
    },
    "required": ["title", "opening", "beats", "ending"],
    "additionalProperties": False,
}


# --- finding a log line --------------------------------------------------------------------------------


def _norm(token: str) -> str:
    token = unicodedata.normalize("NFKC", token).casefold()
    start, end = 0, len(token)
    while start < end and unicodedata.category(token[start])[0] in "PS":
        start += 1
    while end > start and unicodedata.category(token[end - 1])[0] in "PS":
        end -= 1
    return token[start:end]


def _tokens(text: str) -> list[tuple[str, int, int]]:
    out = []
    for m in re.finditer(r"\S+", text):
        n = _norm(m.group())
        if n:
            out.append((n, m.start(), m.end()))
    return out


def locate(quote: str, log: str) -> tuple[int, int] | None:
    """Where `quote` sits in `log` as (start, end) characters, or None. Case, whitespace and punctuation
    differences are ignored; a different word or number is not."""
    q = [t[0] for t in _tokens(quote or "")]
    if len(q) < MIN_QUOTE_WORDS:
        return None
    c = _tokens(log)
    words = [t[0] for t in c]
    for i in range(len(words) - len(q) + 1):
        if words[i:i + len(q)] == q:
            return c[i][1], c[i + len(q) - 1][2]
    return None


def line_at(log: str, span: tuple[int, int]) -> tuple[str, tuple[int, int]]:
    """The whole log line a span sits in, and that line's own span."""
    a = log.rfind("\n", 0, span[0]) + 1
    b = log.find("\n", span[1])
    b = len(log) if b == -1 else b
    return log[a:b].strip(), (a, b)


def clock(line: str) -> tuple[str, int | None]:
    """The time as written in the log line ('02:14'), and its hour. ('', None) if the line has no time."""
    m = re.search(r"(?<!\d)([01]?\d|2[0-3]):([0-5]\d)(?::[0-5]\d)?(?!\d)", line)
    return (f"{int(m.group(1)):02d}:{m.group(2)}", int(m.group(1))) if m else ("", None)


# --- turning a model reply into verified beats -----------------------------------------------------------

SPOOKY = re.compile(r"\b(motion|opened|unlock\w*|knock\w*|alarm|dropped|offline|unknown|no\s+\w+\s+entry)\b", re.I)


def is_night(hour: int | None) -> bool:
    return hour is not None and (hour >= 22 or hour < 5)


def clean_text(text: Any, limit: int, default: str) -> str:
    text = " ".join(str(text or "").split())
    return text if text and len(text) <= limit and not re.search(r"\d", text) else default


def review(raw: dict, log: str) -> list[dict]:
    """Verified beats in log order, followed by the beats the model invented (kept only so we can say so)."""
    good, invented, seen = [], [], set()
    for b in (raw.get("beats") or [])[:MAX_BEATS]:
        if not isinstance(b, dict):
            continue
        quote = str(b.get("log_quote") or "")
        span = locate(quote, log)
        if span is None:
            invented.append({"verified": False, "claimed": " ".join(quote.split())[:200]})
            continue
        line, line_span = line_at(log, span)
        if line_span in seen:
            continue
        seen.add(line_span)
        when, hour = clock(line)
        mood = b.get("mood") if b.get("mood") in MOODS else "uneasy"
        weight = 1 + is_night(hour) + bool(SPOOKY.search(line))
        good.append({"verified": True, "line": line, "span": line_span, "when": when, "night": is_night(hour), "mood": mood,
                     "scene": clean_text(b.get("scene"), 700, DEFAULT_SCENE), "weight": weight})
    good.sort(key=lambda x: x["span"][0])
    return good + invented


def dread(items: list[dict]) -> int:
    """0 (quiet) to 5 (leave the house), from the verified log lines only."""
    total = sum(i["weight"] for i in items if i["verified"])
    return min(5, math.ceil(total / 3))


def title(raw_title: Any) -> str:
    return clean_text(raw_title, 80, DEFAULT_TITLE)


def story_text(name: str, ttl: str, items: list[dict], opening: str = "", ending: str = "") -> str:
    """The story as plain text to copy: each scene sits under the log line that proves it."""
    beats = [i for i in items if i["verified"]]
    lines = [ttl, f"(a night at {name})", ""]
    if not beats:
        return "\n".join(lines + [QUIET, ""])
    if opening:
        lines += [opening, ""]
    for i in beats:
        lines += [i["scene"], f"    [log] {i['line']}", ""]
    if ending:
        lines += [ending, ""]
    return "\n".join(lines)


def prompt(log: str) -> str:
    return f"""You are a gifted ghost-story writer. Your only source is the smart-home sensor log below: the record of one night in a house while its owner slept.

Write ONE connected story with a beginning, a build and an end, as if the house itself were haunted. Choose every line that could be eerie (motion with nobody awake, taps, doors, cold rooms, unknown sources, locks, speakers, lights) and use them in the order they happened.

Fields:
- "title": a short spooky title, no numbers.
- "opening": two or three sentences setting the scene before the first event: the house at bedtime, the quiet, the sleeper. No times or numbers.
- "beats": one per eerie log line, in log order. For each:
  - "log_quote": copied word for word from ONE line of the log (a few words is enough). Never paraphrase it, never invent a line.
  - "scene": three or four vivid sentences in the second person, with sensory detail (sound, cold, smell, shadow) that follow on from the previous scene, so the story builds and the dread rises. Say what that log line really means, but make it feel haunted. No times, no numbers, no readings.
  - "mood": one of uneasy, watching, cold, restless, tender.
- "ending": two or three sentences for the morning after, quietly unsettling. No times or numbers.

Rules:
- Every beat must be backed by a real log line. Do not invent events, rooms or devices that are not in the log.
- If the log is ordinary, write few beats or none.
- Dull lines (lights off, routine alarms) can be skipped, or used as calm before or after the fear.

SENSOR LOG
{log[:MAX_LOG_CHARS]}

Reply with only the JSON object."""
