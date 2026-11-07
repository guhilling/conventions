"""Writes palette.css, the swatches, the overview and the table in README.md from palette.json:
python3 palette/generate.py

palette.json is the one place a colour is set. The CSS carries it as custom properties for a site
to copy or import, and the table says what each colour is for and how much contrast it has
(WCAG's: text needs 4.5:1, lines and shapes 3:1), with a swatch in front of each, swatches/<name>.svg.
overview.svg shows them all, a row for each group of similar colours. test_generate.py fails when
any of them is stale.
"""
import colorsys
import json
import pathlib

HERE = pathlib.Path(__file__).resolve().parent
START = "<!-- palette:start -->"
END = "<!-- palette:end -->"

# What each colour is for, in palette.json's order.
USES = {
    "logo-green": "The logo's green. On light backgrounds only as decoration: it fails contrast there.",
    "logo-green-dark": "The logo's green, just darker (same hue and saturation): green text on light backgrounds.",
    "logo-blue": "The logo's blue: links, accents and buttons on light backgrounds.",
    "light-blue": "Links, accents and buttons on dark backgrounds.",
    "logo-dot": "The dot in the logo, on light backgrounds.",
    "red": "Errors on light backgrounds.",
    "light-red": "Errors on dark backgrounds.",
    "pale-red": "The light red, just lighter (same hue and saturation): errors on dark grey surfaces.",
    "white": "Light backgrounds; text on the blue.",
    "light-grey": "Quiet surfaces and lines on light backgrounds; text on dark ones.",
    "mid-grey": "Secondary text on dark backgrounds.",
    "grey": "Secondary text on light backgrounds; the edge of a form field.",
    "dark-grey": "Quiet surfaces and lines on dark backgrounds.",
    "near-black": "Text on light backgrounds; dark backgrounds. There is no pure black.",
}


# The groups, in the order the overview and the table show them: the greys, then by hue, each up
# to the hue (in degrees) named here, so that a new colour finds its group on its own.
GREYS = "White and greys"
HUES = [(15, "Red"), (45, "Orange"), (70, "Yellow"), (170, "Green"), (260, "Blue"), (320, "Purple"),
        (360, "Red")]
ORDER = list(dict.fromkeys([GREYS] + [name for _, name in HUES]))


def group(colour):
    r, g, b = (int(colour[i:i + 2], 16) / 255 for i in (1, 3, 5))
    hue, lightness, saturation = colorsys.rgb_to_hls(r, g, b)
    if saturation < 0.12 or lightness < 0.06 or lightness > 0.97:
        return GREYS
    return next(name for limit, name in HUES if hue * 360 < limit)


def groups(palette):
    """The colours' names by group, each group from light to dark."""
    found = {}
    for name in sorted(palette, key=lambda name: -luminance(palette[name])):
        found.setdefault(group(palette[name]), []).append(name)
    return {name: found[name] for name in ORDER if name in found}


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


def swatch(colour, w=48, h=16):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}">'
            f'<rect x="0.5" y="0.5" width="{w - 1}" height="{h - 1}" rx="3" fill="{colour}" stroke="#888888"/>'
            f'</svg>\n')


def overview(palette):
    """A row for each group: its name, then a swatch for each colour with its name and value."""
    label, column, row = 150, 130, 96
    rows = groups(palette)
    w = label + column * max(len(names) for names in rows.values()) + 10
    h = row * len(rows) + 10
    text = 'font-family="Inter Tight, Helvetica, Arial, sans-serif" fill="#111111"'
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}">',
             f'<rect width="{w}" height="{h}" fill="#ffffff"/>']
    for i, (heading, names) in enumerate(rows.items()):
        y = 10 + row * i
        parts.append(f'<text x="16" y="{y + 28}" font-size="15" font-weight="600" {text}>{heading}</text>')
        for j, name in enumerate(names):
            x = label + column * j
            parts.append(f'<rect x="{x + 0.5}" y="{y + 0.5}" width="119" height="47" rx="4" '
                         f'fill="{palette[name]}" stroke="#888888"/>')
            parts.append(f'<text x="{x}" y="{y + 66}" font-size="13" {text}>{name}</text>')
            parts.append(f'<text x="{x}" y="{y + 82}" font-size="12" {text}>{palette[name]}</text>')
    return "\n".join(parts + ["</svg>"]) + "\n"


def table(palette):
    """A table for each group, with a swatch in front of each colour."""
    tables = []
    for heading, names in groups(palette).items():
        rows = [f"### {heading}", "", "| | Name | Value | For | On white | On near-black |",
                "| --- | --- | --- | --- | --- | --- |"]
        for name in names:
            value = palette[name]
            rows.append(f"| ![{value}](swatches/{name}.svg) | `{name}` | `{value}` | {USES[name]} "
                        f"| {contrast(value, palette['white'])}:1 | {contrast(value, palette['near-black'])}:1 |")
        tables.append("\n".join(rows))
    return "\n\n".join(tables)


def readme(palette, text):
    before, rest = text.split(START)
    after = rest.split(END)[1]
    return f"{before}{START}\n{table(palette)}\n{END}{after}"


def main():
    palette = json.loads((HERE / "palette.json").read_text())
    (HERE / "palette.css").write_text(css(palette))
    folder = HERE / "swatches"
    folder.mkdir(exist_ok=True)
    for path in folder.glob("*.svg"):
        if path.stem not in palette:
            path.unlink()
    for name, value in palette.items():
        (folder / f"{name}.svg").write_text(swatch(value))
    (HERE / "overview.svg").write_text(overview(palette))
    page = HERE / "README.md"
    page.write_text(readme(palette, page.read_text()))


if __name__ == "__main__":
    main()
