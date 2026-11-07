"""palette.css and README.md's table say what palette.json says (generate.py writes them)."""
import json
import unittest

import generate


class PaletteTest(unittest.TestCase):

    def setUp(self):
        self.palette = json.loads((generate.HERE / "palette.json").read_text())

    def test_the_css_is_current(self):
        self.assertEqual(generate.css(self.palette), (generate.HERE / "palette.css").read_text())

    def test_the_table_is_current(self):
        text = (generate.HERE / "README.md").read_text()
        self.assertEqual(generate.readme(self.palette, text), text)

    def test_every_colour_says_what_it_is_for(self):
        self.assertEqual(list(self.palette), list(generate.USES))

    def test_contrast_is_wcags(self):
        self.assertEqual(generate.contrast("#ffffff", "#000000"), "21.0")
        self.assertEqual(generate.contrast("#0067a6", "#ffffff"), "6.0")


if __name__ == "__main__":
    unittest.main()
