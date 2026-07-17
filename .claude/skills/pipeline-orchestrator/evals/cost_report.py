#!/usr/bin/env python3
"""Token-cost report for pipeline-orchestrator runs (efficiency benchmark / drift guard).

Reads Claude Code transcript JSONL for this project and aggregates token usage by
**model family** (opus / sonnet / haiku) and **thread** (main orchestrator vs. the
Sonnet summary sub-agents), applying a rough public rate table to produce a
comparable cost proxy — plus an optional per-paper figure.

Use it to A/B a skill change: measure a baseline run, edit the skill, measure the
new run over the same papers, and confirm the Opus main-thread cost per paper drops
(i.e. classification stayed on Sonnet and filing didn't slide back onto Opus).

Examples
--------
    # Whole recent window, per-paper over a 3-paper batch
    python3 cost_report.py --since 2026-07-06T18:00 --papers 3

    # One specific session transcript
    python3 cost_report.py --session 5ec6a88d-2d30-44c2-8b65-6ecfd4850543

    # Machine-readable, for capturing before/after numbers
    python3 cost_report.py --since <T0> --until <T1> --papers 3 --json

The cost proxy uses list-ish prices ($/Mtok) and treats cache-read at 0.1x input,
cache-creation at 1.25x input. It is directional, not a billing figure.
"""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

DEFAULT_PROJECT = (
    Path.home()
    / ".claude/projects/-Users-ruisenliu-Repositories-Research"
)

# $/Mtok, (input, output). cache_read billed ~0.1x input, cache_creation ~1.25x input.
RATES: dict[str, dict[str, float]] = {
    "opus": {"in": 15.0, "out": 75.0},
    "sonnet": {"in": 3.0, "out": 15.0},
    "haiku": {"in": 0.80, "out": 4.0},
}


def model_family(model: str | None) -> str:
    m = (model or "").lower()
    for fam in ("opus", "sonnet", "haiku"):
        if fam in m:
            return fam
    return "other"


def parse_ts(raw: str | None) -> datetime | None:
    if not raw:
        return None
    try:
        return datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        return None


def cost_of(family: str, tok: dict[str, float]) -> float:
    rate = RATES.get(family, RATES["sonnet"])
    return (
        tok["in"] * rate["in"]
        + tok["out"] * rate["out"]
        + tok["cache_creation"] * rate["in"] * 1.25
        + tok["cache_read"] * rate["in"] * 0.1
    ) / 1_000_000


def new_bucket() -> dict[str, float]:
    return {"in": 0.0, "out": 0.0, "cache_creation": 0.0, "cache_read": 0.0, "msgs": 0.0}


def aggregate(
    files: list[Path],
    since: datetime | None,
    until: datetime | None,
) -> dict[tuple[str, str], dict[str, float]]:
    buckets: dict[tuple[str, str], dict[str, float]] = defaultdict(new_bucket)
    # A single assistant *turn* is logged as one JSONL line per content block
    # (thinking + text + each tool_use), and every one of those lines carries the
    # SAME usage snapshot. Counting per line therefore multiplies a turn's cost by
    # its block count — worst for the parallel-tool-call turns this skill is built
    # around (e.g. 10 Agent spawns → counted 10x). Dedup by assistant message id so
    # each turn's usage is counted exactly once.
    seen_ids: set[str] = set()
    for path in files:
        try:
            lines = path.read_text().splitlines()
        except OSError:
            continue
        for line in lines:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                continue
            msg = obj.get("message") or {}
            if msg.get("role") != "assistant":
                continue
            usage = msg.get("usage") or {}
            if not usage:
                continue
            mid = msg.get("id")
            if mid is not None:
                if mid in seen_ids:
                    continue
                seen_ids.add(mid)
            ts = parse_ts(obj.get("timestamp"))
            if since and (ts is None or ts < since):
                continue
            if until and (ts is None or ts > until):
                continue
            fam = model_family(msg.get("model"))
            thread = "sub" if obj.get("isSidechain") else "main"
            b = buckets[(fam, thread)]
            b["in"] += usage.get("input_tokens", 0)
            b["out"] += usage.get("output_tokens", 0)
            b["cache_creation"] += usage.get("cache_creation_input_tokens", 0)
            b["cache_read"] += usage.get("cache_read_input_tokens", 0)
            b["msgs"] += 1
    return buckets


def report(buckets: dict[tuple[str, str], dict[str, float]], papers: int | None) -> dict:
    rows = []
    by_family: dict[str, float] = defaultdict(float)
    total = 0.0
    for (fam, thread), tok in sorted(buckets.items()):
        c = cost_of(fam, tok)
        total += c
        by_family[fam] += c
        rows.append(
            {
                "model": fam,
                "thread": thread,
                "msgs": int(tok["msgs"]),
                "in": tok["in"],
                "out": tok["out"],
                "cache_read": tok["cache_read"],
                "cost": c,
            }
        )
    result = {
        "rows": rows,
        "by_family": dict(by_family),
        "total_cost": total,
        "papers": papers,
        "cost_per_paper": (total / papers) if papers else None,
    }
    return result


def print_human(result: dict) -> None:
    print(
        f"{'model':8} {'thread':6} {'msgs':>6} {'in(M)':>8} {'out(M)':>8} "
        f"{'cacheRd(M)':>11} {'~$cost':>9}"
    )
    for r in result["rows"]:
        print(
            f"{r['model']:8} {r['thread']:6} {r['msgs']:>6} "
            f"{r['in'] / 1e6:>8.2f} {r['out'] / 1e6:>8.2f} "
            f"{r['cache_read'] / 1e6:>11.1f} {r['cost']:>9.2f}"
        )
    print("\n~cost proxy by model:")
    total = result["total_cost"] or 1.0
    for fam, c in sorted(result["by_family"].items(), key=lambda kv: -kv[1]):
        print(f"  {fam:8} ${c:8.2f}  ({100 * c / total:4.1f}%)")
    print(f"\nTOTAL ~${result['total_cost']:.2f}")
    if result["cost_per_paper"] is not None:
        print(f"PER PAPER ({result['papers']}) ~${result['cost_per_paper']:.3f}")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--project", type=Path, default=DEFAULT_PROJECT)
    ap.add_argument("--session", help="single transcript UUID (filename without .jsonl)")
    ap.add_argument("--since", help="ISO8601 lower bound on message timestamp")
    ap.add_argument("--until", help="ISO8601 upper bound on message timestamp")
    ap.add_argument("--papers", type=int, help="divide total cost by this many papers")
    ap.add_argument("--json", action="store_true", help="emit machine-readable JSON")
    args = ap.parse_args()

    def as_ts(raw: str | None) -> datetime | None:
        if not raw:
            return None
        dt = parse_ts(raw)
        if dt is None:
            raise SystemExit(f"bad timestamp: {raw!r}")
        return dt.astimezone(timezone.utc) if dt.tzinfo else dt.replace(tzinfo=timezone.utc)

    if args.session:
        files = [args.project / f"{args.session}.jsonl"]
    else:
        files = sorted(args.project.glob("*.jsonl"))
    if not files:
        raise SystemExit(f"no transcripts found under {args.project}")

    buckets = aggregate(files, as_ts(args.since), as_ts(args.until))
    result = report(buckets, args.papers)
    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print_human(result)


if __name__ == "__main__":
    main()
