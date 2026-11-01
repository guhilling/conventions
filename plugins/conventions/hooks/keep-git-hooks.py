#!/usr/bin/env python3
"""
A Claude Code PreToolUse hook that refuses Bash commands switching off this repository's git hooks.

The guard against pushing to main is `.githooks/pre-push`, which git runs with the exact refs it
is about to push. A command can only get past it by skipping or disabling the hooks, so that is
all this checks: `--no-verify` on a push, any mention of `core.hooksPath`, and removing, moving,
writing over or changing the permissions of `.githooks`. It matches text instead of parsing the
shell on purpose. Exit status 2 blocks the call and shows Claude the reason.

Claude's own Write and Edit can write over a hook too (#470). Since a hook is changed that way in
a pull request, those are not refused but put to Gunnar, who confirms each one.
"""

import json
import re
import sys

CHECKS = [
    (re.compile(r"--no-verify"), re.compile(r"\bpush\b")),
    (re.compile(r"hookspath", re.IGNORECASE), None),
    (re.compile(r"\b(?:rm|mv|unlink|truncate|ln)\b[^\n;&|]*\.githooks|>\|?\s*\S*\.githooks",
                re.IGNORECASE), None),
    # Making a hook executable is how one is installed; any other mode change can disable it.
    (re.compile(r"\bchmod\b(?![^\n;&|]*\+x)[^\n;&|]*\.githooks"), None),
    # Writing over a hook (#470): copied or installed onto, as the last word before a redirection,
    # a comment or the command's end, or as -t's directory; teed into, before any `<`; edited in
    # place; or dd's output. Copying one away, or reading it, is fine. In any case, since macOS's
    # file system does not tell them apart.
    (re.compile(r"\b(?:cp|install)\b[^\n;&|]*\s\S*\.githooks\S*\s*(?=\d*[<>]|#|[\n;&|]|$)"
                r"|\b(?:cp|install)\b[^\n;&|]*\s(?:-t\s*|--target-directory[\s=])\S*\.githooks",
                re.IGNORECASE), None),
    (re.compile(r"\btee\b[^\n;&|<]*\.githooks", re.IGNORECASE), None),
    (re.compile(r"\b(?:sed|perl)\b[^\n;&|]*\s(?:-\w*i|--in-place)[^\n;&|]*\.githooks",
                re.IGNORECASE), None),
    (re.compile(r"\bdd\b[^\n;&|]*\bof=\S*\.githooks", re.IGNORECASE), None),
]


def disables_git_hooks(command):
    """Whether `command` would skip or switch off the hooks in `.githooks`."""
    return any(pattern.search(command) and (also is None or also.search(command))
               for pattern, also in CHECKS)


def writes_a_git_hook(path):
    """Whether a file tool's `path` is one in `.githooks`."""
    # In any case: macOS's file system does not tell them apart.
    return re.search(r"(?:^|/)\.githooks/", path, re.IGNORECASE) is not None


def main():
    call = json.load(sys.stdin)
    tool_input = call.get("tool_input", {})
    if call.get("tool_name", "Bash") != "Bash":
        # Write, Edit and the others: a hook is changed this way in a pull request, so Gunnar is
        # asked rather than the write refused (#470).
        if writes_a_git_hook(tool_input.get("file_path") or tool_input.get("notebook_path") or ""):
            reason = ("This writes a git hook in .githooks, which keeps pushes away from main: "
                      "Gunnar confirms each change.")
            print(json.dumps({"hookSpecificOutput": {"hookEventName": "PreToolUse",
                                                     "permissionDecision": "ask",
                                                     "permissionDecisionReason": reason}}))
        return 0
    command = tool_input.get("command", "")
    if disables_git_hooks(command):
        print("This command would skip or disable the git hooks in .githooks, which keep pushes "
              "away from main (the repository's CLAUDE.md). Push a branch and open a pull request "
              "instead; if the hooks themselves need changing, edit them in a pull request.",
              file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
