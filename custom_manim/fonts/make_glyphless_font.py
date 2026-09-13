"""Builds PDFSceneGlyphless.ttf: a font where every glyph is empty.

It is used for the invisible, selectable text layer of PDFScene PDFs. Since the
glyphs have no outlines, no PDF viewer can draw them (not even when selected),
while copy/paste and search still work. Run:  python make_glyphless_font.py
"""
from fontTools.fontBuilder import FontBuilder
from fontTools.pens.ttGlyphPen import TTGlyphPen
import os

FAMILY = "PDFScene Glyphless"
UNITS_PER_EM = 1000
ADVANCE = 500
# Must match FONT_ASCENT / FONT_DESCENT in scene_to_svg.py
ASCENT = 900
DESCENT = 250

RANGES = [
    (0x0020, 0x007E),  # Basic Latin
    (0x00A0, 0x024F),  # Latin-1, Latin Extended A/B
    (0x0370, 0x03FF),  # Greek
    (0x0400, 0x04FF),  # Cyrillic
    (0x0590, 0x05FF),  # Hebrew
    (0x0600, 0x06FF),  # Arabic
    (0x0750, 0x077F),  # Arabic Supplement
    (0x2000, 0x206F),  # General Punctuation
    (0x20A0, 0x20CF),  # Currency
    (0x2100, 0x214F),  # Letterlike
    (0x2150, 0x218F),  # Number Forms
    (0x2190, 0x21FF),  # Arrows
    (0x2200, 0x22FF),  # Math Operators
    (0x2300, 0x23FF),  # Misc Technical
    (0x2500, 0x25FF),  # Box Drawing, Block Elements, Geometric Shapes
    (0x2600, 0x27BF),  # Misc Symbols, Dingbats
    (0x27C0, 0x27EF),  # Misc Math Symbols-A
    (0x2980, 0x2AFF),  # Misc Math Symbols-B, Supplemental Math Operators
    (0xFB50, 0xFDFF),  # Arabic Presentation Forms-A
    (0xFE70, 0xFEFF),  # Arabic Presentation Forms-B
]

def build(path):
    codepoints = [cp for start, end in RANGES for cp in range(start, end + 1)]
    names = {cp: f"uni{cp:04X}" for cp in codepoints}
    glyph_order = [".notdef"] + list(names.values())

    fb = FontBuilder(UNITS_PER_EM, isTTF=True)
    fb.setupGlyphOrder(glyph_order)
    fb.setupCharacterMap(names)
    fb.setupGlyf({name: TTGlyphPen(None).glyph() for name in glyph_order})
    fb.setupHorizontalMetrics({name: (ADVANCE, 0) for name in glyph_order})
    fb.setupHorizontalHeader(ascent=ASCENT, descent=-DESCENT)
    # Typst silently ignores fonts without the full/PostScript names
    fb.setupNameTable({
        "familyName": FAMILY,
        "styleName": "Regular",
        "uniqueFontIdentifier": f"{FAMILY} Regular",
        "fullName": f"{FAMILY} Regular",
        "psName": FAMILY.replace(" ", "") + "-Regular",
        "version": "Version 1.0",
    })
    fb.setupOS2(
        sTypoAscender=ASCENT, sTypoDescender=-DESCENT, sTypoLineGap=0,
        usWinAscent=ASCENT, usWinDescent=DESCENT,
        sxHeight=500, sCapHeight=700,
        fsSelection=0x40, achVendID="NONE",
    )
    fb.setupPost()
    fb.save(path)

if __name__ == "__main__":
    out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "PDFSceneGlyphless.ttf")
    build(out)
    print(f"Font saved to {out}")
