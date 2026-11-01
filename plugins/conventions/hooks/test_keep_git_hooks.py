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


class WrittenOverTest(unittest.TestCase):
    """Commands that write over a hook, which #470 found getting past the checks above."""

    def test_copying_teeing_or_editing_onto_the_hooks(self):
        for command in ["cp /dev/null .githooks/pre-push", "cp -f noop.sh ./.githooks/pre-push",
                        "install -m 755 noop .githooks/pre-push",
                        "echo exit 0 | tee .githooks/pre-push",
                        "tee -a .githooks/pre-push < /dev/null",
                        "sed -i '' 's/main/none/' .githooks/pre-push",
                        "sed -i.bak -e 1q .githooks/pre-push",
                        "perl -pi -e 's/x/y/' .githooks/pre-push",
                        "dd if=/dev/null of=.githooks/pre-push"]:
            with self.subTest(command):
                self.assertTrue(hook.disables_git_hooks(command))

    def test_reading_or_copying_from_the_hooks(self):
        for command in ["cp .githooks/pre-push /tmp/pre-push", "sed -n 1,20p .githooks/pre-push",
                        "diff .githooks/pre-push other/pre-push",
                        "tee log.txt < .githooks/pre-push"]:
            with self.subTest(command):
                self.assertFalse(hook.disables_git_hooks(command))


class ReviewedTest(unittest.TestCase):
    """Ways around the guard /code-review high found on dev-conventions#4."""

    def test_writing_over_a_hook_after_all(self):
        for command in ["cp noop.sh .githooks/pre-push 2>/dev/null",
                        "cp noop.sh .githooks/pre-push >/dev/null",
                        "cp noop .githooks/pre-push # x",
                        "cp -t .githooks pre-push", "cp --target-directory=.githooks pre-push",
                        "sed --in-place 's/main/none/' .githooks/pre-push",
                        "printf 'exit 0' >| .githooks/pre-push", "cp noop .GitHooks/pre-push"]:
            with self.subTest(command):
                self.assertTrue(hook.disables_git_hooks(command))

    def test_a_hook_in_another_case(self):
        # macOS's file system does not tell the cases apart.
        self.assertTrue(hook.writes_a_git_hook("/repo/.GitHooks/pre-push"))


class FileWriteTest(unittest.TestCase):
    """Claude's Write and Edit onto a hook: put to Gunnar, since a hook is changed that way too."""

    def test_a_file_in_the_hooks(self):
        for path in ["/repo/.githooks/pre-push", ".githooks/pre-push", "/repo/.githooks/new-hook"]:
            with self.subTest(path):
                self.assertTrue(hook.writes_a_git_hook(path))

    def test_any_other_file(self):
        for path in ["/repo/README.md", "/repo/doc/githooks.md", "/repo/.githooks-notes.md",
                     "/repo/x.githooks/pre-push", ""]:
            with self.subTest(path):
                self.assertFalse(hook.writes_a_git_hook(path))


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
