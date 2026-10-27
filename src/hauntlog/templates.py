"""Page templates, kept in one module so the app is a single small package with no data files."""

BASE = """<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>{% block title %}Hauntlog{% endblock %}</title>
<style>
:root{--bg:#0d0f14;--card:#151922;--ink:#e4e2dc;--muted:#8b909b;--line:#262b38;--accent:#9b7bd4;--glow:#c9b2f5;--warn:#d9825b;--mark:#3a2f55;
--serif:Georgia,"Iowan Old Style","Palatino Linotype",serif;--sans:system-ui,-apple-system,"Segoe UI",Roboto,sans-serif;--mono:ui-monospace,"Cascadia Code",Menlo,Consolas,monospace}
*{box-sizing:border-box}body{margin:0;background:radial-gradient(60rem 30rem at 50% -10rem,#1b1630,var(--bg));background-color:var(--bg);color:var(--ink);font:17px/1.6 var(--sans);min-height:100vh}
a{color:var(--glow)}header{border-bottom:1px solid var(--line);padding:.8rem clamp(1rem,4vw,2.5rem);display:flex;gap:1.5rem;align-items:center}
header .brand{font:700 1.25rem var(--serif);letter-spacing:.04em;text-decoration:none;color:var(--glow);text-shadow:0 0 12px #6b4fb066}
main{max-width:46rem;margin:0 auto;padding:1.5rem clamp(1rem,4vw,2rem) 4rem}h1{font:400 2rem/1.2 var(--serif);margin:.3rem 0 .5rem}h2{font:400 1.2rem var(--serif);margin:0 0 .5rem}
.lede{color:var(--muted);margin:0 0 1.5rem}.card{background:var(--card);border:1px solid var(--line);border-radius:8px;padding:1.1rem 1.3rem;margin:0 0 1.1rem}
label{display:block;font-weight:600;font-size:.85rem;color:var(--muted);margin:.8rem 0 .25rem}input,textarea{width:100%;font:inherit;padding:.55rem .7rem;border:1px solid var(--line);border-radius:6px;background:#0f1219;color:var(--ink)}
textarea{min-height:11rem;font:.85rem/1.5 var(--mono)}.btn{font:600 .95rem var(--sans);border:0;border-radius:6px;padding:.6rem 1.1rem;background:var(--accent);color:#120d1f;cursor:pointer}
.btn.quiet{background:transparent;color:var(--glow);box-shadow:inset 0 0 0 1.5px var(--accent)}.btn.small{padding:.4rem .8rem;font-size:.88rem}
.error{background:#2b1914;border-left:4px solid var(--warn);padding:.6rem .9rem;margin:0 0 1rem;border-radius:4px}.hint{color:var(--muted);font-size:.9rem}
.scene{font:1.15rem/1.65 var(--serif);margin:.2rem 0 .6rem}.proof{font:.82rem var(--mono);color:var(--muted);border-left:3px solid var(--accent);padding:.15rem .7rem;background:#10131b}
.proof b{color:var(--glow);margin-right:.5rem}.pill{display:inline-block;font:700 .7rem var(--sans);padding:.1rem .5rem;border-radius:1rem;background:var(--mark);color:var(--glow);letter-spacing:.05em;text-transform:uppercase}
.lie{border-color:var(--warn)}.lie .hint{color:#e0a88f}.dread{font-size:1.3rem;letter-spacing:.25rem;color:var(--glow)}.dread .off{color:#2c3040}
pre.log{white-space:pre-wrap;font:.8rem/1.6 var(--mono);margin:0;color:#b8bcc8}mark{background:var(--mark);color:var(--glow);padding:0 .15rem}
pre.copy{white-space:pre-wrap;font:.9rem/1.55 var(--serif);margin:0}details summary{cursor:pointer;font-weight:600}
footer{color:var(--muted);font-size:.85rem;padding:1rem clamp(1rem,4vw,2rem);max-width:46rem;margin:0 auto}
</style></head><body>
<header><a class="brand" href="/">&#9789; Hauntlog</a></header>
<main>{% block content %}{% endblock %}</main>
<footer>Everything stays on this computer: your sensor log and the stories. Told by {{ model_label }}, running locally.</footer>
<script>document.addEventListener('submit',function(e){var b=e.target.querySelector('[data-wait]');if(b){b.disabled=true;b.textContent=b.dataset.wait;}});</script>
</body></html>"""

INDEX = """{% extends "base.html" %}{% block content %}
<h1>What happened while you slept?</h1>
<p class="lede">Paste a night of your smart home's sensor log. A local model tells the ghost story hiding in it, and every haunted moment has to point at a real log line.</p>
{% if error %}<p class="error" role="alert">{{ error }}</p>{% endif %}
{% for n in nights %}<div class="card"><h2><a href="/nights/{{ n.id }}">{{ n.name }}</a></h2><span class="hint">{{ n.created_at[:10] }}</span></div>{% endfor %}
<div class="card"><h2>Add a night</h2><form method="post" action="/nights">
<label for="name">Which house?</label><input id="name" name="name" required>
<label for="text">The sensor log (any text, one event per line, with times)</label><textarea id="text" name="text" required placeholder="2026-10-27 02:14:09 hallway motion sensor: motion detected"></textarea>
<p><button class="btn" type="submit">Add night</button></p></form></div>
{% endblock %}"""

NIGHT = """{% extends "base.html" %}{% block title %}{{ n.name }} &middot; Hauntlog{% endblock %}{% block content %}
<h1>{{ n.name }}</h1><p class="lede">Ask the house what it saw.</p>
{% if error %}<p class="error" role="alert">{{ error }}</p>{% endif %}
{% if long %}<p class="error">This log is longer than {{ 24000 }} characters. Only the start is sent to the model.</p>{% endif %}
<form method="post" action="/nights/{{ n.id }}/tell"><p><button class="btn" type="submit" data-wait="The house is remembering&hellip;">Tell me what happened</button></p></form>
{% if stories %}<h2>Stories told</h2>{% for s in stories %}<div class="card"><a href="/stories/{{ s.id }}">{{ s.title }}</a> <span class="hint">{{ s.at[:10] }}</span>
<span class="dread" title="dread, computed from the log">{% for i in range(5) %}{{ '&#9679;'|safe if i < s.dread else '' }}{% endfor %}</span></div>{% endfor %}{% endif %}
<details class="card"><summary>The log on file</summary><pre class="log">{{ n.log }}</pre></details>
{% endblock %}"""

STORY = """{% extends "base.html" %}{% block title %}{{ s.title }} &middot; Hauntlog{% endblock %}{% block content %}
<p><a href="/nights/{{ n.id }}">&larr; {{ n.name }}</a></p><h1>{{ s.title }}</h1>
<p class="hint">Dread <span class="dread">{% for i in range(5) %}{% if i < s.dread %}&#9679;{% else %}<span class="off">&#9679;</span>{% endif %}{% endfor %}</span>
&nbsp;computed from the log lines, not by the model.</p>
{% if not beats %}<p class="card scene">{{ quiet }}</p>{% endif %}
{% if beats and s.opening %}<p class="scene">{{ s.opening }}</p>{% endif %}
{% for b in beats %}<div class="card"><span class="pill">{{ b.mood }}</span>
<p class="scene">{{ b.scene }}</p><div class="proof"><b>{{ b.when or 'log' }}</b>{{ b.line }}</div></div>{% endfor %}
{% if beats and s.ending %}<p class="scene">{{ s.ending }}</p>{% endif %}
{% if lies %}<div class="card lie"><h2>The house lied</h2><p class="hint">{{ lies|length }} haunted moment{{ 's' if lies|length != 1 }} cited a log line that does not exist, so {{ 'they were' if lies|length != 1 else 'it was' }} dropped:</p>
{% for l in lies %}<div class="proof">{{ l.claimed }}</div>{% endfor %}</div>{% endif %}
<div class="card"><h2>Take it with you</h2><pre class="copy" id="copy">{{ text }}</pre>
<p><button class="btn small" type="button" onclick="navigator.clipboard.writeText(document.getElementById('copy').innerText)">Copy</button></p></div>
<details class="card"><summary>The log, with the cited lines marked</summary><pre class="log">{{ log }}</pre></details>
{% endblock %}"""

TEMPLATES = {"base.html": BASE, "index.html": INDEX, "night.html": NIGHT, "story.html": STORY}
