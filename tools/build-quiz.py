"""Generate a pack's quiz.html from its questions.md, answers.md and scenario-questions.md.

Usage:
    python tools/build-quiz.py 01-java
    python tools/build-quiz.py 02-spring
    python tools/build-quiz.py            # every pack that has the three source files

The output is a single self-contained file that works offline from file://.
"""

import html
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

DIFFICULTY = {
    "C": ("Core", "You must answer this instantly and correctly."),
    "D": ("Deep", "Requires mechanism-level detail."),
    "T": ("Tricky", "The obvious answer is usually wrong."),
    "A": ("Architect", "Judged on trade-off reasoning."),
}

# Per-pack presentation. Anything not listed here falls back to the defaults below.
PACKS = {
    "01-java": {
        "subtitle": "Principal / Lead / Solution Architect preparation. Answer out loud before expanding.",
        "frameworks": "README.md",
        # Predates the shared generator; kept so saved progress is not orphaned.
        "store": "java-interview-progress-v1",
    },
    "02-spring": {
        "subtitle": "Container internals, transactions, security and production engineering. Answer out loud before expanding.",
        "frameworks": "../01-java/README.md",
    },
    "03-microservices": {
        "subtitle": "Boundaries, event-driven architecture, distributed data, resilience and release engineering. Answer out loud before expanding.",
        "frameworks": "../01-java/README.md",
    },
    "04-system-design": {
        "subtitle": "Framing, estimation, component selection, geo-distribution and AI in the request path. Answer out loud before expanding.",
        "frameworks": "../01-java/README.md",
    },
    "05-aws": {
        "subtitle": "Serverless architecture, event-driven mechanics, quotas, multi-region and cost. Answer out loud before expanding.",
        "frameworks": "../01-java/README.md",
    },
    "05-aws/core-services": {
        "subtitle": "EC2, storage, load balancing, Route 53, VPC at scale, RDS, containers and migration. Answer out loud before expanding.",
        "frameworks": "../../01-java/README.md",
        # Nested pack: the directory name alone is not unique across the repo.
        "store": "interview-progress-05-aws-core-v1",
    },
    "06-database": {
        "subtitle": "Relational internals, transactions, scaling and polyglot persistence. Answer out loud before expanding.",
        "frameworks": "../01-java/README.md",
    },
    "07-devops": {
        "subtitle": "Delivery pipelines, Kubernetes, GitOps, observability and incident response. Answer out loud before expanding.",
        "frameworks": "../01-java/README.md",
    },
    "08-genai": {
        "subtitle": "Transformer behavior, tokens, decoding, prompting, evaluation, safety, serving and cost. Answer out loud before expanding.",
        "frameworks": "../01-java/README.md",
    },
    "09-rag": {
        "subtitle": "Ingestion, chunking, embeddings, ANN indexes, hybrid search, reranking, permissions, evaluation and serving. Answer out loud before expanding.",
        "frameworks": "../01-java/README.md",
    },
    "10-ai-agents": {
        "subtitle": "Agent loops, tools, planning, memory, multi-agent topologies, durability, security, evaluation and cost. Answer out loud before expanding.",
        "frameworks": "../01-java/README.md",
    },
    "11-security": {
        "subtitle": "AppSec, identity, cryptography, supply chain, cloud, AI security and incident response. Answer out loud before expanding.",
        "frameworks": "../01-java/README.md",
    },
    "12-behavioural": {
        "subtitle": "Competencies, story construction, evidence and the career narrative. Answer out loud before expanding.",
        "frameworks": "../01-java/README.md",
    },
    "14-coding": {
        "subtitle": "Patterns in Java, complexity, concurrency exercises and design-and-implement. Answer out loud before expanding.",
        "frameworks": "../01-java/README.md",
    },
    "15-mock-interviews": {
        "subtitle": "How a loop is run and scored, every round type, recovery, stories and negotiation. Answer out loud before expanding.",
        "frameworks": "../01-java/README.md",
    },
}

DEFAULT_SUBTITLE = "Answer out loud before expanding."
DEFAULT_FRAMEWORKS = "README.md"


# --------------------------------------------------------------------------
# Minimal markdown rendering, covering only the constructs used in these packs.
# --------------------------------------------------------------------------

CODE_SPAN = re.compile(r"`([^`]+)`")
LINK = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")
BOLD = re.compile(r"\*\*([^*]+)\*\*")
ITALIC = re.compile(r"(?<![\w*])\*([^*\n]+)\*(?![\w*])")


def render_inline(text):
    spans = []

    def stash(match):
        spans.append(html.escape(match.group(1)))
        return f"\x00{len(spans) - 1}\x00"

    text = CODE_SPAN.sub(stash, text)
    text = html.escape(text)
    text = LINK.sub(lambda m: f'<a href="{html.escape(m.group(2))}">{m.group(1)}</a>', text)
    text = BOLD.sub(r"<strong>\1</strong>", text)
    text = ITALIC.sub(r"<em>\1</em>", text)
    return re.sub(r"\x00(\d+)\x00", lambda m: f"<code>{spans[int(m.group(1))]}</code>", text)


def render_markdown(lines):
    out = []
    i = 0
    n = len(lines)

    while i < n:
        line = lines[i]
        stripped = line.strip()

        if not stripped:
            i += 1
            continue

        if stripped.startswith("```"):
            lang = stripped[3:].strip()
            i += 1
            body = []
            while i < n and not lines[i].strip().startswith("```"):
                body.append(lines[i])
                i += 1
            i += 1
            cls = f' class="lang-{html.escape(lang)}"' if lang else ""
            out.append(f"<pre><code{cls}>{html.escape(chr(10).join(body))}</code></pre>")
            continue

        heading = re.match(r"^(#{2,6})\s+(.*)$", stripped)
        if heading:
            level = min(len(heading.group(1)) + 1, 6)
            out.append(f"<h{level}>{render_inline(heading.group(2))}</h{level}>")
            i += 1
            continue

        if stripped.startswith("|") and i + 1 < n and re.match(r"^\|[\s:|-]+\|$", lines[i + 1].strip()):
            def cells(row):
                return [c.strip() for c in row.strip().strip("|").split("|")]

            header = cells(lines[i])
            i += 2
            rows = []
            while i < n and lines[i].strip().startswith("|"):
                rows.append(cells(lines[i]))
                i += 1
            head = "".join(f"<th>{render_inline(c)}</th>" for c in header)
            body = "".join(
                "<tr>" + "".join(f"<td>{render_inline(c)}</td>" for c in r) + "</tr>" for r in rows
            )
            out.append(f"<table><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table>")
            continue

        if stripped.startswith("> "):
            quote = []
            while i < n and lines[i].strip().startswith(">"):
                quote.append(lines[i].strip().lstrip(">").strip())
                i += 1
            out.append(f"<blockquote>{render_markdown(quote)}</blockquote>")
            continue

        bullet = re.match(r"^[-*]\s+(.*)$", stripped)
        ordered = re.match(r"^\d+\.\s+(.*)$", stripped)
        if bullet or ordered:
            tag = "ol" if ordered else "ul"
            pattern = r"^\d+\.\s+(.*)$" if ordered else r"^[-*]\s+(.*)$"
            items = []
            while i < n:
                match = re.match(pattern, lines[i].strip())
                if not match:
                    if lines[i].strip() and lines[i].startswith("  ") and items:
                        items[-1].append(lines[i].strip())
                        i += 1
                        continue
                    break
                items.append([match.group(1)])
                i += 1
            rendered = "".join(f"<li>{render_inline(' '.join(item))}</li>" for item in items)
            out.append(f"<{tag}>{rendered}</{tag}>")
            continue

        paragraph = []
        while i < n and lines[i].strip() and not re.match(r"^([-*]\s|\d+\.\s|>|\||#{2,6}\s|```)", lines[i].strip()):
            paragraph.append(lines[i].strip())
            i += 1
        if paragraph:
            out.append(f"<p>{render_inline(' '.join(paragraph))}</p>")
        else:
            i += 1

    return "".join(out)


def plain_text(markdown):
    text = re.sub(r"`+", "", markdown)
    text = LINK.sub(r"\1", text)
    text = re.sub(r"[*#>|]", " ", text)
    return re.sub(r"\s+", " ", text).strip()


# --------------------------------------------------------------------------
# Parsing
# --------------------------------------------------------------------------


def parse_questions(path):
    categories = []
    questions = []
    current = None

    for raw in path.read_text(encoding="utf-8").splitlines():
        section = re.match(r"^##\s+(\d+)\.\s+(.*)$", raw.strip())
        if section:
            current = {"index": int(section.group(1)), "title": section.group(2).strip()}
            categories.append(current)
            continue

        item = re.match(r"^(\d+)\.\s+(.*)$", raw.strip())
        if item and current:
            number = int(item.group(1))
            text = item.group(2).strip()
            difficulty = None
            tag = re.match(r"^`\[([CDTA])\]`\s*(.*)$", text)
            if tag:
                difficulty = tag.group(1)
                text = tag.group(2).strip()
            questions.append(
                {
                    "n": number,
                    "category": current["index"],
                    "difficulty": difficulty,
                    "html": render_inline(text),
                    "plain": plain_text(text),
                }
            )

    return categories, questions


def parse_blocks(path, heading_pattern):
    """Split a markdown file into blocks keyed by the heading pattern's first group."""
    blocks = {}
    lines = path.read_text(encoding="utf-8").splitlines()
    key = None
    title = None
    body = []

    def flush():
        if key is not None:
            blocks[key] = {"title": title, "body": list(body)}

    for raw in lines:
        stripped = raw.strip()
        match = re.match(heading_pattern, stripped)
        if match:
            flush()
            key = match.group(1)
            title = re.sub(r"\s*`\[[CDTA]\]`\s*$", "", match.group(2)).strip()
            body = []
            continue
        if key is not None:
            if stripped.startswith("## ") or re.fullmatch(r"-{3,}", stripped):
                flush()
                key = None
                body = []
                continue
            body.append(raw)

    flush()
    return blocks


def pack_title(readme):
    """The page title is the pack README's H1."""
    if readme.exists():
        for raw in readme.read_text(encoding="utf-8").splitlines():
            heading = re.match(r"^#\s+(.*)$", raw.strip())
            if heading:
                return heading.group(1).strip()
    return "Interview Questions"


def build(pack_dir):
    questions_path = pack_dir / "questions.md"
    answers_path = pack_dir / "answers.md"
    scenarios_path = pack_dir / "scenario-questions.md"
    output = pack_dir / "quiz.html"

    key = pack_dir.relative_to(ROOT).as_posix()
    config = PACKS.get(key, {})
    title = pack_title(pack_dir / "README.md")
    subtitle = config.get("subtitle", DEFAULT_SUBTITLE)
    frameworks = config.get("frameworks", DEFAULT_FRAMEWORKS)
    store_key = config.get("store", f"interview-progress-{pack_dir.name}-v1")

    categories, questions = parse_questions(questions_path)
    answers = parse_blocks(answers_path, r"^###\s+Q(\d+)\.\s+(.*)$")
    scenarios = parse_blocks(scenarios_path, r"^###\s+(S\d+)\.\s+(.*)$")

    # Scenario headings carry their originating question number, e.g. "... (Q221)".
    scenario_by_question = {}
    for key, block in scenarios.items():
        ref = re.search(r"\(Q(\d+)\)", block["title"])
        if ref:
            scenario_by_question[ref.group(1)] = (key, block)

    leadership_note = (
        "<p>No model answer is scripted for this one on purpose - it must be your own story. "
        "Use the <strong>STAR-L</strong> structure (Situation, Task, Action, Result, "
        "<strong>Learning</strong>), keep it to two or three minutes, and always quantify the "
        "Result.</p>"
        "<p>Worked examples of this style of question are in "
        '<a href="scenario-questions.md">scenario-questions.md</a>, Part C, and the frameworks '
        f'plus the stories to prepare are in <a href="{html.escape(frameworks)}">the README</a>.</p>'
    )

    for question in questions:
        key = str(question["n"])
        if key in answers:
            block = answers[key]
            question["answerTitle"] = block["title"]
            question["answer"] = render_markdown(block["body"])
            question["source"] = "answers.md"
            question["plainAnswer"] = plain_text("\n".join(block["body"]))
        elif key in scenario_by_question:
            scenario_key, block = scenario_by_question[key]
            question["answerTitle"] = re.sub(r"\s*\(Q\d+\)\s*$", "", block["title"])
            question["answer"] = render_markdown(block["body"])
            question["source"] = f"scenario-questions.md ({scenario_key})"
            question["plainAnswer"] = plain_text("\n".join(block["body"]))
        else:
            question["answerTitle"] = "Your own story"
            question["answer"] = leadership_note
            question["source"] = None
            question["plainAnswer"] = ""

        question["search"] = f"{question['plain']} {question['plainAnswer']}".lower()
        del question["plain"]
        del question["plainAnswer"]

    data = {
        "categories": categories,
        "questions": questions,
        "difficulty": {k: v[0] for k, v in DIFFICULTY.items()},
        "difficultyHint": {k: v[1] for k, v in DIFFICULTY.items()},
    }

    payload = json.dumps(data, ensure_ascii=False).replace("</", "<\\/")
    page = (
        TEMPLATE.replace("__TITLE__", html.escape(title))
        .replace("__SUBTITLE__", html.escape(subtitle))
        .replace("__STORE__", store_key)
        .replace("__DATA__", payload)
    )
    output.write_text(page, encoding="utf-8")

    scripted = sum(1 for q in questions if q["source"])
    print(f"Wrote {output.relative_to(ROOT)}")
    print(f"  {len(questions)} questions across {len(categories)} categories")
    print(f"  {scripted} with a scripted answer, {len(questions) - scripted} story-based")
    missing = [q["n"] for q in questions if not q["source"]]
    if missing:
        print(f"  story-based question numbers: {missing[0]}-{missing[-1]}")


def is_pack(path):
    return path.is_dir() and (path / "questions.md").exists() and (path / "answers.md").exists()


def discover_packs():
    """Top-level pack directories plus any nested sub-packs one level below them."""
    packs = []
    for top in ROOT.iterdir():
        if not top.is_dir() or top.name.startswith("."):
            continue
        if is_pack(top):
            packs.append(top)
        packs.extend(child for child in top.iterdir() if is_pack(child))
    return sorted(packs)


def main():
    targets = [ROOT / name for name in sys.argv[1:]] or discover_packs()
    if not targets:
        sys.exit("No packs found. Pass a pack directory, e.g. python tools/build-quiz.py 01-java")
    for target in targets:
        if not (target / "questions.md").exists():
            sys.exit(f"Not a pack directory: {target}")
        build(target)


TEMPLATE = r"""<!DOCTYPE html>
<html lang="en" data-theme="dark">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>__TITLE__</title>
<style>
:root {
  --bg: #0f1117; --panel: #171a23; --panel-2: #1e2230; --border: #2a3040;
  --text: #e6e9f0; --muted: #99a1b3; --accent: #6ea8fe; --accent-soft: #1b2740;
  --code-bg: #11141c; --shadow: 0 1px 3px rgba(0,0,0,.4);
  --c: #4ade80; --d: #6ea8fe; --t: #fbbf24; --a: #c084fc;
}
[data-theme="light"] {
  --bg: #f6f7f9; --panel: #ffffff; --panel-2: #f0f2f6; --border: #dde1e8;
  --text: #1a1d24; --muted: #5c6577; --accent: #1f5fd0; --accent-soft: #e6eefc;
  --code-bg: #f0f2f6; --shadow: 0 1px 3px rgba(16,24,40,.08);
  --c: #15803d; --d: #1f5fd0; --t: #b45309; --a: #7e22ce;
}
* { box-sizing: border-box; }
html { scroll-behavior: smooth; }
body {
  margin: 0; background: var(--bg); color: var(--text);
  font: 15px/1.65 -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
  -webkit-font-smoothing: antialiased;
}
.wrap { max-width: 980px; margin: 0 auto; padding: 0 20px 80px; }

header.top { padding: 40px 0 24px; }
header.top h1 { margin: 0 0 6px; font-size: 28px; letter-spacing: -.02em; }
header.top p { margin: 0; color: var(--muted); }
.legend { display: flex; flex-wrap: wrap; gap: 8px; margin-top: 18px; }

.toolbar {
  position: sticky; top: 0; z-index: 20; background: var(--bg);
  padding: 12px 0; border-bottom: 1px solid var(--border); margin-bottom: 20px;
}
.row { display: flex; flex-wrap: wrap; gap: 8px; align-items: center; }
.row + .row { margin-top: 8px; }
input[type="search"], select {
  background: var(--panel); color: var(--text); border: 1px solid var(--border);
  border-radius: 8px; padding: 9px 12px; font: inherit; font-size: 14px;
}
input[type="search"] { flex: 1 1 260px; }
input[type="search"]:focus, select:focus { outline: 2px solid var(--accent); outline-offset: 1px; }
button {
  background: var(--panel); color: var(--text); border: 1px solid var(--border);
  border-radius: 8px; padding: 8px 12px; font: inherit; font-size: 13px; cursor: pointer;
}
button:hover { border-color: var(--accent); }
button.on { background: var(--accent-soft); border-color: var(--accent); color: var(--accent); }

.pill {
  display: inline-flex; align-items: center; gap: 6px; font-size: 11px; font-weight: 600;
  letter-spacing: .04em; text-transform: uppercase; padding: 3px 8px; border-radius: 999px;
  border: 1px solid currentColor;
}
.pill.C { color: var(--c); } .pill.D { color: var(--d); }
.pill.T { color: var(--t); } .pill.A { color: var(--a); }

.progress { margin: 4px 0 0; }
.bar { height: 6px; border-radius: 999px; background: var(--panel-2); overflow: hidden; display: flex; }
.bar i { display: block; height: 100%; }
.bar .known { background: var(--c); } .bar .review { background: var(--t); }
.stats { color: var(--muted); font-size: 13px; margin-top: 8px; }
.stats b { color: var(--text); font-weight: 600; }

h2.cat {
  margin: 36px 0 14px; font-size: 13px; text-transform: uppercase; letter-spacing: .08em;
  color: var(--muted); border-bottom: 1px solid var(--border); padding-bottom: 8px;
}

article.q {
  background: var(--panel); border: 1px solid var(--border); border-radius: 12px;
  padding: 16px 18px; margin-bottom: 10px; box-shadow: var(--shadow); scroll-margin-top: 130px;
}
article.q[data-status="known"] { border-left: 3px solid var(--c); }
article.q[data-status="review"] { border-left: 3px solid var(--t); }
.q-head { display: flex; gap: 10px; align-items: baseline; flex-wrap: wrap; }
.q-num {
  font-variant-numeric: tabular-nums; font-weight: 700; font-size: 13px;
  color: var(--muted); text-decoration: none;
}
.q-num:hover { color: var(--accent); }
.q-text { margin: 8px 0 0; font-size: 15.5px; font-weight: 500; width: 100%; }
.q-actions { display: flex; gap: 6px; margin-top: 12px; flex-wrap: wrap; align-items: center; }
.q-actions .src { margin-left: auto; color: var(--muted); font-size: 12px; }

details.ans { margin-top: 12px; }
details.ans > summary {
  cursor: pointer; list-style: none; user-select: none;
  color: var(--accent); font-size: 13px; font-weight: 600;
  padding: 8px 12px; border: 1px solid var(--border); border-radius: 8px;
  background: var(--panel-2); display: inline-flex; align-items: center; gap: 8px;
}
details.ans > summary::-webkit-details-marker { display: none; }
details.ans > summary::before { content: "▸"; font-size: 11px; }
details.ans[open] > summary::before { content: "▾"; }
details.ans[open] > summary { border-bottom-left-radius: 0; border-bottom-right-radius: 0; }
.ans-body {
  border: 1px solid var(--border); border-top: none; border-radius: 0 8px 8px 8px;
  padding: 4px 18px 16px; background: var(--panel-2);
}
.ans-title { color: var(--muted); font-size: 12px; text-transform: uppercase; letter-spacing: .06em; margin: 14px 0 0; }

.md p { margin: 12px 0; }
.md ul, .md ol { margin: 12px 0; padding-left: 22px; }
.md li { margin: 6px 0; }
.md h3, .md h4, .md h5 { margin: 18px 0 8px; font-size: 15px; }
.md code {
  background: var(--code-bg); border: 1px solid var(--border); border-radius: 4px;
  padding: 1px 5px; font-size: 12.5px;
  font-family: ui-monospace, SFMono-Regular, "SF Mono", Menlo, Consolas, monospace;
}
.md pre {
  background: var(--code-bg); border: 1px solid var(--border); border-radius: 8px;
  padding: 14px 16px; overflow-x: auto; margin: 14px 0;
}
.md pre code { background: none; border: none; padding: 0; font-size: 12.5px; line-height: 1.6; }
.md blockquote {
  margin: 14px 0; padding: 2px 16px; border-left: 3px solid var(--t);
  background: color-mix(in srgb, var(--t) 8%, transparent); border-radius: 0 8px 8px 0;
}
.md blockquote p { margin: 10px 0; }
.md table { border-collapse: collapse; width: 100%; margin: 14px 0; font-size: 14px; display: block; overflow-x: auto; }
.md th, .md td { border: 1px solid var(--border); padding: 7px 10px; text-align: left; }
.md th { background: var(--panel); font-size: 12px; text-transform: uppercase; letter-spacing: .04em; }
.md a { color: var(--accent); }
.tok-kw { color: var(--a); } .tok-str { color: var(--c); }
.tok-com { color: var(--muted); font-style: italic; } .tok-ann { color: var(--t); }

.empty { text-align: center; color: var(--muted); padding: 60px 20px; }
mark { background: color-mix(in srgb, var(--t) 35%, transparent); color: inherit; border-radius: 3px; padding: 0 2px; }

@media print {
  .toolbar, .q-actions, .legend { display: none; }
  details.ans[open] > summary { display: none; }
  body { background: #fff; color: #000; }
}
@media (max-width: 640px) {
  .q-actions .src { margin-left: 0; width: 100%; }
}
</style>
</head>
<body>
<div class="wrap">

<header class="top">
  <h1>__TITLE__</h1>
  <p>__SUBTITLE__</p>
  <div class="legend" id="legend"></div>
</header>

<div class="toolbar">
  <div class="row">
    <input type="search" id="search" placeholder="Search questions and answers    ( / to focus )" autocomplete="off">
    <select id="category"><option value="">All categories</option></select>
    <select id="status">
      <option value="">Any status</option>
      <option value="unseen">Not marked</option>
      <option value="review">Needs review</option>
      <option value="known">Known</option>
    </select>
  </div>
  <div class="row">
    <span id="diffFilters"></span>
    <button id="expandAll">Expand all</button>
    <button id="collapseAll">Collapse all</button>
    <button id="theme">Light</button>
    <button id="reset">Reset progress</button>
  </div>
  <div class="row progress">
    <div class="bar" style="flex:1"><i class="known" id="barKnown"></i><i class="review" id="barReview"></i></div>
  </div>
  <div class="stats" id="stats"></div>
</div>

<main id="list"></main>
<div class="empty" id="empty" hidden>No questions match those filters.</div>

</div>

<script id="data" type="application/json">__DATA__</script>
<script>
(function () {
  "use strict";

  var DATA = JSON.parse(document.getElementById("data").textContent);
  var STORE = "__STORE__";
  var THEME_KEY = "interview-quiz-theme";
  var progress = {};
  try { progress = JSON.parse(localStorage.getItem(STORE)) || {}; } catch (e) { progress = {}; }

  var list = document.getElementById("list");
  var empty = document.getElementById("empty");
  var searchBox = document.getElementById("search");
  var categoryBox = document.getElementById("category");
  var statusBox = document.getElementById("status");
  var activeDifficulty = new Set();

  var catTitle = {};
  DATA.categories.forEach(function (c) {
    catTitle[c.index] = c.index + ". " + c.title;
    var opt = document.createElement("option");
    opt.value = c.index;
    opt.textContent = catTitle[c.index];
    categoryBox.appendChild(opt);
  });

  var legend = document.getElementById("legend");
  var diffFilters = document.getElementById("diffFilters");
  Object.keys(DATA.difficulty).forEach(function (key) {
    var span = document.createElement("span");
    span.className = "pill " + key;
    span.textContent = DATA.difficulty[key];
    span.title = DATA.difficultyHint[key];
    legend.appendChild(span);

    var btn = document.createElement("button");
    btn.textContent = DATA.difficulty[key];
    btn.dataset.diff = key;
    btn.addEventListener("click", function () {
      if (activeDifficulty.has(key)) { activeDifficulty.delete(key); btn.classList.remove("on"); }
      else { activeDifficulty.add(key); btn.classList.add("on"); }
      render();
    });
    diffFilters.appendChild(btn);
  });

  var KEYWORDS = /\b(abstract|assert|boolean|break|byte|case|catch|char|class|const|continue|default|do|double|else|enum|extends|final|finally|float|for|if|implements|import|instanceof|int|interface|long|native|new|package|private|protected|public|record|return|sealed|short|static|super|switch|synchronized|this|throw|throws|transient|try|var|void|volatile|while|yield|true|false|null)\b/g;

  function highlight(root) {
    root.querySelectorAll("pre code").forEach(function (block) {
      var text = block.textContent;
      var slots = [];
      function keep(cls) {
        return function (m) { slots.push('<span class="' + cls + '">' + esc(m) + "</span>"); return "\u0000" + (slots.length - 1) + "\u0000"; };
      }
      text = text.replace(/\/\/[^\n]*|\/\*[\s\S]*?\*\//g, keep("tok-com"));
      text = text.replace(/"(?:\\.|[^"\\])*"/g, keep("tok-str"));
      text = text.replace(/@\w+/g, keep("tok-ann"));
      text = esc(text).replace(KEYWORDS, '<span class="tok-kw">$&</span>');
      block.innerHTML = text.replace(/\u0000(\d+)\u0000/g, function (_, i) { return slots[+i]; });
    });
  }

  function esc(s) {
    return s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
  }

  function markHits(root, term) {
    if (!term) return;
    var rx = new RegExp("(" + term.replace(/[.*+?^${}()|[\]\\]/g, "\\$&") + ")", "gi");
    var walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT);
    var nodes = [];
    while (walker.nextNode()) {
      if (walker.currentNode.nodeValue.trim() && rx.test(walker.currentNode.nodeValue)) nodes.push(walker.currentNode);
      rx.lastIndex = 0;
    }
    nodes.forEach(function (node) {
      var span = document.createElement("span");
      span.innerHTML = esc(node.nodeValue).replace(rx, "<mark>$1</mark>");
      node.parentNode.replaceChild(span, node);
    });
  }

  function statusOf(n) { return progress[n] || "unseen"; }

  function setStatus(n, value) {
    if (statusOf(n) === value) delete progress[n]; else progress[n] = value;
    try { localStorage.setItem(STORE, JSON.stringify(progress)); } catch (e) {}
    render();
  }

  function card(q, term) {
    var el = document.createElement("article");
    el.className = "q";
    el.id = "q" + q.n;
    el.dataset.status = statusOf(q.n);

    var head = document.createElement("div");
    head.className = "q-head";
    head.innerHTML =
      '<a class="q-num" href="#q' + q.n + '">Q' + q.n + "</a>" +
      (q.difficulty ? '<span class="pill ' + q.difficulty + '" title="' + DATA.difficultyHint[q.difficulty] + '">' + DATA.difficulty[q.difficulty] + "</span>" : "") +
      '<h3 class="q-text">' + q.html + "</h3>";
    el.appendChild(head);

    var actions = document.createElement("div");
    actions.className = "q-actions";
    [["known", "Known"], ["review", "Review"]].forEach(function (pair) {
      var b = document.createElement("button");
      b.textContent = pair[1];
      if (statusOf(q.n) === pair[0]) b.classList.add("on");
      b.addEventListener("click", function () { setStatus(q.n, pair[0]); });
      actions.appendChild(b);
    });
    if (q.source) {
      var src = document.createElement("span");
      src.className = "src";
      src.textContent = q.source;
      actions.appendChild(src);
    }
    el.appendChild(actions);

    var details = document.createElement("details");
    details.className = "ans";
    var summary = document.createElement("summary");
    summary.textContent = q.source ? "Show answer" : "How to answer this";
    details.appendChild(summary);

    var body = document.createElement("div");
    body.className = "ans-body";
    body.innerHTML = '<p class="ans-title">' + esc(q.answerTitle) + '</p><div class="md">' + q.answer + "</div>";
    details.appendChild(body);
    el.appendChild(details);

    var rendered = false;
    details.addEventListener("toggle", function () {
      if (details.open && !rendered) { rendered = true; highlight(body); markHits(body, term); }
    });

    return el;
  }

  function render() {
    var term = searchBox.value.trim().toLowerCase();
    var cat = categoryBox.value;
    var status = statusBox.value;

    var matches = DATA.questions.filter(function (q) {
      if (term && q.search.indexOf(term) === -1) return false;
      if (cat && String(q.category) !== cat) return false;
      if (activeDifficulty.size && !activeDifficulty.has(q.difficulty)) return false;
      if (status && statusOf(q.n) !== status) return false;
      return true;
    });

    list.textContent = "";
    var lastCategory = null;
    matches.forEach(function (q) {
      if (q.category !== lastCategory) {
        lastCategory = q.category;
        var h = document.createElement("h2");
        h.className = "cat";
        h.textContent = catTitle[q.category];
        list.appendChild(h);
      }
      list.appendChild(card(q, term));
    });

    empty.hidden = matches.length > 0;

    var total = DATA.questions.length;
    var known = 0, review = 0;
    DATA.questions.forEach(function (q) {
      if (statusOf(q.n) === "known") known++;
      else if (statusOf(q.n) === "review") review++;
    });
    document.getElementById("barKnown").style.width = (known / total * 100) + "%";
    document.getElementById("barReview").style.width = (review / total * 100) + "%";
    document.getElementById("stats").innerHTML =
      "<b>" + matches.length + "</b> shown of " + total + " &nbsp;·&nbsp; " +
      "<b>" + known + "</b> known &nbsp;·&nbsp; <b>" + review + "</b> to review &nbsp;·&nbsp; " +
      "<b>" + (total - known - review) + "</b> not marked";
  }

  searchBox.addEventListener("input", render);
  categoryBox.addEventListener("change", render);
  statusBox.addEventListener("change", render);

  document.getElementById("expandAll").addEventListener("click", function () {
    list.querySelectorAll("details.ans").forEach(function (d) { d.open = true; });
  });
  document.getElementById("collapseAll").addEventListener("click", function () {
    list.querySelectorAll("details.ans").forEach(function (d) { d.open = false; });
  });
  document.getElementById("reset").addEventListener("click", function () {
    if (!confirm("Clear all Known / Review marks?")) return;
    progress = {};
    try { localStorage.removeItem(STORE); } catch (e) {}
    render();
  });

  var themeBtn = document.getElementById("theme");
  var savedTheme = null;
  try { savedTheme = localStorage.getItem(THEME_KEY); } catch (e) {}
  function applyTheme(t) {
    document.documentElement.dataset.theme = t;
    themeBtn.textContent = t === "dark" ? "Light" : "Dark";
    try { localStorage.setItem(THEME_KEY, t); } catch (e) {}
  }
  applyTheme(savedTheme || "dark");
  themeBtn.addEventListener("click", function () {
    applyTheme(document.documentElement.dataset.theme === "dark" ? "light" : "dark");
  });

  document.addEventListener("keydown", function (e) {
    if (e.key === "/" && document.activeElement !== searchBox) { e.preventDefault(); searchBox.focus(); }
    if (e.key === "Escape" && document.activeElement === searchBox) { searchBox.value = ""; render(); searchBox.blur(); }
  });

  render();

  if (location.hash) {
    var target = document.querySelector(location.hash);
    if (target) { target.scrollIntoView(); var d = target.querySelector("details.ans"); if (d) d.open = true; }
  }
})();
</script>
</body>
</html>
"""


if __name__ == "__main__":
    main()
