"""palette.css, the swatches, the overview and README.md's table say what palette.json says
(generate.py writes them)."""
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

    def test_the_swatches_are_current(self):
        folder = generate.HERE / "swatches"
        self.assertEqual(sorted(path.name for path in folder.iterdir()),
                         sorted(f"{name}.svg" for name in self.palette))
        for name, value in self.palette.items():
            self.assertEqual(generate.swatch(value), (folder / f"{name}.svg").read_text(), name)

    def test_the_overview_is_current(self):
        self.assertEqual(generate.overview(self.palette), (generate.HERE / "overview.svg").read_text())

    def test_a_colour_is_grouped_by_its_hue(self):
        self.assertEqual(generate.group("#ffffff"), "White and greys")
        self.assertEqual(generate.group("#656565"), "White and greys")
        self.assertEqual(generate.group("#111111"), "White and greys")
        self.assertEqual(generate.group("#b42318"), "Red")
        self.assertEqual(generate.group("#f28b4b"), "Orange")
        self.assertEqual(generate.group("#7eae2a"), "Green")
        self.assertEqual(generate.group("#a6d8f5"), "Blue")
        self.assertEqual(generate.group("#8e44ad"), "Purple")
        self.assertEqual(generate.group("#e0218a"), "Red")

    def test_the_groups_go_greys_first_then_by_hue_each_from_light_to_dark(self):
        palette = {"blue": "#0067a6", "black": "#111111", "red": "#b42318", "white": "#ffffff",
                   "light-red": "#f04438", "green": "#7eae2a"}
        self.assertEqual(generate.groups(palette), {
            "White and greys": ["white", "black"],
            "Red": ["light-red", "red"],
            "Green": ["green"],
            "Blue": ["blue"],
        })
        self.assertEqual(list(generate.groups(palette)), ["White and greys", "Red", "Green", "Blue"])

    def test_contrast_is_wcags(self):
        self.assertEqual(generate.contrast("#ffffff", "#000000"), "21.0")
        self.assertEqual(generate.contrast("#0067a6", "#ffffff"), "6.0")


if __name__ == "__main__":
    unittest.main()
