"""
Pins down what check_doc_references.py counts as a reference to the documentation, when one is
dead, and what the command reports.

A code comment, a CLAUDE.md or an OpenTofu file naming `doc/...` in prose is not a link, so
nothing else notices when the page it names moves. This is the check that does.

Run with:  python3 -m unittest discover -s check-doc-references
"""

import pathlib
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).parent))
import check_doc_references as check  # noqa: E402

SCRIPT = pathlib.Path(check.__file__)


class FindReferencesTest(unittest.TestCase):

    def test_a_document_named_in_a_code_comment(self):
        text = "// see doc/decisions/index.md for why"
        self.assertEqual(check.references(text), ["doc/decisions/index.md"])

    def test_a_chapter_named_by_its_directory(self):
        self.assertEqual(check.references("`doc/decisions/` says why"), ["doc/decisions/"])

    def test_several_on_one_line_and_in_markdown_links(self):
        text = "[a](doc/decisions/index.md) and doc/README.md, then (doc/decisions/)."
        self.assertEqual(check.references(text),
                         ["doc/decisions/index.md", "doc/README.md", "doc/decisions/"])

    def test_upper_case_and_underscores_anywhere_in_the_path(self):
        text = "doc/README.md, doc/Setup/index.md and doc/my_dir/First_Page.md"
        self.assertEqual(check.references(text),
                         ["doc/README.md", "doc/Setup/index.md", "doc/my_dir/First_Page.md"])

    def test_a_file_that_only_starts_with_md_is_not_a_page(self):
        self.assertEqual(check.references("doc/decisions/page.mdx, but doc/README.md."),
                         ["doc/README.md"])

    def test_a_longer_path_that_merely_ends_in_doc_is_not_a_reference(self):
        self.assertEqual(check.references("site/doc/notes.md and frontend-doc/x.md"), [])

    def test_the_bare_folder_and_other_files_are_not_checked_as_documents(self):
        self.assertEqual(check.references("the logo is doc/logo.svg, somewhere in doc/"), [])

    def test_a_chapter_or_page_at_the_end_of_a_sentence(self):
        self.assertEqual(check.references("see doc/deployment/. Or doc/decisions/index.md."),
                         ["doc/deployment/", "doc/decisions/index.md"])

    def test_a_longer_file_name_is_not_the_page_it_starts_with(self):
        self.assertEqual(check.references("doc/notes.md-draft, doc/page.md.orig"), [])

    def test_an_excluded_directory_is_left_alone(self):
        # TaskFest's doc/api/ holds generated files, not documentation.
        text = "doc/api/openapi.md and doc/apis/index.md"
        self.assertEqual(check.references(text, exclude=["doc/api/"]), ["doc/apis/index.md"])


class DeadReferencesTest(unittest.TestCase):

    def test_an_existing_document_and_chapter_are_fine(self):
        exists = {"doc/decisions/index.md", "doc/decisions"}.__contains__
        self.assertEqual(check.dead(["doc/decisions/index.md", "doc/decisions/"], exists), [])

    def test_a_moved_document_is_dead(self):
        exists = {"doc/decisions/index.md"}.__contains__
        self.assertEqual(check.dead(["doc/decisions.md"], exists), ["doc/decisions.md"])


class CommandTest(unittest.TestCase):
    """The command checks the git repository it is run in, which is where the action runs it."""

    def setUp(self):
        self.work = tempfile.TemporaryDirectory()
        self.repo = pathlib.Path(self.work.name)
        self.write("doc/README.md", "the chapters\n")
        self.write("src/app.py", "# see doc/README.md\n")
        subprocess.run(["git", "init", "-q", str(self.repo)], check=True)

    def tearDown(self):
        self.work.cleanup()

    def write(self, name, text):
        path = self.repo / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)

    def run_check(self, *args, cwd=None):
        subprocess.run(["git", "-C", str(self.repo), "add", "-A"], check=True)
        return subprocess.run([sys.executable, str(SCRIPT), *args], cwd=cwd or self.repo,
                              capture_output=True, text=True)

    def test_every_reference_resolving_passes(self):
        result = self.run_check()
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_a_dead_reference_fails_with_its_file_and_line(self):
        self.write("infra/main.tf", "# ok\n# see doc/moved.md\n")
        result = self.run_check()
        self.assertEqual(result.returncode, 1)
        self.assertIn("infra/main.tf:2: doc/moved.md", result.stderr)

    def test_an_untracked_file_is_not_read(self):
        self.write("build/out.txt", "doc/moved.md\n")
        (self.repo / ".gitignore").write_text("build/\n")
        self.assertEqual(self.run_check().returncode, 0)

    def test_an_excluded_directory_does_not_fail(self):
        self.write("src/api.py", "# generated into doc/api/openapi.md\n")
        self.assertEqual(self.run_check().returncode, 1)
        result = self.run_check("--exclude", "doc/api/")
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_run_from_a_subdirectory_checks_the_whole_repository(self):
        self.write("infra/main.tf", "# see doc/moved.md\n")
        result = self.run_check(cwd=self.repo / "src")
        self.assertEqual(result.returncode, 1)
        self.assertIn("infra/main.tf:1: doc/moved.md", result.stderr)


if __name__ == "__main__":
    unittest.main()
