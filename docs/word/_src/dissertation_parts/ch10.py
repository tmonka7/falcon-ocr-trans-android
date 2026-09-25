"""Chapter 10: Conclusion and Future Work."""


def build(c):
    c.chapter(10, "Conclusion and Future Work")
    c.h2("Summary", key="summary")
    c.p("This dissertation set out to show that a complete, layout-preserving image translation pipeline "
        "can run entirely on a commodity smartphone, in managed code, without native dependencies of its "
        "own, and to understand exactly what that constraint costs. The system studied does so. It "
        "requests no network permission, so its privacy guarantee is enforced by the operating system "
        "rather than by policy. It chains PP-OCR detection, orientation classification and CTC "
        "recognition with OPUS-MT translation over ONNX Runtime, serialises all inference on one worker "
        "thread, caches recognition sessions per language and keeps one translation pair resident.")
    c.p("Three analytical contributions accompany the artefact. First, the Differentiable Binarization "
        "post-processing was rebuilt without OpenCV or a clipping library: Lemma 4.1 proves that the "
        "convex hull of a component equals the hull of its row extremes, reducing the geometric work "
        "from the component's area to its height; the minimum-area rectangle is exact by the "
        "Freeman–Shapira theorem; and Proposition 4.1 proves that the closed-form rectangle unclip "
        "coincides with a round-join polygon offset followed by a minimum-area refit. Second, the "
        "translation stage was analysed exactly: the Viterbi tokeniser solves the unigram objective, the "
        "cache-less decoder processes n(n + 1)/2 positions for n steps, and English pivoting covers the "
        "six CJK↔CJK directions under a one-pair memory bound at a cost in latency and error "
        "compounding that the evaluation will quantify. Third, the re-rendering replaces opaque "
        "erasure with a translucent highlight whose effect is stated in closed form — Proposition 6.1: "
        "glyph contrast and texture both retain exactly 1 − α, 0.41 at the default — while a halo "
        "restores full contrast around every new glyph (Corollary 6.1), and a bisection search returns a "
        "feasible font size in a logarithmic number of layouts (Proposition 6.2).")
    c.p("The implementation also addresses use: compact, screen-relative control sizes defined as "
        "dimension tokens, a side menu that expands over the content rather than reflowing it, and a "
        "language-gating mechanism that lets a fully implemented language be withheld from users by "
        "editing one list.")

    c.h2("Answers to the Research Questions", key="answers")
    c.p("Because the evaluation protocol has not yet been executed, the research questions can at "
        "present be answered only in part. {T:answers} states, for each, what is established "
        "analytically and what awaits measurement.")
    c.table("answers", "Status of the research questions",
            ["RQ", "Established analytically", "Pending measurement"],
            [["RQ1", "Hull reduction exact (Lemma 4.1); rectangle unclip equals round-join offset + refit "
                     "(Prop. 4.1); box-mean bias bound for unmasked boxes", "H-mean vs reference; angle-"
                                                                             "stratified effect of the score"],
             ["RQ2", "Cost-sensitive interpretation of the 0.9 flip threshold; optimality of sorted batching "
                     "(Lemma 4.2)", "Word accuracy and 1 − NED per script; classifier effect"],
             ["RQ3", "Exact Viterbi segmentation; pivot error-compounding bound under independence",
              "BLEU, chrF, COMET for 12 directions; int8, beam and pivot costs"],
             ["RQ4", "Decoder cost n(n + 1)/2; detection cost ∝ input pixels; one-pair residency",
              "Latency, peak PSS, load times on three tiers; measured KV-cache ratio"],
             ["RQ5", "Retention 1 − α (Prop. 6.1); halo guarantee (Cor. 6.1); ghost contrast ratio",
              "Legibility, naturalness, preferences; measured ρ"]],
            widths=[1.3, 8.2, 6.8])

    c.h2("Future Work", key="future")
    c.bullets([
        "**Execute the protocol.** Fill every [TBD] of Chapter 9, report the outcomes of all hypotheses "
        "including negative ones, and release the evaluation scripts and in-house data where licences "
        "and consent permit.",
        "**Key–value-cached decoding.** Export the decoder with past key–values and thread the cache "
        "through the decoding loop, reducing position-proportional decoder work from n(n + 1)/2 to n; "
        "independently, read only the last row of the logits.",
        "**Direct CJK↔CJK translation.** Evaluate compact direct models, for example distilled from a "
        "multilingual teacher [@kim2016distill, nllb2022], which the router would prefer automatically.",
        "**Compact on-device text erasure.** Combine a small erasure or inpainting model with the halo "
        "renderer, using the highlight as a fallback when the model is not confident.",
        "**Vertical CJK layout** in both grouping and typesetting, and per-line highlight shapes for "
        "ragged paragraphs.",
        "**Language identification** by character bigrams to resolve Kanji-only Japanese.",
        "**Korean release.** Fix line joining for Korean, evaluate it, and enable it in `Lang.USER_FACING`.",
        "**Memory.** Memory-map model files instead of copying them to the Java heap, keep both pivot legs "
        "resident during multi-page jobs if RQ4 shows reloading to be costly, and move models into an "
        "install-time asset pack for store distribution.",
        "**Accessibility.** Evaluate tap accuracy with the compact control tokens and provide an "
        "alternative token set that meets the 48 dp guidance, selectable in settings or by the system "
        "font-scale preference.",
        "**Robustness.** Replace the tolerance comparator of reading order with explicit row "
        "clustering, and add a regression suite built from the evaluation datasets.",
    ])

    c.h2("Closing Remarks", key="closing")
    c.p("Much of the recent progress in image translation has come from larger learned models. This "
        "work took a complementary route: it asked which parts of the problem can be solved exactly, "
        "proved them, and used learned models only where nothing else will do. The result is a system "
        "whose behaviour can be stated in closed form wherever it is not a neural network — which boxes "
        "it produces, how much of the original page survives its rendering, how many layouts its size "
        "search needs — and which runs, privately and offline, on the phone in a user's pocket. Whether "
        "users prefer what it produces is the question the evaluation now has to answer.")
