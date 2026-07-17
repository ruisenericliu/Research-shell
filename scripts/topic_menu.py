#!/usr/bin/env python3
"""Emit a compact topic-scope menu for pipeline classification.

Each `Library/<Topic>/MOC.md` opens with a title and a one-paragraph scope
description (per the library-filing convention). This script distills every
topic into a single `Topic — scope` line, so the pipeline orchestrator can pass
a small menu to each summary sub-agent for in-context classification instead of
having the (expensive) main agent read all ~26 MOC bodies to file each paper.

Usage:
    researchEnv/bin/python3 scripts/topic_menu.py [--max-chars 320]

Output is plain text, one topic per line, sorted by topic name.
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
LIBRARY_DIR = REPO_ROOT / "Library"
MOC_NAME = "MOC.md"


def scope_of(moc_path: Path) -> str:
    """First prose paragraph under the MOC's title (its scope description)."""
    lines = moc_path.read_text().splitlines()
    para: list[str] = []
    seen_title = False
    for raw in lines:
        line = raw.strip()
        if not seen_title:
            if line.startswith("#"):
                seen_title = True
            continue
        if not line:
            if para:  # end of the first paragraph
                break
            continue
        if line.startswith("#"):
            if para:
                break
            continue
        if line.startswith(("- ", "* ", ">", "|")):
            # hit curated concept links / tables before any prose
            if para:
                break
            continue
        para.append(line)
    text = " ".join(para)
    text = re.sub(r"\[\[([^\]|]+)(?:\|[^\]]+)?\]\]", r"\1", text)  # unwrap wikilinks
    return re.sub(r"\s+", " ", text).strip()


def build_menu(max_chars: int) -> list[str]:
    rows: list[str] = []
    for topic_dir in sorted(LIBRARY_DIR.iterdir()):
        moc = topic_dir / MOC_NAME
        if not topic_dir.is_dir() or not moc.exists():
            continue
        scope = scope_of(moc)
        if len(scope) > max_chars:
            scope = scope[: max_chars - 1].rstrip() + "…"
        rows.append(f"{topic_dir.name} — {scope}" if scope else topic_dir.name)
    return rows


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--max-chars", type=int, default=320)
    args = ap.parse_args()
    for row in build_menu(args.max_chars):
        print(row)


if __name__ == "__main__":
    main()
