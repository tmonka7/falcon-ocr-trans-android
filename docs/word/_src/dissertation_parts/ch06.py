"""Chapter 6: Translucent Layout-Preserving Re-rendering."""
import math


def _srgb_lum(v8: float) -> float:
    cc = v8 / 255.0
    return cc / 12.92 if cc <= 0.04045 else ((cc + 0.055) / 1.055) ** 2.4


def _ratio(a8: float, b8: float) -> float:
    la, lb = _srgb_lum(a8), _srgb_lum(b8)
    hi, lo = max(la, lb), min(la, lb)
    return (hi + 0.05) / (lo + 0.05)


def _bisect_steps(p: float, eps: float = 0.25) -> int:
    lo = max(4.0, 0.45 * p)
    hi = max(lo, 1.15 * p)
    n = 0
    while hi - lo > eps:
        hi = (lo + hi) / 2  # the count does not depend on which half is kept
        n += 1
    return n


def build(c):
    c.chapter(6, "Translucent Layout-Preserving Re-rendering")
    c.p("The third stage paints each translation back into the page where its source text was. This "
        "chapter presents the rendering model implemented in `LayoutRenderer` and `TextFitter`. Its "
        "central idea is to replace the usual opaque erase of the original text with a translucent, "
        "feathered highlight in the locally estimated paper colour, and to secure legibility locally "
        "with a halo drawn around each new glyph. The model is simple enough to analyse exactly: "
        "Proposition 6.1 states precisely how much of the original glyphs and of the page texture "
        "survives, and Proposition 6.2 bounds the cost and quality of the size-fitting search.")

    c.h2("Goals and Constraints", key="render_goals")
    c.p("The renderer must preserve, for every translated block, its position, its geometry, its "
        "rotation, its size relative to neighbouring text, its ink and paper colours, and — the property "
        "that opaque erasure destroys — the texture of the page underneath: paper grain, gradients, "
        "photographs behind signage. It must keep the translation legible whatever lies beneath. And it "
        "must do so without a further neural network, because the OCR and MT models already occupy the "
        "memory budget. It does *not* attempt to reproduce the typeface, weight or letterforms of the "
        "original; the system font is substituted, which carries CJK coverage through the platform's "
        "font fallback without bundling a font.")

    c.h2("Block Model", key="blocks")
    c.p("Rendering works on *blocks*. By default a block is one translated paragraph; an option renders "
        "one block per line instead. A block carries its text y, an upright layout rectangle T, a "
        "rotation angle θ, a preferred text size p and a line height h, an ink colour κ and a paper "
        "colour π, and the quadrilaterals {q_{i}} of its source lines ({T:block}).")
    c.table("block", "Fields of a paragraph block and how they are derived (`LayoutRenderer.paragraphBlocks`)",
            ["Field", "Derivation", "Reason"],
            [["y", "Paragraph translation", "Blocks with an empty translation are skipped, so the original "
              "is left untouched where nothing replaces it"],
             ["θ", "Median of the line angles (element ⌊n/2⌋ of the sorted angles); |θ| ≤ 0.75° treated as 0",
              "One skewed detection cannot tilt the paragraph; avoids needless rotation"],
             ["T (upright)", "Union of line bounds", "—"],
             ["T (rotated)", "Centred on the union of line bounds; width = widest line along its baseline; "
              "height = height of the union of bounds", "Layout happens in the block's own frame"],
             ["h", "Median line height", "Robust to a mis-sized line"],
             ["p", "0.82 h", "Line height includes leading; the glyph size is smaller"],
             ["κ, π", "Colours of the paragraph's first line", "One estimate per block"],
             ["{q_{i}}", "Source line quadrilaterals", "Region the highlight must cover"]],
            widths=[2.6, 7.2, 6.5])
    c.p("For a rotated block the height of T is taken from the axis-aligned bounds of the rotated "
        "lines, which exceeds the upright height: for a single line of width w and height h at angle θ "
        "the axis-aligned height is w sin θ + h cos θ. The rectangle is therefore generous in height for "
        "rotated paragraphs, which makes overflow less likely but lets the highlight extend beyond the "
        "original lines along the normal. Rendering runs in two passes over all blocks — first every "
        "highlight, then all text — so that a neighbouring block's highlight can never fade glyphs that "
        "have already been drawn. The source bitmap is copied to a new ARGB_8888 bitmap and never "
        "modified.")

    c.h2("Highlight Region", key="omega")
    c.p("Let 𝓔_{γ} scale a shape by 1 + γ about its centre, 𝓔_{γ}(q) = c_{q} + (1 + γ)(q − c_{q}), and let "
        "𝓡_{θ} rotate about the centre of T. The highlight region of a block is")
    c.eq("Ω = ( ∪_{i} 𝓔_{γ}(q_{i}) ) ∪ 𝓡_{θ}( 𝓔_{γ}(T) ),        γ = 0.06", key="omega")
    c.p("The growth γ covers the fringe of antialiased pixels that a tight detection box leaves outside, "
        "and including T covers wherever the new text will land, which may extend beyond the original "
        "lines. The union is computed *geometrically*, with path Boolean operations, before any pixel is "
        "filled. The order matters: filling overlapping translucent shapes one after another compounds "
        "their opacity. Two overlapping layers of opacity α have an effective opacity 1 − (1 − α)^{2}; for "
        "α = 150/255 that is about 0.83 instead of 0.59 (analytical), and adjacent line boxes, which "
        "overlap after unclipping and growth, would show darker (or lighter) bands between lines. "
        "{F:union} illustrates the difference on a synthetic example.")
    c.figure("union", "highlight_union", "Filling grown line boxes one by one compounds opacity in their "
             "overlaps (a); filling their geometric union once gives a uniform α (b). Synthetic "
             "illustration; dotted outlines are the grown line boxes.", width=15.5)

    c.h2("Compositing", key="composite")
    c.p("Ω is filled with the paper colour π at opacity α using source-over compositing "
        "[@porter1984compositing]. The shape's corners are rounded with radius 0.18 h, and its edge is "
        "feathered with a Gaussian blur mask of radius 0.06 h (applied only when that radius is at least "
        "half a pixel; blur mask filters are honoured because the canvas is bitmap-backed and therefore "
        "rendered in software). Writing α(p) for the effective opacity at pixel p — equal to α in the "
        "interior of Ω and falling smoothly to 0 across the feathered edge — the output is")
    c.eq("Î(p) = α(p) π + (1 − α(p)) I(p),        0 ≤ α(p) ≤ α", key="over")
    c.p("The default opacity is α = 150/255 ≈ 0.59 (`LayoutRenderer.DEFAULT_HIGHLIGHT_ALPHA`). Setting "
        "α = 255/255 reproduces the former opaque erase, and α = 0 disables the highlight.")

    c.h3("Analysis of attenuation", key="prop61")
    c.definition("Proposition", "6.1", "Let an original glyph pixel have colour κ on paper of colour π, "
                 "and model page texture as a perturbation δ of the paper colour, so that a background "
                 "pixel has colour π + δ. At a pixel of Ω with effective opacity α(p), compositing "
                 "with Equation {E:over} yields a ghost contrast |κ̂ − π̂| = (1 − α(p)) |κ − π| and a texture "
                 "amplitude |δ̂| = (1 − α(p)) |δ|. In the interior of Ω both retain exactly the fraction "
                 "1 − α; everywhere in Ω they retain at least 1 − α. The statement holds per colour "
                 "channel in the colour space in which compositing is performed.")
    c.proof("Apply Equation {E:over} to the three colours involved. The paper maps to "
            "π̂ = απ + (1 − α)π = π (dropping the argument p). A glyph pixel maps to "
            "κ̂ = απ + (1 − α)κ, so κ̂ − π̂ = (1 − α)(κ − π). A textured paper pixel maps to "
            "απ + (1 − α)(π + δ) = π + (1 − α)δ, so δ̂ = (1 − α)δ. Taking absolute values channel by "
            "channel gives the equalities; since α(p) ≤ α, 1 − α(p) ≥ 1 − α.")
    c.p("Three consequences follow. First, compositing is affine in the destination colour, so *every* "
        "colour difference inside Ω — between glyph and paper, between texture and paper, between two "
        "texture values — is scaled by the same factor 1 − α. The highlight is a uniform contrast "
        "reduction toward π, not a removal: the page texture is attenuated, not erased, and the patch "
        "artefact of opaque filling, whose interior has zero texture, is avoided. With the default "
        "α ≈ 0.59, the retained fraction is 1 − α ≈ 0.41 (analytical; {F:atten}). Second, the result is "
        "exact only in the compositing colour space. Android blends gamma-encoded sRGB values [@srgb], so "
        "the proposition holds for encoded values; perceived contrast and the WCAG contrast ratio "
        "[@wcag21], which are defined on linearised luminance, follow monotonically but not linearly. "
        "Third, the analysis assumes that the estimated paper colour equals the true local paper colour. "
        "If the estimate is biased by ε, the region's mean shifts by αε toward the estimate — a visible "
        "tint of the highlighted area — while the contrast statements, which concern differences, are "
        "unaffected.")
    c.figure("atten", "attenuation", "Fraction of glyph contrast and texture amplitude retained inside the "
             "highlight as a function of α (analytical, Proposition 6.1).", width=14)
    rows = []
    for a in (0, 90, 150, 200, 255):
        ghost = 255 * a / 255.0
        rows.append([f"{a}", f"{1 - a / 255:.2f}", f"{ghost:.0f}", f"{_ratio(0, ghost) if a else 21.0:.1f} : 1"])
    c.p("To connect the encoded-value result with perceived contrast, {T:ghost} evaluates the simplest "
        "case — black ink (κ = 0) on white paper (π = 255) in all channels — for several opacities. The "
        "ghost glyph takes the encoded value 255α, and its WCAG contrast ratio against the paper "
        "follows from the sRGB transfer function. At the default opacity the ghost retains 41% of the "
        "encoded difference but has a contrast ratio of about 3:1, below the 4.5:1 level that WCAG "
        "requires for body text; the original remains recognisable as a ghost while the new text, "
        "protected by the halo, keeps the full 21:1 (analytical).")
    c.table("ghost", "Ghost of black text on white paper under the highlight (analytical: Proposition 6.1 "
                     "and the WCAG 2.1 contrast formula)",
            ["α (0–255)", "Retained fraction 1 − α", "Ghost encoded value", "Ghost contrast ratio vs paper"],
            rows, widths=[3.2, 4.2, 4.0, 4.9])

    c.h2("Halo", key="halo")
    c.p("The ghost of the original could compete with the new glyphs, especially where a long original "
        "sits behind a short translation or where strokes of both overlap. The renderer therefore draws "
        "the laid-out translation twice with the same text layout: first stroked in the paper colour π "
        "with stroke width w_{h} = 0.16 s (s the fitted text size) and round joins, then filled in the "
        "ink colour κ.")
    c.definition("Corollary", "6.1", "Every point within distance w_{h}/2 = 0.08 s of the outline of a new "
                 "glyph, outside the glyph, has colour exactly π after the halo pass, provided no later "
                 "draw covers it. The new glyphs therefore have their full original contrast |κ − π| "
                 "against their immediate surroundings, independently of α and of what lies beneath.")
    c.proof("A stroke of width w_{h} centred on the glyph outline paints every point within w_{h}/2 of "
            "the outline with π at full opacity, replacing whatever the highlight left there, including "
            "any ghost. The subsequent fill paints the glyph interior with κ. Hence, locally, the glyph "
            "is κ on π.")
    c.p("Because stroking does not change glyph advances, the line breaks chosen during size fitting "
        "remain valid for the halo pass. The proviso in the corollary is not vacuous: blocks are "
        "typeset one after another, so if two blocks' layout rectangles overlap, the halo of the later "
        "block can overpaint glyphs of the earlier one. Within a block the order is safe, because the "
        "layout strokes all its lines before filling any of them. The halo and the highlight divide the "
        "work: the highlight lowers the ghost uniformly and keeps the texture; the halo guarantees "
        "legibility locally. This is why the highlight can stay faint.")

    c.h2("Size Fitting by Bisection", key="fit")
    c.p("Translations change length: English into Chinese or Japanese typically shortens, the reverse "
        "typically lengthens. Reusing the source size overflows the box often enough to be the norm, so "
        "the size is searched for. Let H(s) be the height of the translation laid out at font size s and "
        "width |T|_{w} with the platform's high-quality line breaking [@knuth1981breaking]. With anchor "
        "p = 0.82 h, the target is")
    c.eq("s* = max { s ∈ [s_{lo}, s_{hi}] : H(s) ≤ |T|_{h} },    s_{lo} = max(4, 0.45 p),    s_{hi} = max(s_{lo}, 1.15 p)",
         key="fit")
    c.p("The lower bound keeps text legible (and never below 4 pixels); the upper bound stops short "
        "translations from looking shouty. `TextFitter.fit` proceeds as follows:")
    c.code("""paint.size = lo;  L = layout(text, width)
if L.height > boxH: return (L, lo, overflowed = true)     # even the minimum overflows
best = L;  bestSize = lo
while hi - lo > 0.25:                                      # ε = 0.25 px
    mid = (lo + hi) / 2;  L = layout(text, width) at mid
    if L.height <= boxH: best = L; bestSize = mid; lo = mid
    else: hi = mid
return (best, bestSize, overflowed = false)""")
    c.definition("Proposition", "6.2", "Let Δ = s_{hi} − s_{lo} and ε = 0.25 px. (i) The search performs "
                 "one feasibility layout and exactly k = max(0, ⌈log_{2}(Δ / ε)⌉) bisection layouts. "
                 "(ii) If H(s_{lo}) ≤ |T|_{h}, the returned size is feasible. (iii) If moreover H is "
                 "non-decreasing on [s_{lo}, s_{hi}], the returned size is within ε of the largest "
                 "feasible size in the interval.")
    c.proof("(i) Each iteration halves hi − lo, starting from Δ, and the loop stops at the first k with "
            "Δ/2^{k} ≤ ε. (ii) The variable best is initialised to the feasible layout at s_{lo} and is "
            "replaced only by layouts that were tested and found feasible; the returned size is always "
            "that of best. (iii) The loop maintains the invariant that lo is feasible (or equals s_{lo}) "
            "and that hi is either infeasible or equals s_{hi}. If H is non-decreasing, every feasible "
            "size lies in [s_{lo}, hi], so the largest feasible size ŝ satisfies lo ≤ ŝ ≤ hi at "
            "termination, and hi − lo ≤ ε. The returned size equals lo, since best is updated exactly "
            "when lo is.")
    steps_rows = []
    for p in (8, 12, 24, 48, 96):
        lo = max(4.0, 0.45 * p)
        hi = max(lo, 1.15 * p)
        k = _bisect_steps(p)
        steps_rows.append([f"{p}", f"{lo:.2f}", f"{hi:.2f}", f"{hi - lo:.2f}", f"{k}", f"{k + 1}"])
    c.p("For p ≥ 8.9 px the interval length is Δ = 0.7p, so k = ⌈log_{2}(0.7p / ε)⌉; for p = 24 px this "
        "is 7, and the total is 8 layouts including the feasibility check ({T:bisect}, analytical). The "
        "cost grows only logarithmically with the text size. {F:fit} shows the search on a synthetic "
        "height function.")
    c.table("bisect", "Layouts needed by the size search (analytical, Proposition 6.2)",
            ["p (px)", "s_{lo}", "s_{hi}", "Δ", "Bisection layouts k", "Total layouts"], steps_rows,
            widths=[2.2, 2.4, 2.4, 2.4, 3.6, 3.3])
    c.figure("fit", "textfit", "Bisection on a synthetic layout-height function H(s) built from a greedy "
             "line-breaking model; numbers give the iteration order (synthetic illustration, not a "
             "measurement of the platform's layout engine).", width=15)
    c.p("Monotonicity of H is the delicate assumption. Layout height is a step function of s: it jumps "
        "whenever a larger size forces an extra line break, and is otherwise proportional to s. For "
        "greedy first-fit breaking it is non-decreasing. Optimal-fit breaking of the Knuth–Plass kind, "
        "which minimises a global badness rather than the number of lines, can occasionally choose more "
        "lines at a smaller size, so H may have small non-monotone excursions. Parts (i) and (ii) of the "
        "proposition do not depend on monotonicity: the search always terminates in the stated number of "
        "layouts and always returns a size that fits. Only the optimality claim (iii) may fail, and then "
        "only by returning a feasible size smaller than the largest one.")
    c.p("If even s_{lo} overflows, the minimum size is used and the fit is flagged as overflowed, on the "
        "reasoning that a slightly cropped translation is better than a blank region. The renderer does "
        "not install a clipping rectangle, so the overflowing lines extend beyond the bottom of T; with "
        "the debug option enabled, overflowed blocks are outlined in red and fitting blocks in blue. "
        "Layout uses the high-quality break strategy — without it, CJK text, which has no spaces, would "
        "never wrap — with hyphenation disabled, unit line-spacing multiplier and no extra font padding. "
        "For rotated blocks the canvas is rotated by θ about the centre of T and the text is laid out "
        "upright, so line breaking operates in the block's own frame; rotating individual glyph runs by "
        "hand would lose it.")

    c.h2("Comparison with Opaque Erasure and Inpainting", key="compare")
    c.p("{T:compare} contrasts the translucent scheme with the two alternatives, and {F:comp} applies "
        "opaque filling and translucent highlighting with and without the halo to a synthetic textured "
        "patch. The figure is an illustration of the compositing rules of this chapter on generated "
        "content; it is not an experimental result, and the user study of RQ5 is what will establish "
        "how the variants are perceived.")
    c.figure("comp", "compositing", "Synthetic illustration of the rendering variants on a generated "
             "textured patch with generated text: (a) original; (b) opaque fill in the estimated paper "
             "colour (α = 255); (c) translucent highlight, α = 150, without halo; (d) the same with the "
             "paper-coloured halo. Not an experimental result.", width=15.5)
    c.table("compare", "Properties of re-rendering strategies (analytical where marked; otherwise from "
                       "the literature and the implementation)",
            ["Property", "Opaque erase (α = 1)", "Translucent + halo (this work)", "Learned inpainting"],
            [["Texture retained inside region", "0 (analytical)", "1 − α ≈ 0.41 (analytical)",
              "Synthesised; model-dependent"],
             ["Ghost of original", "None", "(1 − α)|κ − π| outside halo", "None if successful"],
             ["Legibility of new text", "Full contrast", "Full contrast within 0.08 s (Cor. 6.1)",
              "Full contrast"],
             ["Additional model", "No", "No", "Yes (large)"],
             ["Cost", "One fill per block", "Path union, one blurred fill, two text passes",
              "Network inference on masked region"],
             ["Characteristic failure", "Flat \"sticker\" patch over texture", "Visible ghost behind short "
              "translations", "Hallucinated or smeared structure"]],
            widths=[3.8, 3.6, 4.6, 4.3])

    c.h2("Options and Output", key="render_opts")
    c.table("ropts", "Rendering options (`LayoutRenderer.Options`)",
            ["Field", "Default", "Effect"],
            [["`highlightAlpha`", "150", "0 disables the highlight; 255 reproduces the opaque erase"],
             ["`halo`", "true", "Paper-coloured outline behind glyphs"],
             ["`perLine`", "false", "Typeset each line in its own quadrilateral instead of reflowing paragraphs"],
             ["`debugBoxes`", "false", "Outline each target: blue if the text fits, red if it overflowed"]],
            widths=[3.4, 2.2, 10.7])
    c.p("For PDF input with PDF output, each rendered page is drawn into a `PdfDocument` page scaled from "
        "200-dpi pixels back to points by 72/200, so each output page keeps the physical size of its "
        "source page. DOCX and plain-text outputs need only text, so rendering is skipped for them.")

    c.h2("Limitations of the Rendering Model", key="render_limits")
    c.bullets([
        "The typeface, weight and letterforms of the original are not reproduced.",
        "A high-contrast original behind a much shorter translation remains visible as a ghost outside "
        "the halo band, with retained contrast 1 − α; this is the direct price of Proposition 6.1.",
        "The paragraph highlight covers the paragraph's rectangle, so the empty tails of short lines in "
        "ragged-right text are highlighted too.",
        "Block colours come from the paragraph's first line.",
        "For rotated paragraphs the layout rectangle's height is the axis-aligned height, which is "
        "generous and can enlarge the highlight.",
        "Vertical CJK text is recognised as rotated horizontal lines and typeset horizontally.",
        "Overflowing text at the minimum size is not clipped and can extend below its block.",
    ])
