"""Writes palette.css and the table in README.md from palette.json: python3 palette/generate.py

palette.json is the one place a colour is set. The CSS carries it as custom properties for a site
to copy or import, and the table says what each colour is for and how much contrast it has
(WCAG's: text needs 4.5:1, lines and shapes 3:1). test_generate.py fails when either is stale.
"""
import json
import pathlib

HERE = pathlib.Path(__file__).resolve().parent
START = "<!-- palette:start -->"
END = "<!-- palette:end -->"

# What each colour is for, in the order the table lists them.
USES = {
    "logo-green": "The logo's green. On light backgrounds only as decoration: it fails contrast there.",
    "logo-green-dark": "The logo's green, just darker (same hue and saturation): green text on light backgrounds.",
    "logo-blue": "The logo's blue: links, accents and buttons on light backgrounds.",
    "light-blue": "Links, accents and buttons on dark backgrounds.",
    "logo-dot": "The dot in the logo, on light backgrounds.",
    "red": "Errors on light backgrounds.",
    "light-red": "Errors on dark backgrounds.",
    "white": "Light backgrounds; text on the blue.",
    "light-grey": "Quiet surfaces and lines on light backgrounds; text on dark ones.",
    "mid-grey": "Secondary text on dark backgrounds.",
    "grey": "Secondary text on light backgrounds; the edge of a form field.",
    "dark-grey": "Quiet surfaces and lines on dark backgrounds.",
    "near-black": "Text on light backgrounds; dark backgrounds. There is no pure black.",
}


def luminance(colour):
    channels = [int(colour[i:i + 2], 16) / 255 for i in (1, 3, 5)]
    channels = [c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4 for c in channels]
    return 0.2126 * channels[0] + 0.7152 * channels[1] + 0.0722 * channels[2]


def contrast(a, b):
    high, low = sorted([luminance(a), luminance(b)], reverse=True)
    return f"{(high + 0.05) / (low + 0.05):.1f}"


def css(palette):
    lines = ["/* Generated from palette.json by generate.py; change the colours there. */", ":root {"]
    lines += [f"  --palette-{name}: {value};" for name, value in palette.items()]
    return "\n".join(lines + ["}"]) + "\n"


def table(palette):
    rows = ["| Name | Value | For | On white | On near-black |", "| --- | --- | --- | --- | --- |"]
    for name, value in palette.items():
        rows.append(f"| `{name}` | `{value}` | {USES[name]} | {contrast(value, palette['white'])}:1 "
                    f"| {contrast(value, palette['near-black'])}:1 |")
    return "\n".join(rows)


def readme(palette, text):
    before, rest = text.split(START)
    after = rest.split(END)[1]
    return f"{before}{START}\n{table(palette)}\n{END}{after}"


def main():
    palette = json.loads((HERE / "palette.json").read_text())
    (HERE / "palette.css").write_text(css(palette))
    page = HERE / "README.md"
    page.write_text(readme(palette, page.read_text()))


if __name__ == "__main__":
    main()
