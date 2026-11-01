"""
Pins down which shell commands keep-git-hooks.py refuses.

.githooks/pre-push is what stops a push to main; this hook only keeps Claude from switching it
off. It matches text rather than parsing the shell on purpose: a parser misses spellings, and a
false alarm here costs a reworded command, not a push to main.

Run with:  python3 -m unittest discover -s plugins/conventions/hooks -p 'test_*.py'
"""

import importlib.util
import pathlib
import unittest

_spec = importlib.util.spec_from_file_location(
    "keep_git_hooks", pathlib.Path(__file__).with_name("keep-git-hooks.py"))
hook = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(hook)


class RefusedTest(unittest.TestCase):

    def test_skipping_the_hooks_on_a_push(self):
        for command in ["git push --no-verify origin main",
                        "cd /repo\nGIT_TRACE=1 git push origin feature --no-verify"]:
            with self.subTest(command):
                self.assertTrue(hook.disables_git_hooks(command))

    def test_moving_or_removing_the_hooks(self):
        for command in ["git config core.hooksPath /dev/null",
                        "git -c core.hookspath=x push origin main",
                        "git config --unset core.hooksPath",
                        "rm .githooks/pre-push", "chmod -x .githooks/pre-push",
                        "mv .githooks hooks-off"]:
            with self.subTest(command):
                self.assertTrue(hook.disables_git_hooks(command))


class AllowedTest(unittest.TestCase):

    def test_ordinary_git_work(self):
        for command in ["git push -u origin conventions", "git commit --no-verify -m wip",
                        "cat .githooks/pre-push", "git log -- .githooks/pre-push",
                        "chmod +x .githooks/pre-push",
                        "npm test && git push"]:
            with self.subTest(command):
                self.assertFalse(hook.disables_git_hooks(command))


if __name__ == "__main__":
    unittest.main()
