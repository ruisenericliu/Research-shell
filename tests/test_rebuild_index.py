#!/usr/bin/env python3
"""Self-checking tests for rebuild_index (no pytest dependency).

Covers the README library-overview generation: the family/leftover/seeded
rendering logic and the marker-block writer that keeps README in sync with
the live per-topic counts. Run directly:

    source researchEnv/bin/activate
    python tests/test_rebuild_index.py
"""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import rebuild_index as ri  # noqa: E402


def _family_counts(value: int = 1) -> dict[str, int]:
    """Counts dict assigning ``value`` to every topic in every family."""
    counts: dict[str, int] = {}
    for _label, _desc, members in ri.README_FAMILIES:
        for member in members:
            counts[member] = value
    return counts


def test_render_overview_families() -> None:
    counts = _family_counts(2)
    out = ri.render_overview(counts)
    total = 2 * sum(len(m) for _, _, m in ri.README_FAMILIES)
    assert out.startswith(f"{total} papers across "), out.splitlines()[0]
    for label, desc, members in ri.README_FAMILIES:
        heading = f"**{label}**" + (f" — {desc}" if desc else "")
        assert heading in out, f"missing family heading: {heading}"
        for member in members:
            assert f"| `{member}` | 2 |" in out, member
    assert "Seeded but not yet populated" not in out, "spurious seeded line"
    assert "**Other topics**" not in out, "spurious other-topics section"
    print("ok  render_overview families + counts")


def test_render_overview_leftover_and_seeded() -> None:
    counts = _family_counts(1)
    counts["Brand New Topic"] = 3      # unassigned, has papers -> Other
    counts["Fresh Empty Topic"] = 0    # unassigned, empty -> seeded line
    counts["World Models"] = 0         # umbrella hub: neither row nor seeded
    out = ri.render_overview(counts)
    assert "**Other topics**" in out, out
    assert "| `Brand New Topic` | 3 |" in out, out
    assert "Seeded but not yet populated: `Fresh Empty Topic`." in out, out
    assert "| `World Models` |" not in out, "umbrella leaked as a row"
    assert "`World Models`," not in out, "umbrella leaked into seeded line"
    print("ok  render_overview leftover (Other) + seeded + umbrella excluded")


def test_render_overview_skips_absent_family() -> None:
    first_label, first_desc, first_members = ri.README_FAMILIES[0]
    counts = {m: 1 for m in first_members}
    out = ri.render_overview(counts)
    first_heading = f"**{first_label}**" + (
        f" — {first_desc}" if first_desc else ""
    )
    assert first_heading in out, "present family should render"
    for label, desc, _members in ri.README_FAMILIES[1:]:
        heading = f"**{label}**" + (f" — {desc}" if desc else "")
        assert heading not in out, f"empty family rendered: {heading}"
    print("ok  render_overview skips families with no present topics")


def test_update_readme_roundtrip(tmp: Path) -> None:
    readme = tmp / "README.md"
    readme.write_text(
        f"intro line\n\n{ri.README_BEGIN}\nOLD CONTENT\n{ri.README_END}\n\n"
        "outro line\n",
        encoding="utf-8",
    )
    ri.README_PATH = readme
    counts = _family_counts(1)

    assert ri.update_readme(counts, check=False) is True, "should be dirty"
    text = readme.read_text(encoding="utf-8")
    assert text.startswith("intro line\n"), "preamble clobbered"
    assert text.endswith("outro line\n"), "postamble clobbered"
    assert "OLD CONTENT" not in text, "stale block survived"
    assert ri.README_BEGIN in text and ri.README_END in text, "markers lost"

    # Second run with identical counts is a no-op (drift-free).
    assert ri.update_readme(counts, check=False) is False, "not idempotent"

    # --check on a stale file reports drift without writing.
    readme.write_text(
        f"intro line\n{ri.README_BEGIN}\nSTALE\n{ri.README_END}\noutro\n",
        encoding="utf-8",
    )
    assert ri.update_readme(counts, check=True) is True, "drift not reported"
    assert "STALE" in readme.read_text(encoding="utf-8"), "check mode wrote"
    print("ok  update_readme roundtrip (write/idempotent/check)")


def test_update_readme_missing_markers(tmp: Path) -> None:
    readme = tmp / "README.md"
    readme.write_text("no markers anywhere\n", encoding="utf-8")
    ri.README_PATH = readme
    assert ri.update_readme(_family_counts(1), check=False) is False
    assert readme.read_text(encoding="utf-8") == "no markers anywhere\n"

    ri.README_PATH = tmp / "does-not-exist.md"
    assert ri.update_readme(_family_counts(1), check=False) is False
    print("ok  update_readme tolerates missing markers / missing file")


def main() -> int:
    original_readme_path = ri.README_PATH
    try:
        test_render_overview_families()
        test_render_overview_leftover_and_seeded()
        test_render_overview_skips_absent_family()
        with tempfile.TemporaryDirectory() as d:
            test_update_readme_roundtrip(Path(d))
        with tempfile.TemporaryDirectory() as d:
            test_update_readme_missing_markers(Path(d))
    finally:
        ri.README_PATH = original_readme_path
    print("all tests passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
