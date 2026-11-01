#!/usr/bin/env python3
"""
A Claude Code PreToolUse hook that refuses Bash commands changing the AWS infrastructure.

Gunnar runs every `tofu apply` himself; Claude may plan, validate and read state, nothing more
(hilling-it-website: CLAUDE.md, #6). This refuses OpenTofu or Terraform, directly or through
deployment/aws-tofu/tofu.sh, with a subcommand that changes infrastructure or its state. It matches
text, not the shell's grammar, on purpose. Exit status 2 blocks the call and shows Claude why.

TaskFest's `env.sh up`, `down` and `account` apply too, each after showing its plan. Those are not
refused but put to Gunnar, who confirms each one (his decision on ai-assisted-todolist#470).

Text that git or gh only stores -- a commit message, a pull request's title or body, a
here-document fed to them -- is left out first, so mentioning a change in one is no false alarm.
Only text the shell cannot run is: single quotes, double quotes without `$` or a backtick, and a
here-document whose delimiter is quoted. Anything else is still read, and may still be refused.
"""

import json
import re
import shlex
import sys

# `test` creates and destroys real resources; `refresh`, the workspace and migration commands
# write state.
CHANGING = (r"apply|destroy|import|taint|untaint|force-unlock|test|refresh"
            r"|-?-migrate-state|-?-force-copy"
            r"|state\s+(?:rm|mv|push|replace-provider)|workspace\s+(?:new|delete)"
            r"|workspace\s+select\b[^\n;&|]*-or-create")
# The tool, then anything on the same simple command, then a changing subcommand that is a word
# of its own, so `tofu plan -destroy` (a flag) stays a plan.
PATTERN = re.compile(r"\b(?:tofu|terraform|tofu\.sh)\b[^\n;&|]*?(?<![-\w])(?:" + CHANGING + r")\b")


# env.sh's commands that apply, after its options (`-y`, `--yes`).
LIFECYCLE = re.compile(r"\benv\.sh(?:\s+-[-\w]+)*\s+(?:up|down|account)\b")

# The options whose value git or gh only stores: a message, a title, a body, notes.
MESSAGE_OPTIONS = ("-m", "--message", "--title", "--body", "--notes")
MESSAGE_ASSIGNED = tuple(option + "=" for option in MESSAGE_OPTIONS)
# What ends a command or redirects, to the shell; a newline ends one too.
OPERATORS = ";&|()<>\n"
# The start of a line that is git's or gh's alone, after at most a `cd … &&`.
_GIT_OR_GH = r"""^\s*(?:cd\s+[^\s;&|$`]+\s*&&\s*)?(?:git|gh)\s[^\n;&|$`<]*\s"""
# A here-document git or gh read as a message: the option that reads standard input, then the
# here-document, its delimiter quoted so that the shell expands nothing, and nothing after it.
STORED_HEREDOC = re.compile(_GIT_OR_GH + r"""(?:-F|--file|--body-file|--notes-file)[\s=]-\s*"""
                            r"""<<-?\s*(['"])(\w+)\1\s*$""")
# The same as a message option's value: `-m "$(cat <<'EOF'`.
STORED_CAT = re.compile(_GIT_OR_GH + r"""(?:-m|--message|--title|--body|--notes)[\s=]"""
                        r""""\$\(cat\s+<<-?\s*(['"])(\w+)\1\s*$""")


def _without_stored_heredocs(command):
    """`command`'s lines without the here-documents git or gh store; continued lines joined."""
    kept, delimiter = [], None
    for line in command.split("\n"):
        if delimiter is not None:
            # In a here-document a trailing backslash is a character, not a continuation.
            if line.strip() == delimiter:
                delimiter = None
            continue
        stored = STORED_HEREDOC.search(line) or STORED_CAT.search(line)
        # git runs a shell from an alias given with -c.
        if stored and not re.search(r"\s-c[\s=]", line):
            delimiter = stored.group(2)
        kept.append(line)
    # A line continued with a backslash is one command to the shell, and one line here.
    return "\n".join(kept).replace("\\\n", " ")


def _stores(word):
    """Whether `word` is a value the shell expands nothing in: no `$`, no backtick."""
    return "$" not in word and "`" not in word


def runnable(command):
    """
    `command` as words, without the text only git or gh read: the here-documents above, and each
    message option's value on a command that is git's or gh's. The words are the shell's, quotes
    taken off, so a quoted subcommand is still one; a command it cannot split is read as it is.
    """
    text = _without_stored_heredocs(command)
    lexer = shlex.shlex(text, posix=True, punctuation_chars=OPERATORS)
    # A newline ends a command, and `#` is a comment only at a word's start, which shlex ignores.
    lexer.whitespace, lexer.commenters, lexer.whitespace_split = " \t", "", True
    try:
        words = list(lexer)
    except ValueError:
        return text
    kept, simple = [], []
    for word in words:
        if word and all(char in OPERATORS for char in word):
            kept.append(word)
            simple = []
            continue
        # The program is the first word that is not an assignment; git runs a shell from an
        # alias given with -c.
        program = next((each for each in simple if not re.fullmatch(r"\w+=.*", each)), None)
        stores = program in ("git", "gh") and "-c" not in simple
        previous = simple[-1] if simple else None
        simple.append(word)
        if stores and _stores(word) and (previous in MESSAGE_OPTIONS
                                         or word.startswith(MESSAGE_ASSIGNED)):
            continue
        kept.append(word)
    return " ".join(kept)


def changes_infrastructure(command):
    """Whether `command` would run OpenTofu or Terraform to change infrastructure or its state."""
    return PATTERN.search(runnable(command)) is not None


def lifecycle(command):
    """Whether `command` would run one of env.sh's applies, which Gunnar confirms."""
    return LIFECYCLE.search(runnable(command)) is not None


def main():
    command = json.load(sys.stdin).get("tool_input", {}).get("command", "")
    if changes_infrastructure(command):
        print("This command would change the AWS infrastructure or its state. Gunnar applies "
              "every change himself; Claude only plans (CLAUDE.md). Run `tofu plan` and show "
              "him the result instead.", file=sys.stderr)
        return 2
    if lifecycle(command):
        print(json.dumps({"hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "ask",
            "permissionDecisionReason": "env.sh up, down and account apply infrastructure: "
                                        "Gunnar confirms each one."}}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
