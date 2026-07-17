#!/usr/bin/env python3
"""Local discovery review server.

Serves a single-page UI for triaging the *matched* papers across all
``discovery/*.md`` digests and records the user's selections to
``staging/selected-YYYY-MM-DD.md`` in the ``Title — https://arxiv.org/abs/ID``
format the ``pipeline-orchestrator`` skill ingests natively.

Runs entirely on localhost with the Python standard library (no web framework,
no new dependencies).

Usage:
    source researchEnv/bin/activate
    python scripts/review_server.py --port 8000
"""

from __future__ import annotations

import argparse
import json
import logging
import re
from collections.abc import Iterator
from dataclasses import asdict, dataclass
from datetime import date
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPT_DIR = Path(__file__).resolve().parent
DISCOVERY_DIR = REPO_ROOT / "discovery"
LIBRARY_DIR = REPO_ROOT / "Library"
STAGING_DIR = REPO_ROOT / "staging"
UI_HTML = SCRIPT_DIR / "review_ui.html"

HOST = "127.0.0.1"
DEFAULT_PORT = 8000

logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger("review_server")

# A bare arXiv id, e.g. "2606.24595" or "2606.24595v2".
ARXIV_ID_RE = re.compile(r"^\d{4}\.\d{4,6}(v\d+)?$")

# Digest line patterns (mirror backfill_discovery.build_digest output).
_DIGEST_NAME_RE = re.compile(r"^(\d{4}-\d{2}-\d{2})\.md$")
_TOPIC_RE = re.compile(r"^##\s+(.*?)\s+\(\d+\)\s*$")
_ARXIV_RE = re.compile(
    r"\*\*arXiv:\*\*\s+\[([^\]]+)\]\([^)]*\)"
    r"(?:\s+\|\s+\*\*Match:\*\*\s+([\d.]+))?"
    r"(?:\s+\|\s+\*\*▲ Upvotes:\*\*\s+(\d+))?"
    r"(?:\s+\|\s+\*\*Published:\*\*\s+([\d-]+))?"
)
# Header summary line: "**Candidates:** N ... **Passed over:** P ...
# **Matched:** M across T topics".
_STATS_RE = re.compile(
    r"\*\*Candidates:\*\*\s+(\d+).*?"
    r"\*\*Passed over:\*\*\s+(\d+).*?"
    r"\*\*Matched:\*\*\s+(\d+)"
)
# Passed-over bullet: "- [Title](https://arxiv.org/abs/ID) — blurb" (blurb
# and the em-dash separator are optional).
_PASSED_RE = re.compile(
    r"^- \[(?P<title>.+)\]\(https://arxiv\.org/abs/(?P<id>[^)]+)\)"
    r"(?:\s+—\s+(?P<blurb>.*))?$"
)


@dataclass
class Paper:
    """One matched paper parsed out of a digest."""

    date: str
    topic: str
    title: str
    arxiv_id: str
    match: float | None
    upvotes: int | None
    published: str
    blurb: str
    filed: bool = False
    selected: bool = False


def parse_digest(text: str, digest_date: str) -> list[Paper]:
    """Extract matched papers from one digest's markdown.

    Tracks the current ``## <Topic> (N)`` section and skips ``## Passed Over``
    (whose entries are titles-only with no arXiv id). Each ``### <Title>`` is
    paired with the following ``**arXiv:** ...`` metadata line and an optional
    ``> blurb``.
    """
    papers: list[Paper] = []
    topic: str | None = None
    title: str | None = None
    lines = text.splitlines()
    for i, raw in enumerate(lines):
        line = raw.rstrip()
        topic_match = _TOPIC_RE.match(line)
        if topic_match:
            name = topic_match.group(1)
            topic = None if name == "Passed Over" else name
            title = None
        elif line.startswith("### ") and topic is not None:
            title = line[4:].strip()
        elif line.startswith("**arXiv:**") and topic and title:
            meta = _ARXIV_RE.search(line)
            if meta:
                blurb = ""
                if i + 1 < len(lines):
                    nxt = lines[i + 1].lstrip()
                    if nxt.startswith(">"):
                        blurb = nxt[1:].strip()
                match = float(meta.group(2)) if meta.group(2) else None
                upvotes = int(meta.group(3)) if meta.group(3) else None
                papers.append(
                    Paper(
                        date=digest_date,
                        topic=topic,
                        title=title,
                        arxiv_id=meta.group(1),
                        match=match,
                        upvotes=upvotes,
                        published=meta.group(4) or "",
                        blurb=blurb,
                    )
                )
            title = None
    return papers


def parse_passed_over(text: str) -> list[dict]:
    """Papers in a digest's ``## Passed Over`` section.

    Current format is ``- [Title](url) — blurb``; older digests used bare
    ``- Title`` lines (no link/blurb). Both are parsed; missing fields come
    back as empty strings.
    """
    items: list[dict] = []
    in_section = False
    for line in text.splitlines():
        if line.startswith("## Passed Over"):
            in_section = True
            continue
        if in_section:
            if line.startswith("## ") or line.startswith("---"):
                break
            if not line.startswith("- "):
                continue
            match = _PASSED_RE.match(line)
            if match:
                items.append(
                    {
                        "title": match.group("title").strip(),
                        "arxiv_id": match.group("id").strip(),
                        "blurb": (match.group("blurb") or "").strip(),
                    }
                )
            else:  # legacy bare-title line
                items.append(
                    {"title": line[2:].strip(), "arxiv_id": "", "blurb": ""}
                )
    return items


def parse_header_stats(text: str) -> tuple[int, int, int]:
    """(candidates, passed_over, matched) from a digest's summary header."""
    match = _STATS_RE.search(text)
    if not match:
        return (0, 0, 0)
    return (int(match.group(1)), int(match.group(2)), int(match.group(3)))


def iter_digests() -> Iterator[tuple[str, str]]:
    """Yield (date, text) for each ``discovery/YYYY-MM-DD.md``, newest first."""
    for digest in sorted(DISCOVERY_DIR.glob("*.md"), reverse=True):
        name = _DIGEST_NAME_RE.match(digest.name)
        if name:
            yield name.group(1), digest.read_text(encoding="utf-8")


def load_filed_ids() -> set[str]:
    """arXiv ids already filed in any ``Library/*/index.json``."""
    ids: set[str] = set()
    for index in LIBRARY_DIR.glob("*/index.json"):
        try:
            data = json.loads(index.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as err:
            logger.warning("skipping %s: %s", index, err)
            continue
        if not isinstance(data, list):
            continue
        for entry in data:
            if isinstance(entry, dict) and entry.get("arxiv_id"):
                ids.add(str(entry["arxiv_id"]))
    return ids


# --- Library browsing ---------------------------------------------------

# Umbrella-hub sub-topic bullet: "- [[Child Topic]] — description".
_SUBTOPIC_RE = re.compile(r"^-\s+\[\[([^\]]+)\]\]")


def load_library() -> list[dict]:
    """Every filed paper across ``Library/*/index.json``, newest first.

    Each entry carries the metadata stored in the index plus a ``topic`` field
    set to its folder name. Umbrella hubs (empty ``index.json``) contribute
    nothing. Mirrors the tolerant load in :func:`load_filed_ids`.
    """
    papers: list[dict] = []
    for index in LIBRARY_DIR.glob("*/index.json"):
        topic = index.parent.name
        try:
            data = json.loads(index.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as err:
            logger.warning("skipping %s: %s", index, err)
            continue
        if not isinstance(data, list):
            continue
        for entry in data:
            if not isinstance(entry, dict):
                continue
            papers.append(
                {
                    "topic": topic,
                    "arxiv_id": str(entry.get("arxiv_id", "")),
                    "name": str(entry.get("name", "")),
                    "title": str(entry.get("title", "")),
                    "path": str(entry.get("path", "")),
                    "submitted": str(entry.get("submitted", "")),
                    "blurb": str(entry.get("blurb", "")),
                }
            )
    papers.sort(key=lambda p: p["submitted"], reverse=True)
    return papers


def read_moc_scope(topic: str) -> str:
    """First prose paragraph of a topic's ``MOC.md`` (its scope blurb).

    The MOC opens with ``# Title`` then a blank line then a scope paragraph;
    this returns that paragraph (joined to one line), or ``""`` when the file
    or paragraph is missing.
    """
    moc = LIBRARY_DIR / topic / "MOC.md"
    try:
        text = moc.read_text(encoding="utf-8")
    except OSError:
        return ""
    paragraph: list[str] = []
    seen_title = False
    for raw in text.splitlines():
        line = raw.strip()
        if not seen_title:
            if line.startswith("# "):
                seen_title = True
            continue
        if line.startswith("#"):  # hit next heading before any prose
            break
        if not line:
            if paragraph:  # blank line ends the first paragraph
                break
            continue
        paragraph.append(line)
    return " ".join(paragraph)


def parse_subtopics(topic: str) -> list[str]:
    """Child topic names from an umbrella MOC's ``## Sub-Topics`` section.

    Returns the ``[[wikilink]]`` targets (exact child folder names) in file
    order, or ``[]`` when the topic has no such section.
    """
    moc = LIBRARY_DIR / topic / "MOC.md"
    try:
        text = moc.read_text(encoding="utf-8")
    except OSError:
        return []
    children: list[str] = []
    in_section = False
    for raw in text.splitlines():
        line = raw.strip()
        if line.startswith("## "):
            in_section = line[3:].strip() == "Sub-Topics"
            continue
        if in_section:
            match = _SUBTOPIC_RE.match(line)
            if match:
                children.append(match.group(1).strip())
    return children


def build_taxonomy() -> list[dict]:
    """The Library topic tree: umbrella hubs with children, then standalones.

    A folder is an umbrella when it holds no papers of its own yet its MOC
    lists sub-topics; its ``count`` is the sum of its children's counts.
    Top-level nodes are sorted by count descending.
    """
    counts: dict[str, int] = {}
    for index in LIBRARY_DIR.glob("*/index.json"):
        try:
            data = json.loads(index.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as err:
            logger.warning("skipping %s: %s", index, err)
            continue
        counts[index.parent.name] = len(data) if isinstance(data, list) else 0

    umbrellas: dict[str, list[str]] = {}
    for topic, count in counts.items():
        if count == 0:
            children = [c for c in parse_subtopics(topic) if c in counts]
            if children:
                umbrellas[topic] = children

    claimed = {child for children in umbrellas.values() for child in children}
    nodes: list[dict] = []
    for topic, children in umbrellas.items():
        child_nodes = [
            {"name": c, "scope": read_moc_scope(c), "count": counts[c]}
            for c in children
        ]
        nodes.append(
            {
                "name": topic,
                "scope": read_moc_scope(topic),
                "is_umbrella": True,
                "count": sum(counts[c] for c in children),
                "children": child_nodes,
            }
        )
    for topic, count in counts.items():
        if topic in umbrellas or topic in claimed:
            continue
        nodes.append(
            {
                "name": topic,
                "scope": read_moc_scope(topic),
                "is_umbrella": False,
                "count": count,
                "children": [],
            }
        )
    nodes.sort(key=lambda n: n["count"], reverse=True)
    return nodes


def read_note(topic: str, path: str) -> str | None:
    """Body markdown of a filed note, or ``None`` if it is not a filed paper.

    The ``(topic, path)`` pair is validated against the set of entries in the
    Library indexes, so an arbitrary/relative ``path`` can never escape the
    Library (path-traversal defence). The leading YAML frontmatter block is
    stripped; the body already opens with a ``# Title`` header.
    """
    allowed = {(p["topic"], p["path"]) for p in load_library()}
    if (topic, path) not in allowed:
        return None
    note = LIBRARY_DIR / topic / path
    try:
        text = note.read_text(encoding="utf-8")
    except OSError:
        return None
    if text.startswith("---"):
        end = text.find("\n---", 3)
        if end != -1:
            nl = text.find("\n", end + 1)
            text = text[nl + 1 :] if nl != -1 else ""
    return text.lstrip("\n")


def selection_path(today: str) -> Path:
    """Path of today's selection file."""
    return STAGING_DIR / f"selected-{today}.md"


# Parses a stored line: "Title — https://arxiv.org/abs/ID". The title is
# greedy so a title that itself contains " — " is handled (the URL anchor
# is unambiguous).
_SELECTION_LINE_RE = re.compile(
    r"^(?P<title>.*) — https://arxiv\.org/abs/(?P<id>\S+)\s*$"
)


def read_selection_entries(today: str) -> list[dict]:
    """Selections in today's file as ``[{arxiv_id, title}]`` in file order."""
    path = selection_path(today)
    if not path.exists():
        return []
    entries: list[dict] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        match = _SELECTION_LINE_RE.match(line)
        if match:
            entries.append(
                {"arxiv_id": match.group("id"), "title": match.group("title")}
            )
    return entries


def write_selection_entries(today: str, entries: list[dict]) -> None:
    """Rewrite today's selection file (or delete it when empty)."""
    path = selection_path(today)
    if not entries:
        path.unlink(missing_ok=True)
        return
    STAGING_DIR.mkdir(exist_ok=True)
    lines = [f"# Selected from discovery review — {today}", ""]
    lines += [
        f"{e['title']} — https://arxiv.org/abs/{e['arxiv_id']}"
        for e in entries
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def selected_ids(today: str) -> set[str]:
    """arXiv ids currently in today's selection file."""
    return {e["arxiv_id"] for e in read_selection_entries(today)}


def add_selection(item: dict) -> list[dict]:
    """Append one paper to today's selections (deduped). Returns the list."""
    aid = str(item.get("arxiv_id", "")).strip()
    title = str(item.get("title", "")).strip()
    if not ARXIV_ID_RE.match(aid):
        raise ValueError(f"invalid arxiv id: {aid!r}")
    today = date.today().isoformat()
    entries = read_selection_entries(today)
    if aid not in {e["arxiv_id"] for e in entries}:
        entries.append({"arxiv_id": aid, "title": title})
        write_selection_entries(today, entries)
        logger.info("selected %s", aid)
    return entries


def remove_selection(aid: str) -> list[dict]:
    """Drop one paper from today's selections. Returns the remaining list."""
    today = date.today().isoformat()
    entries = [
        e for e in read_selection_entries(today) if e["arxiv_id"] != aid
    ]
    write_selection_entries(today, entries)
    logger.info("deselected %s", aid)
    return entries


def clear_selections() -> list[dict]:
    """Remove all of today's selections (deletes the file)."""
    write_selection_entries(date.today().isoformat(), [])
    logger.info("cleared selections")
    return []


def collect_papers() -> list[Paper]:
    """Parse every digest (newest date first) with filed/selected flags."""
    filed = load_filed_ids()
    selected = selected_ids(date.today().isoformat())
    papers: list[Paper] = []
    for digest_date, text in iter_digests():
        for paper in parse_digest(text, digest_date):
            paper.filed = paper.arxiv_id in filed
            paper.selected = paper.arxiv_id in selected
            papers.append(paper)
    return papers


def collect_passed_over() -> list[dict]:
    """All passed-over papers as ``[{date, title, arxiv_id, blurb}]``."""
    out: list[dict] = []
    for digest_date, text in iter_digests():
        for item in parse_passed_over(text):
            out.append({"date": digest_date, **item})
    return out


def compute_stats() -> dict:
    """Aggregate counts across all digests plus today's selection count."""
    candidates = passed = matched = days = 0
    for _digest_date, text in iter_digests():
        cand, pas, mat = parse_header_stats(text)
        candidates += cand
        passed += pas
        matched += mat
        days += 1
    selected = len(read_selection_entries(date.today().isoformat()))
    return {
        "candidates": candidates,
        "matched": matched,
        "passed_over": passed,
        "selected": selected,
        "days": days,
    }


class ReviewHandler(BaseHTTPRequestHandler):
    """Serves the UI and the papers/select JSON endpoints."""

    def _send_json(self, payload: dict, status: int = 200) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:  # noqa: N802 (http.server API)
        if self.path in ("/", "/index.html"):
            self._serve_ui(UI_HTML)
        elif self.path == "/api/papers":
            papers = collect_papers()
            topics = sorted({p.topic for p in papers})
            today = date.today().isoformat()
            self._send_json(
                {
                    "topics": topics,
                    "papers": [asdict(p) for p in papers],
                    "selected": read_selection_entries(today),
                    "stats": compute_stats(),
                }
            )
        elif self.path == "/api/passed":
            self._send_json(
                {"passed": collect_passed_over(), "stats": compute_stats()}
            )
        elif self.path == "/api/taxonomy":
            taxonomy = build_taxonomy()
            papers_total = sum(
                n["count"] for n in taxonomy if not n["is_umbrella"]
            ) + sum(
                c["count"]
                for n in taxonomy
                if n["is_umbrella"]
                for c in n["children"]
            )
            topics_total = sum(
                len(n["children"]) if n["is_umbrella"] else 1
                for n in taxonomy
            )
            self._send_json(
                {
                    "taxonomy": taxonomy,
                    "topics_total": topics_total,
                    "papers_total": papers_total,
                }
            )
        elif self.path == "/api/library":
            lib_papers = load_library()
            topics = sorted({p["topic"] for p in lib_papers})
            self._send_json({"papers": lib_papers, "topics": topics})
        elif urlparse(self.path).path == "/api/note":
            query = parse_qs(urlparse(self.path).query)
            topic = (query.get("topic") or [""])[0]
            path = (query.get("path") or [""])[0]
            body = read_note(topic, path)
            if body is None:
                self.send_error(404)
            else:
                self._send_json({"markdown": body})
        else:
            self.send_error(404)

    def _serve_ui(self, path: Path) -> None:
        try:
            body = path.read_bytes()
        except OSError:
            self.send_error(500, f"{path.name} missing")
            return
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _read_json(self) -> dict:
        length = int(self.headers.get("Content-Length") or 0)
        raw = self.rfile.read(length) if length else b""
        data = json.loads(raw.decode("utf-8"))
        if not isinstance(data, dict):
            raise ValueError("body must be a JSON object")
        return data

    def do_POST(self) -> None:  # noqa: N802 (http.server API)
        try:
            if self.path == "/api/select":
                entries = add_selection(self._read_json())
            elif self.path == "/api/deselect":
                aid = str(self._read_json().get("arxiv_id", ""))
                entries = remove_selection(aid)
            elif self.path == "/api/clear":
                entries = clear_selections()
            else:
                self.send_error(404)
                return
        except (json.JSONDecodeError, ValueError, UnicodeDecodeError) as err:
            logger.warning("bad POST body: %s", err)
            self._send_json({"error": "invalid request"}, status=400)
            return
        self._send_json({"selected": entries})

    def log_message(self, fmt: str, *args: object) -> None:
        logger.info("%s %s", self.address_string(), fmt % args)


def main() -> int:
    parser = argparse.ArgumentParser(description="Discovery review server")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    args = parser.parse_args()
    server = ThreadingHTTPServer((HOST, args.port), ReviewHandler)
    logger.info("Serving review UI at http://%s:%d", HOST, args.port)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        logger.info("shutting down")
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
