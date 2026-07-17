#!/usr/bin/env python3
"""Backfill the discovery digests against the current (expanded) topic set.

Re-runs the paper-discovery classification for every calendar day in a date
range and overwrites each ``discovery/YYYY-MM-DD.md``. Unlike the daily skill
run, this operates **per-day with no dedup**: each digest covers exactly its own
date (``Window: D -> D``) and is classified independently, with no cross-day or
cross-run deduplication.

Classification mirrors ``.claude/skills/paper-discovery/SKILL.md`` Steps 2-6:
a paper is a candidate for a topic only if it passes **both** the BM25 keyword
pass (table parsed out of SKILL.md) and the semantic pass
(``semantic_classify.classify``), and is placed in the single topic with the
highest semantic score.

Usage:
    source researchEnv/bin/activate
    python scripts/backfill_discovery.py                 # full default range
    python scripts/backfill_discovery.py --start 2026-06-01 --end 2026-06-25
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
import urllib.error
import urllib.request
from datetime import date, timedelta
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SKILL_DIR = REPO_ROOT / ".claude" / "skills" / "paper-discovery"
SKILL_MD = SKILL_DIR / "SKILL.md"
DISCOVERY_DIR = REPO_ROOT / "discovery"

DEFAULT_START = date(2026, 5, 11)
DEFAULT_END = date(2026, 6, 25)

API_URL = "https://huggingface.co/api/daily_papers?date={d}&limit=100&sort=publishedAt"
FETCH_TIMEOUT = 10  # seconds, per RELIABILITY.md
FETCH_RETRIES = 3
SEMANTIC_THRESHOLD = 0.50

# Import the bundled semantic classifier (loads all-MiniLM-L6-v2 once per call).
sys.path.insert(0, str(SKILL_DIR))
from semantic_classify import classify  # type: ignore[import-not-found]  # noqa: E402


def parse_bm25_table(skill_md: Path) -> dict[str, list[str]]:
    """Parse the ``| Topic | Keywords |`` table out of SKILL.md.

    Keywords are backtick-wrapped, comma-separated. Returns
    {topic_name: [keyword, ...]} keyed by canonical (parent) topic name.
    """
    text = skill_md.read_text(encoding="utf-8")
    table: dict[str, list[str]] = {}
    for line in text.splitlines():
        line = line.strip()
        if not line.startswith("|"):
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        if len(cells) != 2:
            continue
        topic, keywords = cells
        if topic == "Topic" or set(topic) <= {"-"}:  # header / separator rows
            continue
        kws = re.findall(r"`([^`]+)`", keywords)
        if kws:
            table[topic] = [k.lower() for k in kws]
    if not table:
        raise RuntimeError(f"No BM25 keyword rows parsed from {skill_md}")
    return table


def fetch_papers(d: date) -> list[dict]:
    """Fetch the HuggingFace daily-papers list for a single date.

    Dedups within the date by ``paper.id`` (first occurrence wins). Returns an
    empty list for days with no papers. Fails loudly only after exhausting
    retries on a real network error.
    """
    url = API_URL.format(d=d.isoformat())
    last_err: Exception | None = None
    for attempt in range(FETCH_RETRIES):
        try:
            with urllib.request.urlopen(url, timeout=FETCH_TIMEOUT) as resp:
                raw = json.loads(resp.read().decode("utf-8"))
            break
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as err:
            last_err = err
            time.sleep(2 * (attempt + 1))
    else:
        raise RuntimeError(f"Failed to fetch {url}: {last_err}")

    seen: set[str] = set()
    papers: list[dict] = []
    for item in raw:
        paper = item.get("paper", {})
        pid = paper.get("id")
        if not pid or pid in seen:
            continue
        seen.add(pid)
        blurb = (paper.get("ai_summary") or item.get("summary") or "").strip()
        papers.append(
            {
                "id": pid,
                "title": (item.get("title") or paper.get("title") or "").strip(),
                "summary": (item.get("summary") or paper.get("summary") or "").strip(),
                "blurb": blurb,
                "published": (item.get("publishedAt") or paper.get("publishedAt") or "")[:10],
                "upvotes": int(paper.get("upvotes") or 0),
            }
        )
    return papers


def bm25_topics(paper: dict, bm25: dict[str, list[str]]) -> set[str]:
    """Topics whose keywords appear in the paper's title+summary (case-insensitive)."""
    haystack = f"{paper['title']} {paper['summary']}".lower()
    return {topic for topic, kws in bm25.items() if any(kw in haystack for kw in kws)}


def truncate_sentences(text: str, n: int = 2) -> str:
    """Keep the first ``n`` sentences of a blurb."""
    if not text:
        return ""
    parts = re.split(r"(?<=[.!?])\s+", text.strip())
    return " ".join(parts[:n]).strip()


def assign_topics(
    papers: list[dict],
    bm25: dict[str, list[str]],
    semantic: dict[str, dict[str, float]],
) -> tuple[dict[str, list[tuple[dict, float]]], list[dict]]:
    """Both-pass merge + best-fit assignment for one date's papers.

    Returns (sections, passed_over) where sections maps topic -> list of
    (paper, score) sorted by score desc, and each paper lands in at most one
    topic (highest semantic score among its both-pass candidates).
    """
    sections: dict[str, list[tuple[dict, float]]] = {}
    passed_over: list[dict] = []
    for paper in papers:
        sem = semantic.get(paper["id"], {})
        candidates = bm25_topics(paper, bm25) & set(sem)
        if not candidates:
            passed_over.append(paper)
            continue
        best = max(candidates, key=lambda t: sem[t])
        sections.setdefault(best, []).append((paper, sem[best]))
    for entries in sections.values():
        entries.sort(key=lambda e: e[1], reverse=True)
    return sections, passed_over


def build_digest(
    d: date,
    candidates: int,
    sections: dict[str, list[tuple[dict, float]]],
    passed_over: list[dict],
) -> str:
    iso = d.isoformat()
    matched = sum(len(v) for v in sections.values())
    lines: list[str] = [
        f"# Paper Discovery — {iso}",
        f"> **Fetched:** {iso} · **Window:** {iso} → {iso}",
        (
            f"> **Candidates:** {candidates} total · **Prior duplicates skipped:** 0 · "
            f"**Passed over:** {len(passed_over)} · **Matched:** {matched} across {len(sections)} topics"
        ),
        "",
    ]
    if matched == 0:
        lines.append("> No papers matched today's topics.")
        lines.append("")
    else:
        # Topic sections sorted by their top match score descending.
        for topic in sorted(sections, key=lambda t: sections[t][0][1], reverse=True):
            entries = sections[topic]
            lines.append(f"## {topic} ({len(entries)})")
            lines.append("")
            for paper, score in entries:
                lines.append(f"### {paper['title']}")
                lines.append(
                    f"**arXiv:** [{paper['id']}](https://arxiv.org/abs/{paper['id']}) | "
                    f"**Match:** {score:.2f} | **▲ Upvotes:** {paper['upvotes']} | "
                    f"**Published:** {paper['published']}"
                )
                blurb = truncate_sentences(paper["blurb"])
                if blurb:
                    lines.append(f"> {blurb}")
                lines.append("")

    if passed_over:
        lines.append(f"## Passed Over ({len(passed_over)})")
        for paper in passed_over:
            link = f"[{paper['title']}](https://arxiv.org/abs/{paper['id']})"
            blurb = truncate_sentences(paper["blurb"], n=1)
            lines.append(f"- {link} — {blurb}" if blurb else f"- {link}")
        lines.append("")

    lines.append("---")
    lines.append("*Generated by paper-discovery skill · [HuggingFace Daily Papers](https://huggingface.co/papers)*")
    return "\n".join(lines) + "\n"


def daterange(start: date, end: date):
    cur = start
    while cur <= end:
        yield cur
        cur += timedelta(days=1)


def main() -> None:
    parser = argparse.ArgumentParser(description="Backfill discovery digests against current topics")
    parser.add_argument("--start", type=date.fromisoformat, default=DEFAULT_START)
    parser.add_argument("--end", type=date.fromisoformat, default=DEFAULT_END)
    parser.add_argument("--threshold", type=float, default=SEMANTIC_THRESHOLD)
    args = parser.parse_args()

    bm25 = parse_bm25_table(SKILL_MD)
    print(f"Parsed {len(bm25)} BM25 topic rows.", file=sys.stderr)

    # 1. Fetch every date.
    dates = list(daterange(args.start, args.end))
    per_date: dict[date, list[dict]] = {}
    for d in dates:
        papers = fetch_papers(d)
        per_date[d] = papers
        print(f"  {d}: {len(papers)} papers", file=sys.stderr)
        time.sleep(0.5)  # polite pacing

    # 2. Semantic classify the union of unique papers in ONE call (model loads once).
    union: dict[str, dict] = {}
    for papers in per_date.values():
        for p in papers:
            union.setdefault(p["id"], {"id": p["id"], "title": p["title"], "abstract": p["summary"]})
    print(f"Semantic-classifying {len(union)} unique papers…", file=sys.stderr)
    semantic = classify(list(union.values()), threshold=args.threshold) if union else {}

    # 3. Build + write each date's digest.
    DISCOVERY_DIR.mkdir(exist_ok=True)
    for d in dates:
        papers = per_date[d]
        sections, passed_over = assign_topics(papers, bm25, semantic)
        digest = build_digest(d, len(papers), sections, passed_over)
        out = DISCOVERY_DIR / f"{d.isoformat()}.md"
        out.write_text(digest, encoding="utf-8")
        matched = sum(len(v) for v in sections.values())
        print(f"  wrote {out.name}: {matched} matched / {len(passed_over)} passed over", file=sys.stderr)

    print(f"Done. {len(dates)} digests written to {DISCOVERY_DIR}.", file=sys.stderr)


if __name__ == "__main__":
    main()
