from manimlib import VMobject
from manimlib.mobject.svg.string_mobject import StringMobject
from manimlib.mobject.svg.text_mobject import MarkupText, Text
from manimlib.utils.color import color_to_rgb
from fontTools.pens.boundsPen import BoundsPen
from fontTools.ttLib import TTFont
from functools import lru_cache
from statistics import median
from xml.sax.saxutils import quoteattr
import html
import math
import re
import subprocess

# Metrics (in em) of fonts/PDFSceneGlyphless.ttf, the text layer font when the drawn font is unknown
FONT_ASCENT = 0.9
FONT_DESCENT = 0.25
# Text layer font for Tex, whose glyphs can't be matched to characters
TEX_FONT = "New Computer Modern"
# Only glyphs at least this tall (in em) are used to measure a line
MIN_GLYPH_HEIGHT = 0.3

TYPST_WEIGHTS = {"thin", "extralight", "light", "regular", "medium", "semibold", "bold", "extrabold", "black"}

def color_to_hex(color):
    rgb = color_to_rgb(color)
    return "#%02x%02x%02x" % (int(rgb[0] * 255), int(rgb[1] * 255), int(rgb[2] * 255))

def get_projector(scene, width, height):
    camera = scene.camera
    frame = camera.frame

    # Focal distance in canonical units
    d = frame.get_focal_distance() / frame.get_scale()

    def transform(p):
        p_local = frame.to_fixed_frame_point(p)
        z = p_local[2]
        if math.isclose(z, d):
            factor = 1000.0
        else:
            factor = d / (d - z)

        x_proj = p_local[0] * factor
        y_proj = p_local[1] * factor

        # Fixed frame height is 8.0 units (standard Manim)
        x_pixel = x_proj * (height / 8.0) + width / 2
        y_pixel = -y_proj * (height / 8.0) + height / 2

        return x_pixel, y_pixel

    return transform

def vmobject_to_svg_path(vmobject, scene, width, height):
    try:
        points = vmobject.get_points()
    except AttributeError:
        return ""

    if len(points) == 0:
        return ""

    transform = get_projector(scene, width, height)

    path_data = []
    # ManimGL uses quadratic beziers.
    # Points are stored as: [anch1, ctrl1, anch2, ctrl2, anch3, ...]
    # A shape can hold several subpaths (e.g. the holes of "B"); each needs its
    # own "M", otherwise the jump between them is drawn as a stray curve.
    for subpath in vmobject.get_subpaths():
        if len(subpath) < 3:
            continue
        start = transform(subpath[0])
        path_data.append(f"M {start[0]:.3f} {start[1]:.3f}")

        # Each segment is 2 points: control and end-anchor.
        for i in range(1, len(subpath) - 1, 2):
            control = transform(subpath[i])
            end = transform(subpath[i+1])
            path_data.append(f"Q {control[0]:.3f} {control[1]:.3f}, {end[0]:.3f} {end[1]:.3f}")

        if vmobject.consider_points_equal(subpath[0], subpath[-1]):
            path_data.append("Z")

    if not path_data:
        return ""

    try:
        fill_color = color_to_hex(vmobject.get_fill_color())
        fill_opacity = vmobject.get_fill_opacity()
        stroke_color = color_to_hex(vmobject.get_stroke_color())
        stroke_opacity = vmobject.get_stroke_opacity()
        stroke_width = vmobject.get_stroke_width()
    except Exception:
        return ""

    path_str = " ".join(path_data)
    style = f'fill="{fill_color}" fill-opacity="{fill_opacity}" stroke="{stroke_color}" stroke-opacity="{stroke_opacity}" stroke-width="{stroke_width}"'
    return f'<path d="{path_str}" {style} />'

@lru_cache(maxsize=None)
def resolve_font(family, weight, slant):
    """The font fontconfig (and so pango) draws a Text with: (family, file, index) or None."""
    weight = weight.lower()
    slant = "roman" if slant.lower() == "normal" else slant.lower()
    for pattern in (f"{family}:weight={weight}:slant={slant}", family):
        try:
            result = subprocess.run(
                ["fc-match", "-f", "%{family[0]}\n%{file}\n%{index}", pattern],
                capture_output=True, text=True, check=True,
            )
        except (OSError, subprocess.CalledProcessError):
            continue
        parts = result.stdout.split("\n")
        if len(parts) == 3 and parts[1]:
            return parts[0], parts[1], int(parts[2] or 0)
    return None

@lru_cache(maxsize=None)
def load_font(file, index):
    try:
        font = TTFont(file, fontNumber=index, lazy=True)
        return font, font["head"].unitsPerEm, font.getBestCmap(), font.getGlyphSet()
    except Exception:
        return None

@lru_cache(maxsize=None)
def glyph_metrics(file, index, char):
    """(x_min, y_min, x_max, y_max, advance) of a character's glyph in em, or None."""
    loaded = load_font(file, index)
    if loaded is None:
        return None
    font, units_per_em, cmap, glyph_set = loaded
    name = cmap.get(ord(char))
    if name is None:
        return None
    pen = BoundsPen(glyph_set)
    glyph_set[name].draw(pen)
    if pen.bounds is None:
        return None
    x_min, y_min, x_max, y_max = (v / units_per_em for v in pen.bounds)
    return x_min, y_min, x_max, y_max, font["hmtx"][name][0] / units_per_em

def is_invisible(mob):
    try:
        return mob.get_fill_opacity() == 0 and (mob.get_stroke_opacity() == 0 or mob.get_stroke_width() == 0)
    except Exception:
        return False

def get_plain_text(mob):
    if isinstance(mob, Text):
        return mob.text
    if isinstance(mob, MarkupText):
        return html.unescape(re.sub(r"<[^>]*>", "", mob.text))
    # Tex and other StringMobjects: fall back to the source string
    return mob.get_string()

def string_mobject_line_runs(mob):
    """Split a StringMobject into (text, glyphs, glyph_chars) triples, one per line.

    Text/MarkupText have one glyph submobject per non-whitespace character,
    which lets each line be matched to its own glyphs. Anything else (Tex,
    or a text whose glyphs were edited) becomes a single run with
    glyph_chars set to None.
    """
    string = get_plain_text(mob)
    glyphs = mob.submobjects
    if not isinstance(mob, MarkupText) or len(re.sub(r"\s", "", string)) != len(glyphs):
        return [(" ".join(string.split()), glyphs, None)]

    # Placeholder glyph drawn in place of a space (see Paragraph show_spaces)
    space_char = getattr(mob, "svg_space_char", None)
    runs = []
    index = 0
    for line in string.split("\n"):
        chars = []
        line_glyphs = []
        glyph_chars = []
        for char in line.strip():
            if char.isspace():
                chars.append(" ")
                continue
            line_glyphs.append(glyphs[index])
            glyph_chars.append(char)
            index += 1
            chars.append(" " if char == space_char else char)
        if line_glyphs:
            runs.append(("".join(chars), line_glyphs, glyph_chars))
    return runs

def glyph_box(glyph, transform):
    points = [transform(p) for p in glyph.get_all_points()]
    if not points:
        return None
    xs = [p[0] for p in points]
    ys = [p[1] for p in points]
    return min(xs), min(ys), max(xs), max(ys)

def measure_line_with_font(boxes, file, index):
    """Place a line of text in the font it was drawn with.

    Each glyph's pixel box is matched with its outline in the font file, which
    gives the em size and baseline exactly. Returns (x, baseline, width, em) in
    pixels, where x..x+width spans the advance widths, or None.
    """
    samples = []
    for box, char in boxes:
        metrics = glyph_metrics(file, index, char)
        if metrics and metrics[3] - metrics[1] >= MIN_GLYPH_HEIGHT:
            samples.append((box, metrics))
    if not samples:
        return None
    em = median((box[3] - box[1]) / (m[3] - m[1]) for box, m in samples)
    # Pixel y grows downwards while font y grows upwards
    baseline = median(box[3] + m[1] * em for box, m in samples)

    (first_box, first_char), (last_box, last_char) = boxes[0], boxes[-1]
    first = glyph_metrics(file, index, first_char)
    last = glyph_metrics(file, index, last_char)
    x = first_box[0] - first[0] * em if first else first_box[0]
    end = last_box[2] + (last[4] - last[2]) * em if last else last_box[2]
    return x, baseline, end - x, em

def string_mobject_text_runs(mob, transform):
    """Measure each line of a StringMobject in SVG pixels, for the text layer."""
    if getattr(mob, "svg_skip_text", False):
        return []
    font = None
    weight, style = "regular", "normal"
    if isinstance(mob, MarkupText):
        font = resolve_font(mob.font, mob.weight, mob.slant)
        weight = mob.weight.lower() if mob.weight.lower() in TYPST_WEIGHTS else "regular"
        style = mob.slant.lower()

    runs = []
    for content, glyphs, glyph_chars in string_mobject_line_runs(mob):
        if not content.strip() or all(is_invisible(g) for g in glyphs):
            continue
        boxes = [
            (box, char)
            for box, char in zip((glyph_box(g, transform) for g in glyphs), glyph_chars or [None] * len(glyphs))
            if box
        ]
        if not boxes:
            continue

        measured = None
        if font and glyph_chars:
            family, file, index = font
            measured = measure_line_with_font(boxes, file, index)
        if measured:
            x, baseline, width, em = measured
            runs.append(dict(text=content, font=family, weight=weight, style=style, x=x, y=baseline, w=width, size=em))
            continue

        # No usable font: fit the text box to the glyphs' bounding box
        left = min(b[0] for b, _ in boxes)
        top = min(b[1] for b, _ in boxes)
        right = max(b[2] for b, _ in boxes)
        bottom = max(b[3] for b, _ in boxes)
        if right - left <= 0 or bottom - top <= 0:
            continue
        em = (bottom - top) / (FONT_ASCENT + FONT_DESCENT)
        runs.append(dict(
            text=content, font=TEX_FONT if glyph_chars is None else "", weight="regular", style="normal",
            x=left, y=top + FONT_ASCENT * em, w=right - left, size=em,
        ))
    return runs

def text_runs_to_svg_metadata(runs):
    """Serialize text runs as <metadata>, which is not rendered but read by pdfscene.typ."""
    elements = [
        f'<run x="{run["x"]:.3f}" y="{run["y"]:.3f}" w="{run["w"]:.3f}" size="{run["size"]:.3f}" '
        f'font={quoteattr(run["font"])} weight="{run["weight"]}" style="{run["style"]}" t={quoteattr(run["text"])} />'
        for run in runs
    ]
    return ['<metadata id="pdfscene-text">'] + elements + ['</metadata>']

def save_scene_to_svg(scene, file_path):
    camera = scene.camera
    width = camera.get_pixel_width()
    height = camera.get_pixel_height()
    transform = get_projector(scene, width, height)

    svg_header = [
        f'<?xml version="1.0" encoding="UTF-8" standalone="no"?>',
        f'<!-- Generated by ManimGL SVG Exporter (Quadratic Bezier Fix) -->',
        f'<svg width="{width}" height="{height}" viewBox="0 0 {width} {height}" xmlns="http://www.w3.org/2000/svg" style="background-color: black;">'
    ]
    svg_body = []
    text_runs = []
    try:
        mobs=scene.mobjects
    except:
        mobs=scene
    for mob in mobs:
        for submob in mob.get_family():
            if isinstance(submob, VMobject):
                path = vmobject_to_svg_path(submob, scene, width, height)
                if path:
                    svg_body.append(path)
            if isinstance(submob, StringMobject):
                text_runs.extend(string_mobject_text_runs(submob, transform))

    if text_runs:
        svg_header += text_runs_to_svg_metadata(text_runs)

    svg_footer = ['</svg>']

    content = "\n".join(svg_header + svg_body + svg_footer)
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"SVG saved to {file_path}")
