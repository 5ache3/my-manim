// Places a PDFScene screenshot (an SVG from scene_to_svg.py) and lays an
// invisible, selectable text layer over it, one text object per line.
//
// The layer is set in the font manim drew the text with, at the same size and
// position, so viewers that redraw selected text (Papers, Evince) show the same
// letters. Characters missing from that font use "PDFScene Glyphless", whose
// glyphs are all empty.
//
// Compile with:  typst compile --font-path <custom_manim/fonts> file.typ
// Usage:         #scene-page(read("0.svg", encoding: none))

#let _children(node, tag) = node.children.filter(e => type(e) == dictionary and e.tag == tag)

#let scene-page(source, width: 100%) = layout(size => {
  let svg = xml(source).find(e => type(e) == dictionary and e.tag == "svg")
  let meta = _children(svg, "metadata").filter(e => e.attrs.at("id", default: none) == "pdfscene-text")
  let runs = if meta.len() == 0 { () } else { _children(meta.first(), "run") }

  let w = if type(width) == ratio {
    size.width * width
  } else if type(width) == relative {
    size.width * width.ratio + width.length
  } else {
    width
  }
  // Page length per SVG pixel
  let k = w / float(svg.attrs.width)

  block(width: w, {
    image(source, format: "svg", width: w)
    for run in runs {
      let a = run.attrs
      let family = a.at("font", default: "")
      let line = text(
        font: if family == "" { "PDFScene Glyphless" } else { (family, "PDFScene Glyphless") },
        weight: a.at("weight", default: "regular"),
        style: a.at("style", default: "normal"),
        fallback: false,
        ligatures: false,
        fill: rgb(0, 0, 0, 0),
        size: float(a.size) * k,
        top-edge: "baseline",
        bottom-edge: "baseline",
        a.t,
      )
      let natural = measure(line).width
      if natural > 0pt {
        // Stretch the line horizontally so it covers the drawn glyphs
        place(top + left, dx: float(a.x) * k, dy: float(a.y) * k,
          scale(x: float(a.w) * k / natural * 100%, origin: left, line))
      }
    }
  })
})
