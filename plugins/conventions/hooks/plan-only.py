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
import sys

# `test` creates and destroys real resources; `refresh`, the workspace and migration commands
# write state.
CHANGING = (r"apply|destroy|import|taint|untaint|force-unlock|test|refresh"
            r"|-migrate-state|-force-copy"
            r"|state\s+(?:rm|mv|push|replace-provider)|workspace\s+(?:new|delete)"
            r"|workspace\s+select\b[^\n;&|]*-or-create")
# The tool, then anything on the same simple command, then a changing subcommand that is a word
# of its own, so `tofu plan -destroy` (a flag) stays a plan.
PATTERN = re.compile(r"\b(?:tofu|terraform|tofu\.sh)\b[^\n;&|]*?(?<![-\w])(?:" + CHANGING + r")\b")


# env.sh's commands that apply, after its options (`-y`, `--yes`).
LIFECYCLE = re.compile(r"\benv\.sh(?:\s+-[-\w]+)*\s+(?:up|down|account)\b")

# A message, title, body or notes given to git or gh, quoted so that the shell expands nothing.
STORED_TEXT = re.compile(r"(?<![-\w])(?:-m|--message|--title|--body|--notes)(?:\s+|=)"
                         r"""(?:'[^']*'|"(?:[^"\\$`]|\\[^$`])*")""")
# A here-document with a quoted delimiter, on a line that hands it to git or gh.
STORED_HEREDOC = re.compile(r"""\b(?:git|gh)\b[^\n;&|]*<<-?\s*(['"])(\w+)\1""")


def runnable(command):
    """`command` without the text only git or gh read, its continued lines joined."""
    # A line continued with a backslash is one command to the shell, and one line here.
    lines = command.replace("\\\n", " ").split("\n")
    kept, delimiter = [], None
    for line in lines:
        if delimiter is not None:
            if line.strip() == delimiter:
                delimiter = None
            continue
        heredoc = STORED_HEREDOC.search(line)
        delimiter = heredoc.group(2) if heredoc else None
        kept.append(line)
    return STORED_TEXT.sub(" ", "\n".join(kept))


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
