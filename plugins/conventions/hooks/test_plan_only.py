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


class AllowedTest(unittest.TestCase):

    def test_reading_and_planning(self):
        for command in ["./deployment/aws-tofu/tofu.sh site plan", "tofu plan -destroy",
                        "tofu validate", "tofu fmt -check", "tofu init -backend=false",
                        "tofu state list", "tofu show -json plan.bin", "tofu output",
                        "tofu workspace list", "tofu init -backend=false -input=false",
                        "git commit -m 'apply review fixes'", "grep apply README.md"]:
            with self.subTest(command):
                self.assertFalse(hook.changes_infrastructure(command))


if __name__ == "__main__":
    unittest.main()
