#!/usr/bin/env python3
"""
A Claude Code PreToolUse hook that refuses Bash commands changing the AWS infrastructure.

Gunnar runs every `tofu apply` himself; Claude may plan, validate and read state, nothing more
(hilling-it-website: CLAUDE.md, #6). This refuses OpenTofu or Terraform, directly or through
deployment/aws-tofu/tofu.sh, with a subcommand that changes infrastructure or its state. It matches
text, not the shell's grammar, on purpose. Exit status 2 blocks the call and shows Claude why.
"""

import json
import re
import sys

# `test` creates and destroys real resources; `refresh`, the workspace and migration commands
# write state.
CHANGING = (r"apply|destroy|import|taint|untaint|force-unlock|test|refresh|-migrate-state"
            r"|state\s+(?:rm|mv|push|replace-provider)|workspace\s+(?:new|delete)")
# The tool, then anything on the same simple command, then a changing subcommand that is a word
# of its own, so `tofu plan -destroy` (a flag) stays a plan.
PATTERN = re.compile(r"\b(?:tofu|terraform|tofu\.sh)\b[^\n;&|]*?(?<![-\w])(?:" + CHANGING + r")\b")


def changes_infrastructure(command):
    """Whether `command` would run OpenTofu or Terraform to change infrastructure or its state."""
    # A line continued with a backslash is one command to the shell, and one line here.
    return PATTERN.search(command.replace("\\\n", " ")) is not None


def main():
    command = json.load(sys.stdin).get("tool_input", {}).get("command", "")
    if changes_infrastructure(command):
        print("This command would change the AWS infrastructure or its state. Gunnar applies "
              "every change himself; Claude only plans (CLAUDE.md). Run `tofu plan` and show "
              "him the result instead.", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
