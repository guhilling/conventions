#!/usr/bin/env python3
"""
A Claude Code PreToolUse hook that refuses Bash commands switching off this repository's git hooks.

The guard against pushing to main is `.githooks/pre-push`, which git runs with the exact refs it
is about to push. A command can only get past it by skipping or disabling the hooks, so that is
all this checks: `--no-verify` on a push, any mention of `core.hooksPath`, and removing, moving
or changing the permissions of `.githooks`. It matches text instead of parsing the shell on
purpose. Exit status 2 blocks the call and shows Claude the reason.
"""

import json
import re
import sys

CHECKS = [
    (re.compile(r"--no-verify"), re.compile(r"\bpush\b")),
    (re.compile(r"hookspath", re.IGNORECASE), None),
    (re.compile(r"\b(?:rm|mv|unlink|truncate|ln)\b[^\n;&|]*\.githooks|>\s*\S*\.githooks"), None),
    # Making a hook executable is how one is installed; any other mode change can disable it.
    (re.compile(r"\bchmod\b(?![^\n;&|]*\+x)[^\n;&|]*\.githooks"), None),
]


def disables_git_hooks(command):
    """Whether `command` would skip or switch off the hooks in `.githooks`."""
    return any(pattern.search(command) and (also is None or also.search(command))
               for pattern, also in CHECKS)


def main():
    command = json.load(sys.stdin).get("tool_input", {}).get("command", "")
    if disables_git_hooks(command):
        print("This command would skip or disable the git hooks in .githooks, which keep pushes "
              "away from main (CLAUDE.md, Workflow). Push a branch and open a pull request "
              "instead; if the hooks themselves need changing, edit them in a pull request.",
              file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
