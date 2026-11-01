"""
Pins down which shell commands plan-only.py refuses.

Gunnar applies the infrastructure himself; Claude may plan it, and nothing more (CLAUDE.md,
#6). Like keep-git-hooks.py this matches text rather than parsing the shell: a false alarm costs
a reworded command, a miss changes AWS.

Run with:  python3 -m unittest discover -s plugins/conventions/hooks -p 'test_*.py'
"""

import importlib.util
import pathlib
import unittest

_spec = importlib.util.spec_from_file_location(
    "plan_only", pathlib.Path(__file__).with_name("plan-only.py"))
hook = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(hook)


class RefusedTest(unittest.TestCase):

    def test_anything_that_changes_infrastructure_or_its_state(self):
        for command in ["tofu apply", "./deployment/aws-tofu/tofu.sh site apply -auto-approve",
                        "cd site && tofu destroy", "tofu -chdir=site import aws_s3_bucket.x y",
                        "terraform apply plan.bin", "tofu state rm aws_s3_bucket.site",
                        "tofu force-unlock 1234", "tofu taint aws_s3_bucket.site",
                        "npm test\n./tofu.sh bootstrap apply",
                        # `test` creates and destroys real resources; the others write state.
                        "tofu -chdir=site test", "./deployment/aws-tofu/tofu.sh site refresh",
                        "tofu workspace delete old", "tofu workspace new other",
                        "tofu init -migrate-state",
                        # A line continued with a backslash is still one command.
                        "./tofu.sh site \\\n  apply -auto-approve"]:
            with self.subTest(command):
                self.assertTrue(hook.changes_infrastructure(command))

    def test_the_ways_around_it_found_on_470(self):
        for command in [# Migrating state without asking, and making a workspace by selecting it.
                        "tofu init -force-copy", "tofu workspace select -or-create other",
                        # A message whose command substitution would run it.
                        'git commit -m "$(tofu apply -auto-approve)"',
                        "gh pr create --body \"`tofu destroy`\"",
                        # A here-document read by a shell, not by git or gh.
                        "bash <<'EOF'\ntofu apply\nEOF"]:
            with self.subTest(command):
                self.assertTrue(hook.changes_infrastructure(command))


class ReviewedTest(unittest.TestCase):
    """Ways around the guard /code-review high found on dev-conventions#4."""

    def test_text_that_is_not_gits_or_ghs_to_store(self):
        for command in [# A here-document read by a shell, on a line that names git.
                        'git commit -m "$(bash <<\'EOF\'\ntofu apply -auto-approve\nEOF\n)"',
                        "bash <<'X'; git commit -F - <<'EOF'\ntofu apply -auto-approve\nX\nm\nEOF",
                        "bash -s git <<'EOF'\ntofu apply\nEOF",
                        # git running a shell through an alias.
                        "git -c alias.x='!sh' x <<'EOF'\ntofu apply -auto-approve\nEOF",
                        # A trailing backslash is literal in a quoted here-document.
                        "git commit -F - <<'EOF'\nmsg \\\nEOF\ntofu apply -auto-approve",
                        # A quote that closes a string, not one that opens a message.
                        "echo 'a -m '; tofu apply -auto-approve; echo ''",
                        'echo "a -m "; tofu apply -auto-approve; echo ""',
                        "bash -c -m 'tofu apply -auto-approve'",
                        # OpenTofu takes a flag with two dashes as well.
                        "tofu init --force-copy", "tofu init --migrate-state"]:
            with self.subTest(command):
                self.assertTrue(hook.changes_infrastructure(command))

    def test_a_quoted_subcommand_of_env_sh(self):
        for command in ["./env.sh 'up' qa", './env.sh "down" prod --yes']:
            with self.subTest(command):
                self.assertTrue(hook.lifecycle(command))


class ConfirmedTest(unittest.TestCase):
    """env.sh's own applies: Gunnar confirms them, not refused (his decision on #470)."""

    def test_starting_stopping_and_the_account_root(self):
        for command in ["./deployment/aws-tofu/env.sh up qa",
                        "deployment/aws-tofu/env.sh down prod --yes",
                        "cd deployment/aws-tofu && ./env.sh account", "bash env.sh up qa",
                        "TASKFEST_QA_AWS_PROFILE=x ./env.sh -y down qa"]:
            with self.subTest(command):
                self.assertTrue(hook.lifecycle(command))
                self.assertFalse(hook.changes_infrastructure(command))

    def test_what_env_sh_does_besides(self):
        for command in ["./deployment/aws-tofu/env.sh status qa", "./env.sh help",
                        "./env.sh migrate qa", "./env.sh db-bootstrap qa", "grep -n up env.sh"]:
            with self.subTest(command):
                self.assertFalse(hook.lifecycle(command))


class AllowedTest(unittest.TestCase):

    def test_reading_and_planning(self):
        for command in ["./deployment/aws-tofu/tofu.sh site plan", "tofu plan -destroy",
                        "tofu validate", "tofu fmt -check", "tofu init -backend=false",
                        "tofu state list", "tofu show -json plan.bin", "tofu output",
                        "tofu workspace list", "tofu init -backend=false -input=false",
                        "git commit -m 'apply review fixes'", "grep apply README.md"]:
            with self.subTest(command):
                self.assertFalse(hook.changes_infrastructure(command))

    def test_selecting_a_workspace_that_exists(self):
        self.assertFalse(hook.changes_infrastructure("tofu workspace select other"))

    def test_text_that_only_mentions_a_change(self):
        # A message or a body is text to git and gh, and runs nothing.
        for command in ["git commit -m 'Gunnar runs tofu apply himself'",
                        'gh pr create --title "Docs" --body "Then run tofu apply on qa."',
                        "gh pr comment 3 --body='run ./env.sh up qa first'",
                        "git commit -m \"$(cat <<'EOF'\nRun tofu apply, then env.sh up.\nEOF\n)\"",
                        "git commit -F - <<'EOF'\nRun tofu destroy only by hand.\nEOF",
                        "gh pr create --body-file - <<'EOF'\nenv.sh down qa\nEOF\ngit status"]:
            with self.subTest(command):
                self.assertFalse(hook.changes_infrastructure(command))
                self.assertFalse(hook.lifecycle(command))


if __name__ == "__main__":
    unittest.main()
