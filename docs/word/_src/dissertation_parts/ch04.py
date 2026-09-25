"""Chapter 4: Library-free Text Detection and Recognition."""
import math


def build(c):
    c.chapter(4, "Library-free Text Detection and Recognition")
    c.p("This chapter develops the recognition half of the pipeline: preparing the detector input, "
        "turning the detector's probability map into oriented boxes without OpenCV or a polygon-clipping "
        "library, rectifying and orienting each line, recognising it, estimating its colours, arranging "
        "lines into reading order and paragraphs, and verifying the source language. The neural networks "
        "are the released PP-OCR models, used unchanged; everything described here is the algorithmic "
        "code around them, implemented in Java in the `ocr` and `engine` packages. The central results "
        "are Lemma 4.1, which shows that the convex-hull input can be reduced to row extremes without "
        "changing the hull, and Proposition 4.1, which shows that the closed-form rectangle unclip "
        "coincides with a round-join polygon offset followed by a minimum-area refit.")

    # ------------------------------------------------------------ input prep
    c.h2("Detector Input Preparation", key="detinput")
    c.p("The detector is fully convolutional, so it accepts any input size, but its cost grows with the "
        "number of pixels. The page is therefore scaled so that its long edge is at most L_{max}, the "
        "value behind the user-visible Image Quality setting (LOW 640, MEDIUM 960, HIGH 1280 pixels; the "
        "stored default is HIGH, and the engine clamps any value to the range 320–2048). Pages already "
        "smaller than L_{max} are not enlarged. Both sides are then rounded to a multiple of 32:")
    c.eq("ρ = min(1, L_{max} / max(W, H)),   w′ = 32 · max(1, round(ρW / 32)),   h′ = 32 · max(1, round(ρH / 32))",
         key="resize")
    c.p("with a floor of 32 pixels per side. The rounding matters because the detector's backbone has "
        "five stride-2 stages (a total stride of 32); a side that is not a multiple of 32 makes the "
        "upsampled output disagree with the input by a pixel or two and shifts every box. Note that "
        "rounding to the *nearest* multiple can exceed L_{max} by up to 16 pixels and changes the aspect "
        "ratio slightly; both effects are harmless because the map is scaled back with separate "
        "horizontal and vertical factors. The image is converted to an NCHW float tensor in RGB order "
        "normalised with ImageNet statistics (mean 0.485, 0.456, 0.406; standard deviation 0.229, 0.224, "
        "0.225). The recogniser, in contrast, normalises to [−1, 1]; confusing the two produces "
        "confident nonsense rather than an error, which is why the two normalisations live in separate, "
        "explicitly named functions of `ImageOps`.")
    c.p("The detector outputs a probability map P ∈ [0, 1]^{h×w}. Its tensor shape, not the size of the "
        "resized input, is taken as authoritative: the page-space scale factors are s_{x} = W / w and "
        "s_{y} = H / h, computed from the map itself. Because detection cost is roughly proportional to "
        "w′h′, moving from MEDIUM to HIGH multiplies the number of detector input pixels by about "
        "(1280/960)^{2} ≈ 1.78 and from LOW to HIGH by 4 (analytical, for pages larger than L_{max}); "
        "RQ4 measures the resulting latency.")

    # --------------------------------------------------------- DB overview
    c.h2("DB Post-processing without Libraries", key="dbpp")
    c.p("{F:db} illustrates the post-processing chain on a synthetic probability map, and {T:dbsteps} "
        "lists its steps with their defaults and the upstream operation each one replaces. The chain is "
        "implemented in `DbPostProcessor.extract` within a single Java class of under 400 lines.")
    c.figure("db", "db_steps", "DB post-processing on a synthetic probability map (illustration, not "
             "detector output): (a) map P; (b) 8-connected components of P ≥ 0.3, with a low-scoring "
             "component (red) and a speck (grey) rejected; (c) row extremes and convex hull; (d) "
             "minimum-area rectangle and unclipped quadrilateral.", width=16)
    c.table("dbsteps", "Steps of the library-free DB post-processing (defaults from `DbPostProcessor`)",
            ["Step", "Operation", "Default", "Replaces upstream"],
            [["1", "Binarise: keep pixels with P ≥ τ_{b}", "τ_{b} = 0.3", "Threshold"],
             ["2", "Iterative 8-connected flood fill with explicit stack", "—", "Contour extraction (border following)"],
             ["3", "Reject specks: |C| < a_{min}", "a_{min} = 12 px", "Size filter"],
             ["4", "Score over component pixels, keep S(C) ≥ τ_{s}", "τ_{s} = 0.6", "Box-mean score"],
             ["5", "Row-extreme outline R(C)", "—", "Contour points"],
             ["6", "Convex hull (Andrew's monotone chain)", "—", "Convex hull"],
             ["7", "Minimum-area rectangle over hull edges", "—", "Minimum-area rectangle"],
             ["8", "Reject slivers: min side < 3 px", "3 px", "Size filter"],
             ["9", "Closed-form unclip d = A r / L", "r = 1.6", "Polygon offset + refit"],
             ["10", "Order corners, clamp to map, scale to page", "—", "Box ordering"],
             ["—", "Safety valve: stop after N_{max} boxes", "N_{max} = 1000", "—"]],
            widths=[1.0, 7.3, 3.0, 5.0])

    c.h3("Binarisation and connected components")
    c.p("Pixels with P ≥ τ_{b} = 0.3 are foreground. Components are extracted by an iterative flood fill "
        "that scans seeds in raster order, pushes unvisited foreground neighbours onto an explicit integer "
        "stack, and collects each component's pixel indices in a growable integer array. Recursion is "
        "avoided deliberately: a full-page paragraph is routinely a single component of 10^{5} or more "
        "pixels, which would overflow the call stack. Eight-connectivity keeps diagonally touching "
        "strokes in one run. A boolean *visited* array of size hw guarantees that every pixel is pushed "
        "at most once, so the fill is O(hw) in time over the whole map, with O(hw) auxiliary memory for "
        "the visited flags and a stack that starts at min(hw, 2^{16}) entries and doubles on demand. "
        "Components with fewer than 12 pixels are discarded as specks. As a safety valve on pathological "
        "maps, extraction stops after 1000 boxes.")

    c.h3("Component-restricted confidence score", key="score")
    c.p("Each surviving component *C* is scored by the mean probability over its own pixels:")
    c.eq("S(C) = (1 / |C|) · Σ_{p ∈ C} P(p),        keep C  ⇔  S(C) ≥ τ_{s} = 0.6", key="score")
    c.p("The project documentation and the companion manuscript contrast this with a reference score "
        "that averages *P* over the component's axis-aligned bounding box. To see why the distinction "
        "matters, consider a straight text line of length ℓ and thickness *t* at angle θ whose pixels all "
        "have probability *q*, on a background of probability approximately zero. Its axis-aligned "
        "bounding box has area (ℓ cos θ + t sin θ)(ℓ sin θ + t cos θ), so the box mean is")
    c.eq("S_{box}(θ) ≈ q · ℓt / [(ℓ cos θ + t sin θ)(ℓ sin θ + t cos θ)],        S(C) = q", key="boxbias")
    ratio_rows = []
    for asp in (5, 10, 20):
        row = [f"ℓ/t = {asp}"]
        for deg in (0, 5, 20, 45):
            th = math.radians(deg)
            box = (asp * math.cos(th) + math.sin(th)) * (asp * math.sin(th) + math.cos(th))
            row.append(f"{asp / box:.2f}")
        ratio_rows.append(row)
    c.p("For θ = 0 the two scores agree; as θ grows the box mean falls quickly because the box fills "
        "with background. {T:boxbias} evaluates the factor S_{box}/S(C) for a few aspect ratios and "
        "angles. For a 10:1 line at 20°, a box-averaged score of a line whose pixels all have "
        "probability 1 would be about 0.24 — far below τ_{s} — so a pure axis-aligned box mean would "
        "discard it. The component mean is invariant to rotation by construction.")
    c.table("boxbias", "Analytical attenuation factor S_{box}/S(C) of an axis-aligned box mean for a "
                       "uniform line on a zero background (Equation {E:boxbias}; analytical, not measured)",
            ["Aspect ratio", "θ = 0°", "θ = 5°", "θ = 20°", "θ = 45°"], ratio_rows,
            widths=[3.3, 3.2, 3.2, 3.2, 3.2])
    c.p("Two qualifications keep this analysis honest. First, the author's reading of the upstream "
        "implementation is that its fast scoring mode masks the minimum-area (rotated) rectangle inside "
        "the bounding box before averaging, in which case the real bias of the reference is much smaller "
        "than {T:boxbias} suggests; the table is an upper bound that applies only to an unmasked box "
        "mean. Second, averaging over the component alone has its own bias: a component is by definition "
        "the set of pixels above τ_{b}, so S(C) ≥ τ_{b} always, and the score measures confidence "
        "*within* the detected region rather than contrast against its surroundings. Whether the "
        "component mean helps, hurts or is neutral relative to the reference on real data is therefore "
        "an empirical question, which is exactly the box-mean versus component-mean ablation of RQ1, "
        "stratified by text angle ({S:m_rq1}).")

    # --------------------------------------------------------------- hull
    c.h3("Exact hull reduction to row extremes", key="rowhull")
    c.p("The minimum-area rectangle of a component depends only on its convex hull. Computing the hull of "
        "all pixels of a large component would dominate the post-processing time, so the point set is "
        "reduced first.")
    c.definition("Definition", "4.1", "Let C ⊂ ℤ^{2} be finite. For each row y with C_{y} = {(x, y) ∈ C} "
                 "non-empty, let l_{y} and r_{y} be the elements of C_{y} with minimum and maximum x. The "
                 "row-extreme set of C is R(C) = ∪_{y} {l_{y}, r_{y}}.")
    c.definition("Lemma", "4.1", "For every finite C ⊂ ℤ^{2}, conv(R(C)) = conv(C).")
    c.proof("Since R(C) ⊆ C, monotonicity of the convex hull gives conv(R(C)) ⊆ conv(C). For the reverse "
            "inclusion, recall two standard facts about a finite point set [@deberg2008cg]: conv(C) is a "
            "convex polygon (possibly degenerate) whose vertices — its extreme points — all belong to C; "
            "and conv(C) is the convex hull of its extreme points. It therefore suffices to show that "
            "every extreme point v of conv(C) lies in R(C). Suppose v = (v_{x}, y₀) ∈ C is extreme but "
            "not a row extreme. Then v ≠ l_{y₀} and v ≠ r_{y₀}, so there exist a = l_{y₀} and "
            "b = r_{y₀} in C with a_{x} < v_{x} < b_{x} and a_{y} = b_{y} = y₀. Setting "
            "λ = (b_{x} − v_{x}) / (b_{x} − a_{x}) ∈ (0, 1) gives v = λa + (1 − λ)b, a convex combination "
            "of two points of conv(C) distinct from v, which contradicts the extremality of v. Hence "
            "every extreme point lies in R(C), and conv(C) = conv(ext conv(C)) ⊆ conv(R(C)).")
    c.p("Three remarks complete the picture. (i) The reduced set has at most 2h_{C} points, where h_{C} "
        "is the number of rows the component spans; a row containing a single pixel contributes it once, "
        "as in the implementation, which adds the right extreme only when it differs from the left. "
        "(ii) Nothing in the proof depends on rows specifically: column extremes are equally exact, and "
        "for vertical text, whose components are tall and narrow, using columns would give at most "
        "2w_{C} points instead; choosing the smaller of the two is a free optimisation not currently "
        "implemented. (iii) The reduction also removes the need for contour tracing altogether: the row "
        "extremes are collected in one pass over the component's pixel list, O(|C|) time and O(h_{C}) "
        "memory.")
    c.figure("hull", "hull", "Geometry of the hull reduction and the minimum-area rectangle on a synthetic "
             "component: (a) interior points of a row are strict convex combinations of that row's "
             "extremes, so only row extremes can be hull vertices; (b) one candidate rectangle per hull "
             "edge, with the minimum-area choice highlighted (schematic).", width=16)

    c.h3("Convex hull by monotone chain")
    c.p("The hull of R(C) is computed with Andrew's monotone chain [@andrew1979hull]. The m ≤ 2h_{C} "
        "points are sorted lexicographically by (x, y); the lower hull is built by scanning left to right "
        "and popping the last point while the last two points and the new one fail to make a strict "
        "counter-clockwise turn; the upper hull is built by the symmetric right-to-left scan. The turn "
        "test is the sign of the cross product")
    c.eq("cross(o, a, b) = (a_{x} − o_{x})(b_{y} − o_{y}) − (a_{y} − o_{y})(b_{x} − o_{x})", key="cross")
    c.p("evaluated in 64-bit integer arithmetic, so it is exact for any pixel coordinates. Popping on "
        "cross ≤ 0 discards collinear points, which does not change the hull. The cost is O(m log m) for "
        "the sort and O(m) for the scans, i.e. O(h_{C} log h_{C}) per component — independent of the "
        "component's area, which is the purpose of Lemma 4.1.")

    c.h3("Minimum-area rectangle")
    c.p("Freeman and Shapira [@freeman1975rect] proved that some minimum-area rectangle enclosing a "
        "convex polygon has a side collinear with one of the polygon's edges. The implementation uses "
        "this directly: for each hull edge with unit direction u = e / ‖e‖ and normal v = (−u_{y}, u_{x}), "
        "it projects every hull vertex p onto both axes and takes the extents")
    c.eq("[u_{min}, u_{max}] = [min_{p} p·u, max_{p} p·u],    [v_{min}, v_{max}] = [min_{p} p·v, max_{p} p·v],    "
         "A(u) = (u_{max} − u_{min})(v_{max} − v_{min})", key="proj")
    c.p("and keeps the edge with the smallest A(u). The result is stored as a centre c, half-extents "
        "(a, b) along (u, v), and the unit axis u, which directly gives the baseline angle the renderer "
        "needs. With k hull vertices this exhaustive enumeration costs O(k^{2}); the rotating-calipers "
        "technique [@toussaint1983calipers] would reduce it to O(k) by advancing four support indices "
        "monotonically around the hull. The quadratic version is kept because k is small in practice — "
        "hulls of text components are close to rectangles, and collinear points have already been "
        "removed — and because it is simpler to verify. The theorem guarantees that the enumeration is "
        "exhaustive, so the result is an exact minimum-area rectangle, not an approximation.")

    c.h3("Closed-form unclip", key="unclip")
    c.p("DB trains the network to predict text regions shrunk by an offset D = A(1 − r_{s}^{2})/L "
        "[@liao2020db]. At inference the region is dilated back by an offset proportional to its area "
        "over its perimeter, d = A r / L, with unclip ratio r = 1.6; upstream this is a general polygon "
        "offset computed by a clipping library [@vatti1992clip]. For a w × h rectangle, A = wh and "
        "L = 2(w + h), which gives the closed form")
    c.eq("d = w h r / (2(w + h)),        (a, b) ← (a + d, b + d)", key="unclip_rect")
    c.p("so the unclipped rectangle has size (w + 2d) × (h + 2d) with unchanged centre and axis. "
        "{F:unclip} plots d. For a long line (w ≫ h) the offset approaches r h / 2 = 0.8 h, so each side "
        "grows by 0.8 times the shrunk height — consistent with the purpose of the unclip, which is to "
        "recover ascenders, descenders and the end glyphs that the shrunk prediction clips.")
    c.figure("unclip", "unclip", "Closed-form unclip offset as a function of rectangle width for several "
             "heights (analytical).", width=14)
    c.p("A natural question is whether replacing the polygon offset by Equation {E:unclip_rect} changes "
        "the final box. The reference implementation, as the author reads it, offsets the four corners of "
        "the minimum-area rectangle with rounded joins and then fits a minimum-area rectangle to the "
        "offset polygon. The following result shows that, under that reading, the two procedures agree "
        "exactly (up to the discretisation of arcs by the clipping library).")
    c.definition("Proposition", "4.1", "Let K be a w × h rectangle with axis u, and let K_{d} = K ⊕ B_{d} "
                 "be its offset by distance d > 0 with round joins (the Minkowski sum with a disc of radius "
                 "d). Then a minimum-area rectangle enclosing K_{d} is the rectangle with axis u, the same "
                 "centre as K, and size (w + 2d) × (h + 2d).")
    c.proof("The width of K in direction φ (measured from u) is ω_{K}(φ) = w|cos φ| + h|sin φ|, and "
            "Minkowski addition of a disc adds 2d to every width: ω_{K_d}(φ) = ω_{K}(φ) + 2d. The enclosing "
            "rectangle of K_{d} with sides along φ and φ + 90° has area f(φ) = (ω_{K}(φ) + 2d)(ω_{K}(φ + 90°) + 2d). "
            "By symmetry it suffices to take φ ∈ [0, 90°] and write c = cos φ, s = sin φ ≥ 0. Then "
            "f(φ) = (wc + hs)(ws + hc) + 2d[(wc + hs) + (ws + hc)] + 4d^{2}. The first product equals "
            "wh(c^{2} + s^{2}) + (w^{2} + h^{2})cs = wh + (w^{2} + h^{2})cs ≥ wh, and the bracket equals "
            "(w + h)(c + s) ≥ w + h because c + s ≥ 1 on [0, 90°]. Hence f(φ) ≥ wh + 2d(w + h) + 4d^{2} = "
            "(w + 2d)(h + 2d) = f(0). The rectangle at φ = 0 encloses K_{d} (its extents are those of K "
            "plus d on each side) and attains the minimum.")
    c.p("With square joins (a mitred offset) the offset polygon *is* the (w + 2d) × (h + 2d) rectangle, "
        "so the same conclusion holds trivially. Where the reference unclips the raw contour instead of "
        "its rectangle, the two procedures can differ for strongly non-convex components; the "
        "polygon-versus-rectangle unclip ablation of RQ1 quantifies that case. Rectangles with a side "
        "shorter than 3 pixels (before unclipping) are rejected as slivers.")

    c.h3("Corner ordering, clamping and scaling")
    c.p("The four corners c ± (a + d)u ± (b + d)v are ordered clockwise from the top-left using sums and "
        "differences of coordinates: the top-left corner minimises x + y, the bottom-right maximises it, "
        "the top-right maximises x − y and the bottom-left minimises it. If a degenerate box maps two "
        "roles onto one corner, the raw order is kept rather than emitting a quadrilateral with "
        "duplicated vertices. Corners are clamped to the map and scaled by (s_{x}, s_{y}) to page "
        "pixels. The result is a `Quad`.")

    c.h3("Complexity of the whole chain")
    c.p("{T:complexity} collects the costs. The dominant term for typical pages is the linear flood fill; "
        "Lemma 4.1 ensures that the geometric work per component depends on its height, not its area.")
    c.table("complexity", "Asymptotic cost of the DB post-processing (analytical; h × w map, component C "
                          "spanning h_{C} rows with k_{C} hull vertices)",
            ["Step", "Time", "Memory"],
            [["Flood fill (all components)", "O(hw)", "O(hw) visited flags + stack"],
             ["Score, bounds, row extremes", "O(|C|) per component; O(hw) total", "O(h_{C})"],
             ["Monotone-chain hull", "O(h_{C} log h_{C})", "O(h_{C})"],
             ["Minimum-area rectangle", "O(k_{C}^{2}) (O(k_{C}) with rotating calipers)", "O(1)"],
             ["Unclip, ordering, scaling", "O(1)", "O(1)"],
             ["**Total**", "**O(hw + Σ_{C} (h_{C} log h_{C} + k_{C}^{2}))**", "**O(hw)**"]],
            widths=[5.5, 6.8, 4.0])

    # ----------------------------------------------------- crop + orientation
    c.h2("Rectification and Orientation", key="crop")
    c.p("Each quadrilateral q = (p_{0}, p_{1}, p_{2}, p_{3}) is mapped onto an upright crop of size "
        "w_{q} × h_{q}, where w_{q} and h_{q} are the rounded mean lengths of opposite edges, capped at "
        "4096 pixels per side to guard against pathological detections. The map is the planar "
        "homography H determined by the four correspondences p_{0} ↦ (0, 0), p_{1} ↦ (w_{q}, 0), "
        "p_{2} ↦ (w_{q}, h_{q}), p_{3} ↦ (0, h_{q}) [@hartley2004mvg], computed by the platform's "
        "`Matrix.setPolyToPoly`:")
    c.eq("[x′, y′, z′]^{T} = H [x, y, 1]^{T},        (u, v) = (x′ / z′, y′ / z′)", key="homography")
    c.p("Because the map is projective rather than a rotation, mild keystone distortion from photographing "
        "a page at an angle is corrected at the same time. Detected boxes are rectangles, so the "
        "homography is in practice a similarity; the projective generality costs nothing. If the corners "
        "are collinear and no homography exists, the crop falls back to the axis-aligned bounds. The crop "
        "is drawn with bilinear filtering onto a white background.")
    c.p("An orientation classifier (the PP-OCR v2.0 angle classifier, input 48 × 192, optional) decides "
        "for each crop whether it is upside down. The crop is rotated by 180° only when the classifier's "
        "probability for the rotated class exceeds 0.9. The asymmetry is intentional and can be "
        "justified as a cost-sensitive decision. Let p be the classifier's probability that the crop is "
        "rotated, C_{w} the cost of wrongly flipping a correct crop, and C_{m} the cost of missing a "
        "rotated one. Flipping minimises expected cost when p C_{m} > (1 − p) C_{w}, i.e.")
    c.eq("flip  ⇔  p > C_{w} / (C_{w} + C_{m})", key="flip")
    c.p("A threshold of 0.9 therefore corresponds to treating a wrong flip as nine times as costly as a "
        "missed one (analytical). The asymmetry is plausible: a wrongly flipped crop is recognised as "
        "garbage and cannot be recovered downstream, whereas a missed flip on an upside-down crop merely "
        "lowers recognition accuracy on text that was already unusual. If the classifier model is absent "
        "the stage is skipped with a log message, and if classification fails for any crop the remaining "
        "crops keep their orientation. RQ2 measures recognition with and without this stage.")

    # ------------------------------------------------------------ recognition
    c.h2("Batched Recognition", key="rec")
    c.p("Crops are resized to a height of 48 pixels, preserving aspect ratio, and normalised to [−1, 1]. "
        "They are processed in batches of six. Within a batch all tensors must share a width, so shorter "
        "crops are right-padded; the padded width of a batch is")
    c.eq("W_{pad} = clamp(8 · ⌈48 · ρ_{max} / 8⌉, 16, 1200)", key="padw")
    c.p("where ρ_{max} is the largest width-to-height ratio in the batch. Crops wider than W_{pad} after "
        "resizing — which happens only when a line's aspect ratio exceeds 1200/48 = 25 — are squeezed "
        "horizontally to fit rather than padded. The padding value is zero *after* normalisation, which "
        "corresponds to mid-grey in the original intensity scale; CTC recognisers generally emit blanks "
        "over such featureless regions, but a model trained with a different padding convention could "
        "behave differently, which is one reason the evaluation compares batched and unbatched "
        "recognition implicitly through the RQ2 protocol.")
    c.p("To minimise padding, crops are first sorted by aspect ratio and then batched in order "
        "({F:batching}). The following lemma shows that this is optimal for the padded tensor area when "
        "the number of crops is a multiple of the batch size.")
    c.figure("batching", "batching", "Padding waste for recognition batches of six in arrival order (a) "
             "and after sorting by aspect ratio (b), on randomly generated aspect ratios (synthetic "
             "illustration).", width=16)
    c.definition("Lemma", "4.2", "Let n = kb crops with padded widths ω_{1} ≥ ω_{2} ≥ … ≥ ω_{n} be "
                 "partitioned into k batches of size b, and let the cost of a partition be "
                 "Σ_{batches G} b · max_{i∈G} ω_{i}. Sorting and cutting into consecutive groups minimises "
                 "the cost.")
    c.proof("Order the batch maxima of any partition decreasingly as M_{1} ≥ … ≥ M_{k}. The "
            "(j − 1)b + 1 widest crops ω_{1}, …, ω_{(j−1)b+1} cannot fit in j − 1 batches of size b, so "
            "they meet at least j distinct batches, each of which therefore has maximum at least "
            "ω_{(j−1)b+1}. Hence M_{j} ≥ ω_{(j−1)b+1} for every j, and the cost is at least "
            "b Σ_{j} ω_{(j−1)b+1}. Sorted consecutive batching attains this bound with equality.")
    c.p("When n is not a multiple of b the last, partial batch receives the narrowest crops, which is "
        "also the cheapest place for it; the lemma's bound argument extends with minor bookkeeping. "
        "Sorting costs O(n log n) for n lines, negligible beside the network.")

    c.h3("Greedy CTC decoding")
    c.p("For each crop the recogniser outputs, per time step t = 1…T, a probability vector over C "
        "classes (the exported PP-OCR graphs include the softmax). Greedy CTC decoding "
        "[@graves2006ctc] takes the arg-max class at each step, collapses runs of identical classes and "
        "removes the blank. With k_{t} = argmax_{j} y_{t,j}, the output string and line confidence are")
    c.eq("x = 𝓑(k_{1} … k_{T}),        c = (1 / |𝒦|) Σ_{t ∈ 𝒦} max_{j} y_{t,j}", key="ctc")
    c.p("where 𝓑 collapses repeats and then drops blanks, and 𝒦 is the set of time steps whose class "
        "was emitted (the first step of each non-blank run). Lines whose trimmed text is empty or whose "
        "confidence is below 0.5 are discarded. Greedy decoding returns the most probable *path*, not "
        "the most probable *string*, but for CRNN-style recognisers with peaky output distributions the "
        "difference is usually small, and beam search over CTC would add cost to every line.")
    c.h3("Dictionary alignment")
    c.p("PP-OCR dictionary files list only the glyphs. The label set the network predicts is that list "
        "wrapped in two extras: the CTC blank at index 0 and, for models trained with a space class, a "
        "space appended at the end. Class j ≥ 1 therefore maps to glyph j − 1, and the class count must "
        "satisfy")
    c.eq("C ∈ { |G| + 1,  |G| + 2 }", key="dict")
    c.p("where |G| is the number of glyphs after trailing empty lines (an exporter artefact) are "
        "removed. An off-by-one here does not throw; it shifts every character of every result. The "
        "engine therefore reads C from the loaded graph's output shape, rejects a dynamic class count "
        "with an explicit error, and `CharDict` refuses a dictionary that satisfies neither case of "
        "Equation {E:dict}. Four unit tests exercise exactly these rules (Chapter 7).")

    # ---------------------------------------------------------------- colour
    c.h2("Ink and Paper Colour Estimation", key="colour")
    c.p("The renderer needs, for every line, the colour of the original glyphs (ink κ) and of their "
        "background (paper π). `ImageOps.sampleColors` estimates both in one pass over a subsampled "
        "crop. With a sampling step δ = max(1, ⌊√(w_{q} h_{q} / 4096)⌋) about 4096 pixels are visited. "
        "Each pixel's luminance is computed with the Rec. 601 weights [@bt601] in integer arithmetic,")
    c.eq("Y = (299 R + 587 G + 114 B) / 1000", key="luma")
    c.p("and the pixels are split at the mid-range Y_{mid} = (Y_{min} + Y_{max}) / 2 into a dark and a "
        "light class, each averaged in RGB. The class with *fewer* pixels is taken as ink and the other "
        "as paper; ties go to dark ink on light paper. If the crop has no luminance range at all, black "
        "on white is returned. The minority rule handles dark-on-light and light-on-dark text alike, "
        "because in a tight text box the glyph strokes occupy less area than the background.")
    c.p("The estimator can be read as a single step of two-cluster k-means on luminance, initialised at "
        "the extremes; it is cheaper and less stable than Otsu thresholding but adequate for the "
        "purpose, since the renderer uses the colours to blend and to draw, not to segment. Its failure "
        "modes follow from its assumptions: very bold, large text in a tight box can make glyphs the "
        "majority and swap ink and paper; a strong illumination gradient across the crop splits the "
        "paper into both classes; and a single specular highlight stretches Y_{max}. Paragraph blocks "
        "take their colours from the first line of the paragraph, so a heading-like first line with "
        "unusual colours would colour the whole block.")

    # ---------------------------------------------------------------- layout
    c.h2("Reading Order and Paragraph Grouping", key="layout")
    c.p("Detection returns boxes in the raster order of their seed pixels, which is not reading order, "
        "and it has no notion of a paragraph. Both matter downstream: the translator needs whole "
        "sentences, and the renderer needs to know across which boxes it may reflow text. `LineGrouper` "
        "first sorts lines top to bottom, treating two lines as the same row when the vertical centres "
        "of their bounding boxes differ by less than 0.6 times the smaller box height, and orders lines "
        "within a row left to right.")
    c.p("A comparator with a tolerance is not transitive: three lines whose centres are successively "
        "within tolerance of each other but not end to end can be ordered inconsistently, and Java's "
        "sort is entitled to reject such a comparator at run time. The situation requires unusual "
        "geometry (a staircase of small vertical offsets across one row), but a robust alternative — "
        "clustering centres into rows first and then sorting rows and lines within rows — would remove "
        "the possibility entirely and is recorded as a limitation.")
    c.p("Lines are then grouped greedily: a line n continues the paragraph of its predecessor m if and "
        "only if all of the following hold ({F:paragraph}):")
    c.eq("max(h_{m}, h_{n}) / min(h_{m}, h_{n}) ≤ 1.7,    |θ_{m} − θ_{n}| ≤ 8°", key="para1")
    c.eq("top_{n} − bot_{m} ≤ 1.6 · max(h_{m}, h_{n}),    cy_{n} ≥ cy_{m},    overlap_{x}(m, n) / min(w_{m}, w_{n}) ≥ 0.25",
         key="para2")
    c.figure("paragraph", "paragraph", "Paragraph-continuation conditions between consecutive lines "
             "(schematic).", width=14.5)
    c.p("Heights h and angles θ are those of the quadrilaterals; vertical positions, overlap and widths "
        "are taken from axis-aligned bounds. The conditions encode typographic regularities: the height "
        "ratio separates headings from body text, the angle condition separates rotated labels, the gap "
        "condition separates blocks, and the overlap and centre-order conditions separate columns — a "
        "line that starts above its predecessor is the top of a new column, not a wrap. Negative gaps "
        "(overlapping boxes, common after unclipping) are allowed.")
    c.p("Paragraph source text is assembled by joining lines with a space, except when the characters on "
        "both sides of the join are CJK; in CJK text a space at that position would be a real character "
        "rather than a line-wrap artefact. The CJK test covers the CJK unified ideographs (and extension "
        "A), CJK symbols and punctuation, Hiragana, Katakana, Hangul syllables and Jamo, and half-width "
        "and full-width forms. Including Hangul in this test is correct for Chinese and Japanese "
        "conventions but not for Korean, which separates words with spaces; a Korean line that wraps "
        "between two words is therefore joined without a space. Since Korean is hidden in the deployed "
        "interface (Chapter 7) the issue does not arise for users today, but it would need attention "
        "before Korean is enabled.")

    # --------------------------------------------------------------- script
    c.h2("Script-based Source Verification", key="lid")
    c.p("A recogniser for the wrong script produces confident garbage rather than an error. The pipeline "
        "therefore checks the first recognition pass with a script test. Let n_{hg}, n_{kn}, n_{han} and "
        "n_{lat} count the Hangul (syllables, Jamo, compatibility Jamo), Kana (Hiragana, Katakana), Han "
        "(CJK unified ideographs and extension A) and Latin letters (Basic Latin and Latin-1 Supplement) "
        "in the recognised text, ignoring whitespace and digits, and let N be their sum. Then")
    c.eq("ℓ̂ = KO if n_{hg}/N > 0.08;  else JA if n_{kn}/N > 0.08;  else ZH if n_{han} > 0 ∧ n_{han} ≥ n_{lat};  "
         "else EN if n_{lat} > 0;  else ℓ_{s}", key="lid")
    c.p("If N = 0 the configured source ℓ_{s} is kept. Hangul and Kana are exclusive to Korean and "
        "Japanese respectively, so a small share settles the question; the genuine ambiguity is Han, "
        "shared by Chinese and Japanese, which is resolved by the presence of Kana — Japanese prose "
        "almost always contains some. The known failure mode is Japanese written only in Kanji (a sign "
        "reading 出口, \"exit\", for example), which is classified as Chinese; a character-bigram "
        "language identifier is the natural remedy.")
    c.p("If ℓ̂ differs from ℓ_{s} and is user-facing, the page is recognised again with the head for ℓ̂ — "
        "detection runs again as well, which is the cost of auto-detection — and the second result is "
        "kept only if it is non-empty. The test is run on text produced by the *wrong* recogniser, which "
        "is less paradoxical than it appears: recognisers for Latin script emit Latin letters on CJK "
        "input and vice versa, so the test mainly detects mismatches between the user's setting and the "
        "page, which is its purpose. A detected language that is implemented but hidden from the user "
        "interface is ignored, so a hidden language can never become the source behind the user's back.")
    c.table("lidcases", "Behaviour of the script test on representative inputs (from the unit tests of "
                        "`ScriptDetector`)",
            ["Input characteristic", "Result", "Unit test"],
            [["Hangul text", "KO", "`hangulIsKorean`"], ["Kana text", "JA", "`kanaIsJapanese`"],
             ["Han without Kana", "ZH", "`hanWithoutKanaIsChinese`"], ["Latin letters", "EN", "`latinIsEnglish`"],
             ["Han mixed with Kana", "JA", "`mixedHanAndKanaIsJapanese`"],
             ["Small Hangul share above 8%", "KO", "`smallHangulShareStillWins`"],
             ["Digits and punctuation only", "fallback ℓ_{s}", "`digitsAndPunctuationFallBack`"],
             ["Null or empty", "fallback ℓ_{s}", "`nullAndEmptyFallBack`"],
             ["Kanji-only Japanese", "ZH (known failure)", "`pureKanjiJapaneseIsReportedAsChinese`"]],
            widths=[6.0, 3.5, 6.8])
