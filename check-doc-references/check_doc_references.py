#!/usr/bin/env python3
"""
Fails when a file in the repository names a documentation page that does not exist.

Run it anywhere inside the repository to check; the action in this directory does that in CI:

    python3 check_doc_references.py [--exclude doc/api/ ...]

A site build catches a dead link between pages. What it cannot see is everything else that
points into `doc/`: a Javadoc saying "see doc/decisions/index.md", an OpenTofu comment, a
CLAUDE.md, a workflow. Those are prose, not links, so nothing resolves them, and when
ai-assisted-todolist split its long documents into chapters 47 of them had to move at once. This
makes a missed one a failed build instead of a reader's dead end.

A reference is `doc/<path>.md`, or `doc/<chapter>/` for a chapter as a whole. `--exclude` leaves a
directory alone, such as one of generated files rather than documentation. Only files git tracks
are read, so build output and node_modules cannot contribute.
"""

import argparse
import pathlib
import re
import subprocess
import sys

# Preceded by nothing that would make it part of a longer path (`site/doc/...`), then either a
# .md file (not .mdx) or a chapter directory with its trailing slash.
REFERENCE = re.compile(r"(?<![\w./-])(doc/(?:[\w-]+/)*(?:[\w-]+\.md(?!\w)|[\w-]+/(?![\w.-])))")


def references(text, exclude=()):
    """Every documentation path a text names, in order, except those under an excluded prefix."""
    return [ref for ref in REFERENCE.findall(text) if not ref.startswith(tuple(exclude))]


def dead(found, exists):
    """The references among `found` whose target does not exist, according to `exists`."""
    return [ref for ref in found if not exists(ref.rstrip("/"))]


def repository_root():
    listing = subprocess.run(["git", "rev-parse", "--show-toplevel"],
                             capture_output=True, text=True, check=True)
    return pathlib.Path(listing.stdout.strip())


def tracked_files(root):
    listing = subprocess.run(["git", "-C", str(root), "ls-files"],
                             capture_output=True, text=True, check=True)
    return [root / name for name in listing.stdout.splitlines()]


def main(argv=None):
    parser = argparse.ArgumentParser(description="Fail on a reference to a doc/ page that does not exist.")
    parser.add_argument("--exclude", action="append", default=[], metavar="PREFIX",
                        help="leave references starting with PREFIX alone, e.g. doc/api/")
    args = parser.parse_args(argv)

    root = repository_root()
    exists = lambda ref: (root / ref).exists()
    problems = []
    for path in tracked_files(root):
        try:
            text = path.read_text()
        except (UnicodeDecodeError, OSError):
            continue
        for number, line in enumerate(text.splitlines(), 1):
            for ref in dead(references(line, args.exclude), exists):
                problems.append(f"{path.relative_to(root)}:{number}: {ref}")

    if problems:
        print("These name documentation that does not exist:\n", file=sys.stderr)
        print("\n".join(f"  {p}" for p in problems), file=sys.stderr)
        print("\nPoint them at the page the text is about.", file=sys.stderr)
        return 1
    print("every reference to doc/ names a page that exists")
    return 0


if __name__ == "__main__":
    sys.exit(main())
