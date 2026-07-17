#!/usr/bin/env python3
"""Semantic paper classifier using local sentence-transformers embeddings.

Reads each topic's MOC.md from Library/ as the topic specification, then
scores incoming papers by cosine similarity between the paper's title+abstract
embedding and the topic embedding.

Usage:
    echo '[{"id": "2605.01234", "title": "...", "abstract": "..."}]' \\
        | python scripts/semantic_classify.py

    # Tune threshold (default 0.40):
    ... | python scripts/semantic_classify.py --threshold 0.35

    # Limit to specific topics:
    ... | python scripts/semantic_classify.py --topics "Inference-Time Reasoning Algorithms" "Multi-Agent Coordination"

Output (stdout):
    {"2605.01234": {"Inference-Time Reasoning Algorithms": 0.87}, ...}

    Keys are topic names that exceeded the threshold; values are cosine similarity scores.
"""

import argparse
import json
import sys
from pathlib import Path

LIBRARY_DIR = Path(__file__).parent.parent.parent.parent / "Library"
MODEL_NAME = "all-MiniLM-L6-v2"
DEFAULT_THRESHOLD = 0.50

# Sub-topic folders are named "<Prefix> — <Child>" (space em-dash space). For
# discovery we classify at *parent* granularity — fine sub-topic placement is
# library-filing's job — so a sub-topic's MOC text is folded into its parent's
# semantic spec. PARENT_ALIASES maps a sub-topic prefix to the canonical parent
# (umbrella) topic name when the two differ (the VLA family folder is
# "Vision Language Action Models" but its children are prefixed "VLA").
SUBTOPIC_SEP = " — "
PARENT_ALIASES = {"VLA": "Vision Language Action Models"}


def _canonical_topic(folder_name: str, known_parents: set[str]) -> str:
    """Map a Library folder name to its canonical (parent) topic name.

    A sub-topic folder ("<Prefix> — <Child>") folds into its parent *only when
    that parent actually exists* as an umbrella folder (after PARENT_ALIASES
    resolution). A standalone topic whose name merely contains " — " (e.g.
    "3D Reconstruction — Feed-Forward", which has no "3D Reconstruction" umbrella)
    keeps its full name and stays its own topic. A non-sub-topic folder is its
    own topic.
    """
    if SUBTOPIC_SEP in folder_name:
        prefix = folder_name.split(SUBTOPIC_SEP, 1)[0]
        parent = PARENT_ALIASES.get(prefix, prefix)
        if parent in known_parents:
            return parent
    return folder_name


def load_topics(topic_names: list[str] | None = None) -> dict[str, str]:
    """Build {canonical_topic: combined_MOC_text}.

    Umbrella parents and their sub-topics are merged under one canonical name so
    the classifier emits scores at parent granularity while drawing on the richer
    sub-topic MOC content. Folding only happens toward a parent that exists as a
    real Library folder, so standalone em-dash topics are not lost to a phantom
    parent. Topics are kept in first-seen (sorted-folder) order.
    """
    topic_dirs = [
        d for d in sorted(LIBRARY_DIR.iterdir()) if d.is_dir() and (d / "MOC.md").exists()
    ]
    known_parents = {d.name for d in topic_dirs}
    topics: dict[str, list[str]] = {}
    for topic_dir in topic_dirs:
        canonical = _canonical_topic(topic_dir.name, known_parents)
        if topic_names and canonical not in topic_names:
            continue
        topics.setdefault(canonical, []).append((topic_dir / "MOC.md").read_text(encoding="utf-8"))
    return {name: "\n\n".join(parts) for name, parts in topics.items()}


def classify(
    papers: list[dict],
    threshold: float = DEFAULT_THRESHOLD,
    topic_names: list[str] | None = None,
) -> dict[str, dict[str, float]]:
    try:
        from sentence_transformers import SentenceTransformer
        from sentence_transformers.util import cos_sim
    except ImportError:
        print(
            "sentence-transformers not installed. Run:\n"
            "  source researchEnv/bin/activate && pip install sentence-transformers",
            file=sys.stderr,
        )
        sys.exit(1)

    topics = load_topics(topic_names)
    if not topics:
        print(f"No topics found in {LIBRARY_DIR}", file=sys.stderr)
        return {p["id"]: {} for p in papers}

    model = SentenceTransformer(MODEL_NAME)

    topic_names_ordered = list(topics.keys())
    topic_texts = list(topics.values())
    topic_embeddings = model.encode(topic_texts, convert_to_tensor=True, show_progress_bar=False)

    paper_texts = [f"{p['title']} {p.get('abstract', '')}" for p in papers]
    paper_embeddings = model.encode(paper_texts, convert_to_tensor=True, show_progress_bar=False)

    results: dict[str, dict[str, float]] = {}
    for i, paper in enumerate(papers):
        matched: dict[str, float] = {}
        for j, topic_name in enumerate(topic_names_ordered):
            sim = float(cos_sim(paper_embeddings[i], topic_embeddings[j]))
            if sim >= threshold:
                matched[topic_name] = round(sim, 3)
        results[paper["id"]] = matched

    return results


def main() -> None:
    parser = argparse.ArgumentParser(description="Semantic paper topic classifier")
    parser.add_argument(
        "--threshold",
        type=float,
        default=DEFAULT_THRESHOLD,
        help=f"Cosine similarity threshold (default: {DEFAULT_THRESHOLD})",
    )
    parser.add_argument(
        "--topics",
        nargs="*",
        metavar="TOPIC",
        help="Restrict classification to these topic names (default: all Library topics)",
    )
    args = parser.parse_args()

    papers = json.load(sys.stdin)
    results = classify(papers, threshold=args.threshold, topic_names=args.topics)
    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
