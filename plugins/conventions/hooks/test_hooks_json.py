"""
Pins down that hooks.json can do what the plugin promises: the rules reach every session whole,
and every hook it names exists.

Claude Code adds a SessionStart hook's output to the context only up to 10,000 characters. Past
that it stores the text in a file and shows Claude the first 2,000, which would quietly drop most
of the rules. A path in hooks.json that does not exist fails only when a session starts, in the
repository that uses the plugin, not here.

Run with:  python3 -m unittest discover -s plugins/conventions/hooks -p 'test_*.py'
"""

import json
import pathlib
import unittest

PLUGIN_ROOT = pathlib.Path(__file__).resolve().parent.parent
HOOKS = json.loads((PLUGIN_ROOT / "hooks" / "hooks.json").read_text(encoding="utf-8"))["hooks"]
# Claude Code's cap on a hook's plain stdout and on additionalContext.
CONTEXT_LIMIT = 10_000


def commands(event):
    """Every command hook registered for `event`."""
    return [hook for group in HOOKS.get(event, []) for hook in group["hooks"]]


def files(hook):
    """The plugin files a hook's arguments name, as paths."""
    return [PLUGIN_ROOT / arg.removeprefix("${CLAUDE_PLUGIN_ROOT}/")
            for arg in hook.get("args", []) if arg.startswith("${CLAUDE_PLUGIN_ROOT}/")]


class SessionStartTest(unittest.TestCase):

    def test_prints_the_rules_on_every_kind_of_start(self):
        # No matcher: startup, resume, /clear and a compaction all get the rules again.
        groups = HOOKS["SessionStart"]
        self.assertEqual([None], [group.get("matcher") for group in groups])
        self.assertEqual([("cat", [PLUGIN_ROOT / "rules.md"])],
                         [(hook["command"], files(hook)) for hook in commands("SessionStart")])

    def test_the_rules_fit_into_the_context_whole(self):
        rules = (PLUGIN_ROOT / "rules.md").read_text(encoding="utf-8")
        self.assertLess(len(rules), CONTEXT_LIMIT)


class PreToolUseTest(unittest.TestCase):

    def test_every_guard_named_exists(self):
        guards = [path for hook in commands("PreToolUse") for path in files(hook)]
        self.assertEqual(["keep-git-hooks.py", "plan-only.py"], [path.name for path in guards])
        for path in guards:
            with self.subTest(path.name):
                self.assertTrue(path.is_file())

    def test_guards_watch_bash_only(self):
        self.assertEqual(["Bash"], [group["matcher"] for group in HOOKS["PreToolUse"]])


if __name__ == "__main__":
    unittest.main()
