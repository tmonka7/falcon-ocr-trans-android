"""Chapter 9: Results and Discussion (result cells are placeholders by design)."""

T = "[TBD]"


def _pending(c):
    c.note("Values pending execution of the protocol in Chapter 8. Every cell marked [TBD] is to be "
           "filled from measured data; no value in this table is a measurement.", label="Status")


def build(c):
    c.chapter(9, "Results and Discussion")
    c.p("This chapter contains the result tables for every research question. In accordance with the "
        "reporting rule stated in Chapter 1, **all experimental values are pending execution of the "
        "protocol in Chapter 8** and appear as [TBD]. For each table the text states what the table will "
        "show, which hypothesis of {T:hyp} it tests, and what outcome would confirm or refute it. "
        "Columns that contain analytical values derived from formulas in earlier chapters are labelled "
        "as such. The chapter closes with a discussion of the trade-offs that can be anticipated from "
        "the analysis alone, and of the limitations of the system.")

    # ------------------------------------------------------------------ RQ1
    c.h2("RQ1: Faithfulness of Library-free Detection Post-processing", key="r_rq1")
    c.p("{T:det} will report H-mean at IoU 0.5 for the reference post-processing and for the "
        "library-free implementation with each of its two deviations switched on separately. It tests "
        "H1a (equivalence of the deployed configuration, last row, with the reference, first row, "
        "within the pre-specified margin) and H1c (identity of the two unclip variants, rows two and "
        "four versus three and five). Proposition 4.1 predicts that the rectangle and round-join "
        "polygon unclips coincide whenever the reference unclips the minimum-area rectangle; any "
        "difference between those rows would therefore point to contour-mode unclipping or to "
        "discretisation effects.")
    _pending(c)
    rows = [["Reference (OpenCV + polygon clipping, box-mean score)"] + [T] * 4,
            ["Library-free, box-mean score, polygon unclip"] + [T] * 4,
            ["Library-free, box-mean score, rectangle unclip"] + [T] * 4,
            ["Library-free, component-mean score, polygon unclip"] + [T] * 4,
            ["Library-free, component-mean score, rectangle unclip (deployed)"] + [T] * 4]
    c.table("det", "Detection H-mean (%) at IoU 0.5 by post-processing variant (pending)",
            ["Post-processing", "IC15", "MLT-zh", "MLT-ja", "MLT-ko"], rows, widths=[7.9, 2.1, 2.1, 2.1, 2.1])
    c.p("{T:detangle} breaks precision and recall down by the angle of the ground-truth text and tests "
        "H1b. The analysis of Section {S:score} predicts that any advantage of component-mean scoring "
        "should grow with angle and vanish for near-horizontal text; a recall gain concentrated in the "
        "> 20° stratum with unchanged precision below 5° would confirm H1b, while no difference in any "
        "stratum would indicate that the reference's masked box score already avoids the bias.")
    _pending(c)
    rows = []
    for stratum in ("< 5°", "5–20°", "> 20°"):
        for score in ("box mean", "component mean"):
            rows.append([stratum, score, T, T, T, T])
    c.table("detangle", "Detection precision, recall and H-mean (%) by text angle and score (pending)",
            ["Angle stratum", "Score", "P", "R", "H-mean", "Boxes (n)"], rows,
            widths=[2.8, 3.6, 2.3, 2.3, 2.6, 2.7])
    c.table("pptime", "Post-processing time per image on the workstation (ms, median [p90]; pending)",
            ["Implementation", "IC15", "MLT-zh", "MLT-ja", "MLT-ko"],
            [["Reference (Python + OpenCV + clipping)", T, T, T, T],
             ["Library-free (Java)", T, T, T, T]], widths=[6.3, 2.5, 2.5, 2.5, 2.5])
    c.p("{T:pptime} is a secondary outcome. It will show whether the library-free implementation is "
        "competitive in speed on a common platform; the complexity analysis of {T:complexity} predicts "
        "that both are dominated by a linear pass over the map.")

    # ------------------------------------------------------------------ RQ2
    c.h2("RQ2: Recognition Accuracy", key="r_rq2")
    c.p("{T:rec} will report word accuracy and 1 − NED per script on ground-truth crops, with the "
        "orientation classifier off and on, both for crops as annotated and for the same crops rotated "
        "by 180°. It tests H2: the classifier should raise accuracy substantially on rotated crops "
        "(where, without it, the recogniser reads upside-down text) and leave upright crops essentially "
        "unchanged, which is what the conservative threshold of 0.9 is designed to achieve.")
    _pending(c)
    rows = []
    for script in ("English (IC15)", "Chinese (MLT)", "Japanese (MLT)", "Korean (MLT)"):
        rows.append([script, T, T, T, T, T, T, T, T])
    c.table("rec", "Recognition word accuracy / 1 − NED (%) by script and orientation handling (pending)",
            ["Script", "Upright, cls off: acc", "1−NED", "Upright, cls on: acc", "1−NED",
             "Rotated, cls off: acc", "1−NED", "Rotated, cls on: acc", "1−NED"],
            rows, widths=[2.6, 1.8, 1.4, 1.8, 1.4, 1.8, 1.4, 1.8, 1.4], font_size=8)
    c.p("{T:scriptcheck} will report the effect of script-based source verification on the in-house set "
        "when the configured source language is deliberately wrong, including the rate at which the "
        "known failure mode (Kanji-only Japanese classified as Chinese) occurs and the added latency of "
        "the second recognition pass.")
    _pending(c)
    c.table("scriptcheck", "Script-based source verification with a misconfigured source (pending)",
            ["Configured → true source", "Pages", "Correctly re-recognised (%)", "End-to-end word acc. (%)",
             "Added latency (ms)"],
            [["EN → JA", T, T, T, T], ["EN → ZH", T, T, T, T], ["JA → ZH", T, T, T, T],
             ["ZH → JA", T, T, T, T]], widths=[3.9, 1.8, 3.7, 3.7, 3.2])

    # ------------------------------------------------------------------ RQ3
    c.h2("RQ3: Translation Quality", key="r_rq3")
    c.p("{T:mt} will report BLEU, chrF and COMET for all twelve directions in the deployed configuration "
        "(int8, greedy). It will show the level of quality the device offers per direction and, by "
        "comparing pivoted rows (†) with the direct rows of the same target language, the cost of "
        "pivoting. The comparison with a direct model is made formally in {T:pivotref}.")
    _pending(c)
    rows = [["en → ko / ko → en", T, T, T, T, T, T], ["en → ja / ja → en", T, T, T, T, T, T],
            ["en → zh / zh → en", T, T, T, T, T, T], ["ko → ja† / ja → ko†", T, T, T, T, T, T],
            ["ko → zh† / zh → ko†", T, T, T, T, T, T], ["ja → zh† / zh → ja†", T, T, T, T, T, T]]
    c.table("mt", "Translation quality on FLORES-200 devtest, int8 and greedy decoding; † pivoted through "
                  "English (pending)",
            ["Directions (a / b)", "BLEU a", "BLEU b", "chrF a", "chrF b", "COMET a", "COMET b"], rows,
            widths=[3.9, 2.0, 2.0, 2.0, 2.0, 2.2, 2.2])
    c.p("{T:quant} tests H3a and H3b. It will show the change in chrF and COMET when int8 weights "
        "replace fp32 and when beam search (k = 4) replaces greedy decoding, together with the latency "
        "cost from RQ4. H3a is confirmed if the int8 differences fall inside the equivalence margin for "
        "all directions; H3b concerns whether the beam gain justifies an approximately k-fold decoder "
        "cost for OCR-length inputs.")
    _pending(c)
    rows = []
    for d in ("en → ja", "ja → en", "en → zh", "zh → en", "en → ko", "ko → en"):
        rows.append([d, T, T, T, T, T])
    c.table("quant", "Effect of quantisation and beam search (differences in points; pending)",
            ["Direction", "ΔchrF int8 − fp32", "ΔCOMET int8 − fp32", "ΔchrF beam4 − greedy",
             "ΔCOMET beam4 − greedy", "Decode time ratio beam4/greedy"], rows,
            widths=[2.4, 2.6, 2.8, 2.8, 2.9, 2.8], font_size=8.5)
    c.p("{T:pivotref} tests H3c by comparing the six pivoted directions with direct translation by "
        "NLLB-200-distilled-600M, which covers these pairs but does not fit the device budget. It will "
        "show how much quality the English pivot costs relative to a direct multilingual model. The "
        "tokeniser-fidelity check — the number of FLORES source sentences on which the Java "
        "SentencePiece segmentation differs from the reference library — is reported in the last "
        "column and is expected to be zero.")
    _pending(c)
    rows = [[d, T, T, T, T, T] for d in ("ko → ja", "ja → ko", "ko → zh", "zh → ko", "ja → zh", "zh → ja")]
    c.table("pivotref", "Pivoted on-device translation versus direct NLLB-200-distilled-600M (off-device; "
                        "pending)",
            ["Direction", "chrF pivot", "chrF NLLB", "COMET pivot", "COMET NLLB", "SPM mismatches (src)"],
            rows, widths=[2.6, 2.4, 2.4, 2.6, 2.6, 3.7])

    # ------------------------------------------------------------------ RQ4
    c.h2("RQ4: Latency and Memory on Device", key="r_rq4")
    c.p("{T:lat} will report median per-stage latency at the HIGH quality level on each device tier; "
        "{T:latq} the dependence of detection latency on the quality level (H4a), for which Chapter 4 "
        "predicts a roughly proportional relationship to the number of detector input pixels — "
        "analytical input-pixel ratios of 1 : 2.25 : 4 for 640 : 960 : 1280 on pages larger than the "
        "limit. {T:mem} reports memory and model-load times.")
    _pending(c)
    c.table("lat", "Median on-device latency per page (ms), quality HIGH (1280 px); p90 in brackets "
                   "(pending)",
            ["Stage", "Low tier", "Mid tier", "High tier"],
            [["Detection", T, T, T], ["Detection post-processing", T, T, T],
             ["Classification + recognition", T, T, T], ["Script check + re-recognition (when triggered)", T, T, T],
             ["Translation, direct pair", T, T, T], ["Translation, pivoted pair", T, T, T],
             ["Rendering", T, T, T], ["End to end, direct pair", T, T, T]],
            widths=[7.0, 3.1, 3.1, 3.1])
    c.table("latq", "Detection latency (ms, median) by quality level; analytical pixel ratio relative to "
                    "LOW (pending)",
            ["Quality level", "L_{max}", "Pixel ratio (analytical)", "Low tier", "Mid tier", "High tier"],
            [["LOW", "640", "1.00", T, T, T], ["MEDIUM", "960", "2.25", T, T, T],
             ["HIGH", "1280", "4.00", T, T, T]], widths=[2.8, 2.0, 3.6, 2.6, 2.6, 2.7])
    c.table("mem", "Memory and model loading (pending)",
            ["Quantity", "Low tier", "Mid tier", "High tier"],
            [["Peak PSS, direct page (MB)", T, T, T], ["Peak PSS, pivoted page (MB)", T, T, T],
             ["Peak PSS, PDF job at 200 dpi (MB)", T, T, T], ["Detector session creation (ms)", T, T, T],
             ["Recogniser session creation, per language (ms)", T, T, T],
             ["MT pair load, encoder + decoder (ms)", T, T, T]], widths=[7.0, 3.1, 3.1, 3.1])
    c.p("{T:kv} tests H4b. For each output-length bin it lists the analytical overhead factor (n + 1)/2 "
        "for position-proportional work, computed at the bin's midpoint, beside the measured ratio of "
        "decoder time without and with a key–value cache. Because attention terms grow faster "
        "({T:costterms}) and fixed per-step overheads grow slower, the measured ratio may lie on either "
        "side of the analytical column; the table will show which effect dominates on real hardware.")
    _pending(c)
    rows = []
    for lo, hi in ((1, 8), (9, 16), (17, 32), (33, 64)):
        mid = (lo + hi) / 2
        rows.append([f"{lo}–{hi}", f"{(mid + 1) / 2:.2f}", T, T, T])
    c.table("kv", "Decoder cost ratio without / with KV cache by output length (analytical column from "
                  "Equation {E:positions}; measured columns pending)",
            ["Steps n", "(n + 1)/2 at bin midpoint (analytical)", "Measured, low tier", "Measured, mid tier",
             "Measured, high tier"], rows, widths=[2.2, 4.6, 3.1, 3.1, 3.3])

    # ------------------------------------------------------------------ RQ5
    c.h2("RQ5: Perceived Rendering Quality", key="r_rq5")
    c.p("{T:user} will report mean ratings and measured texture retention for each condition. The "
        "rightmost column is analytical (Proposition 6.1). The table tests H5a (C3 not less legible than "
        "C1), H5b (C3 more natural than C1) and H5c (ρ tracks 1 − α). The contrast between C3 and C4 "
        "isolates the halo; the contrast between C3 and C6 compares the analytic approach with "
        "learned inpainting.")
    _pending(c)
    c.table("user", "User study: mean ratings (1–5) and texture retention ρ (pending; last column analytical)",
            ["Condition", "Legibility", "Naturalness", "Preference share", "ρ (measured)", "1 − α (analytical)"],
            [["C1 α = 255, opaque erase", T, T, T, T, "0.00"],
             ["C2 α = 200, halo", T, T, T, T, "0.22"],
             ["C3 α = 150, halo (default)", T, T, T, T, "0.41"],
             ["C4 α = 150, no halo", T, T, T, T, "0.41"],
             ["C5 α = 90, halo", T, T, T, T, "0.65"],
             ["C6 LaMa inpainting (off-device)", T, T, T, T, "—"]],
            widths=[4.8, 2.1, 2.3, 2.4, 2.3, 2.4])
    c.table("clmm", "CLMM estimates for condition contrasts (log-odds, 95% CI; pending)",
            ["Contrast", "Outcome", "Estimate", "95% CI", "p (Holm)", "Hypothesis"],
            [["C3 − C1", "Legibility", T, T, T, "H5a (non-inferiority)"],
             ["C3 − C1", "Naturalness", T, T, T, "H5b"],
             ["C3 − C4", "Legibility", T, T, T, "Halo effect"],
             ["C3 − C6", "Naturalness", T, T, T, "Analytic vs inpainting"],
             ["Condition × stratum", "Naturalness", T, T, T, "Secondary"]],
            widths=[2.8, 2.5, 2.3, 2.6, 2.2, 3.9])
    c.p("{T:hypsum} will summarise the outcome of every hypothesis once the tables are filled.")
    c.table("hypsum", "Summary of hypothesis outcomes (pending)",
            ["Hypothesis", "Table(s)", "Outcome", "Effect size / CI"],
            [["H1a", "{T:det}", T, T], ["H1b", "{T:detangle}", T, T], ["H1c", "{T:det}", T, T],
             ["H2", "{T:rec}", T, T], ["H3a", "{T:quant}", T, T], ["H3b", "{T:quant}", T, T],
             ["H3c", "{T:pivotref}", T, T], ["H4a", "{T:latq}", T, T], ["H4b", "{T:kv}", T, T],
             ["H5a", "{T:user}, {T:clmm}", T, T], ["H5b", "{T:user}, {T:clmm}", T, T],
             ["H5c", "{T:user}", T, T]], widths=[2.4, 4.4, 4.0, 5.5])

    # ----------------------------------------------------------- discussion
    c.h2("Discussion of Expected Trade-offs", key="discussion")
    c.p("Although no measurement is yet available, the analysis of the preceding chapters already "
        "determines the shape of several trade-offs. This section states them, so that the measured "
        "results can be read against explicit expectations; none of the statements below is an "
        "empirical finding.")
    c.h3("Exactness of the geometry")
    c.p("Lemma 4.1 and Proposition 4.1 imply that, for components whose reference treatment is "
        "\"minimum-area rectangle, then round-join offset, then minimum-area rectangle\", the "
        "library-free boxes are identical to the reference boxes up to arc discretisation. Differences "
        "in {T:det} can therefore arise only from the score (a deliberate change), from contour-mode "
        "unclipping of non-convex components, from connectivity conventions of contour tracing versus "
        "flood fill, and from the order of size filters. This is a narrow and testable set of causes, "
        "which makes RQ1 a sharp test.")
    c.h3("Rendering: completeness of removal versus fidelity of texture")
    c.p("Proposition 6.1 makes the central trade-off of the renderer explicit. Lowering α retains more "
        "texture and more of the original's ghost in exactly equal proportion; no choice of α removes "
        "the ghost while keeping the texture. The halo breaks this coupling locally, but only within "
        "0.08 s of each new glyph. The practical question for RQ5 is therefore where the balance lies "
        "for users, and whether it differs by content: for flat documents the texture is weak and an "
        "opaque fill may look acceptable, whereas over photographs the flat patch of α = 1 is expected "
        "to be most conspicuous. The retained ghost contrast at the default α — about 3:1 for black on "
        "white by the WCAG formula ({T:ghost}) — sits below the 4.5:1 level for body text, which is "
        "consistent with the design intention that the ghost be noticeable but not compete with the "
        "halo-protected translation at 21:1.")
    c.h3("Translation: quadratic decoding and pivoting")
    c.p("The cache-less decoder's overhead factor (n + 1)/2 is modest for short outputs — 8.5 at 16 "
        "steps — but reaches 32.5 at 64 steps (analytical), and the logit transfer of "
        "{T:costterms} grows with the same factor times the vocabulary size. The design is therefore "
        "expected to be adequate for signs, labels and short paragraphs and to become the dominant cost "
        "for dense document pages, where paragraphs approach the 192-token chunk budget. Pivoting "
        "roughly doubles translation time and, on the independence model of Chapter 5, can only lose "
        "meaning relative to its weaker leg; its measured cost relative to NLLB in {T:pivotref} will "
        "decide whether shipping direct CJK↔CJK models is worth their size.")
    c.h3("Quality level as the main speed knob")
    c.p("Detection is the only stage whose cost the user controls directly. The analytical pixel ratios "
        "in {T:latq} imply that LOW processes a quarter of the pixels of HIGH; if detection dominates "
        "end-to-end latency on low-tier devices, LOW may be the better default there, at a cost in "
        "small-text recall that RQ1's per-level results will quantify.")

    c.h2("Limitations", key="limitations")
    c.p("The limitations of the system, collected from the preceding chapters, are:")
    c.bullets([
        "**Recognition.** Vertical CJK text is not typeset vertically, and the script test cannot "
        "distinguish Kanji-only Japanese from Chinese. The reading-order comparator uses a tolerance and "
        "is not transitive. Colour estimation assumes that glyphs are the minority of a crop.",
        "**Korean.** Paragraph assembly joins Korean line wraps without a space, although Korean "
        "separates words with spaces; this must be fixed before Korean is exposed in the interface.",
        "**Translation.** Greedy, cache-less decoding suits short segments but not long documents; the "
        "full logit block is copied at every step; chunk outputs are joined with a space even for CJK "
        "targets; pivoting doubles latency and compounds errors; and multi-page pivoted jobs reload both "
        "model pairs on every page.",
        "**Rendering.** The typeface is not reproduced; a high-contrast original remains as a ghost "
        "outside the halo; paragraph highlights cover the empty tails of ragged lines; overflowing text "
        "is not clipped; and colours are taken from a paragraph's first line.",
        "**Interface.** The compact dimension tokens place most touch targets below the 48 dp platform "
        "guidance (24–32 dp for most controls on phones), a deliberate trade-off for screen space that "
        "can be expected to raise tap-error rates, especially one-handed; it has not been evaluated.",
        "**Memory.** Model files are copied into a Java byte array before session creation instead of "
        "being memory-mapped.",
        "**Evaluation.** At the time of writing none of the protocol has been executed; every "
        "experimental claim of the thesis statement remains a hypothesis.",
    ])
