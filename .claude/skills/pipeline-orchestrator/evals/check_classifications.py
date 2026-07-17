#!/usr/bin/env python3
"""Score a pipeline-orchestrator eval run's classifications against the golden set.

The load-bearing behavior of the redesigned pipeline is that each Sonnet summary
sub-agent *classifies* its paper (stamps `topic:` into the note frontmatter when
confident, leaves it unstamped when not). This script grades that decision — it
does **not** run the pipeline. A future agent runs the eval (see README.md),
pointing each classified note into a scratch run directory, then invokes this to
get a pass/fail scorecard.

It reads every `*.md` under `--run-dir`, parses each note's YAML frontmatter for
`arxiv_id` + `topic`, matches to the golden set by `arxiv_id`, and applies:

  - require_unsure case  → PASS iff no topic stamped (the confidence gate must
    fire on an out-of-scope paper); a stamped topic FAILS (gate leaked).
  - stamped a topic      → PASS iff topic ∈ expected_topics, else FAIL (wrong).
  - unstamped (UNSURE)   → PASS iff unsure_ok, else FAIL (gate too conservative).
  - note missing entirely → FAIL (sub-agent produced nothing).

Exit code is non-zero if any case fails, so it can gate CI / a drift check.

Usage:
    researchEnv/bin/python3 check_classifications.py --run-dir <dir> [--golden PATH] [--json]
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
DEFAULT_GOLDEN = HERE / "golden_set.jsonl"


def parse_frontmatter(md_path: Path) -> dict[str, str]:
    """Minimal YAML-frontmatter reader (no external dep): flat `key: value` pairs."""
    text = md_path.read_text(errors="ignore")
    if not text.startswith("---"):
        return {}
    lines = text.splitlines()
    fields: dict[str, str] = {}
    for line in lines[1:]:
        if line.strip() == "---":
            break
        if ":" not in line or line.startswith((" ", "\t", "#")):
            continue
        key, _, val = line.partition(":")
        fields[key.strip()] = val.strip().strip('"').strip("'")
    return fields


def load_golden(path: Path) -> list[dict]:
    cases = []
    for line in path.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            cases.append(json.loads(line))
    return cases


def index_run(run_dir: Path) -> dict[str, dict[str, str]]:
    """arxiv_id -> {topic, path} for every note under run_dir that has frontmatter."""
    found: dict[str, dict[str, str]] = {}
    for md in sorted(run_dir.rglob("*.md")):
        fm = parse_frontmatter(md)
        aid = fm.get("arxiv_id")
        if aid:
            found[aid] = {"topic": fm.get("topic", ""), "path": str(md)}
    return found


def grade(case: dict, note: dict[str, str] | None) -> tuple[bool, str]:
    name = case.get("name", case["arxiv_id"])
    if note is None:
        return False, f"{name}: no note produced for {case['arxiv_id']}"
    topic = note["topic"] or None
    if case.get("require_unsure"):
        if topic is None:
            return True, f"{name}: correctly UNSURE (out-of-scope gate fired)"
        return False, f"{name}: gate LEAKED — stamped '{topic}', expected UNSURE"
    if topic is not None:
        if topic in case["expected_topics"]:
            return True, f"{name}: correct topic '{topic}'"
        return (
            False,
            f"{name}: WRONG topic '{topic}' (expected one of {case['expected_topics']})",
        )
    # unstamped / UNSURE
    if case.get("unsure_ok"):
        return True, f"{name}: UNSURE (acceptable — conservative)"
    return False, f"{name}: UNSURE but a confident call was expected {case['expected_topics']}"


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--run-dir", type=Path, required=True, help="dir of classified eval notes")
    ap.add_argument("--golden", type=Path, default=DEFAULT_GOLDEN)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    if not args.run_dir.is_dir():
        raise SystemExit(f"run-dir not found: {args.run_dir}")

    golden = load_golden(args.golden)
    notes = index_run(args.run_dir)

    results = []
    passed = 0
    for case in golden:
        ok, msg = grade(case, notes.get(case["arxiv_id"]))
        passed += ok
        results.append({"arxiv_id": case["arxiv_id"], "pass": ok, "detail": msg})

    total = len(golden)
    if args.json:
        print(json.dumps({"passed": passed, "total": total, "results": results}, indent=2))
    else:
        for r in results:
            print(f"  [{'PASS' if r['pass'] else 'FAIL'}] {r['detail']}")
        print(f"\n{passed}/{total} classifications correct")
        if passed < total:
            print("REGRESSION: classification behavior drifted — inspect the FAILs above.")

    raise SystemExit(0 if passed == total else 1)


if __name__ == "__main__":
    main()
