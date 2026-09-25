"""Chapter 8: Experimental Methodology."""


def build(c):
    c.chapter(8, "Experimental Methodology")
    c.p("This chapter specifies how the five research questions will be answered. It is written as a "
        "protocol to be executed, with hypotheses, datasets, metrics, procedures, ablations and analyses "
        "fixed in advance, so that the results reported in Chapter 9 cannot be shaped by the data. "
        "Where a quantity must be chosen before execution — the number of pages, participants or "
        "devices — it is marked [TBD] and must be fixed, with its justification, before data "
        "collection begins. Exact software versions, model checksums, random seeds and device builds "
        "are to be recorded with every run.")

    c.h2("Overview", key="exp_overview")
    c.p("{F:exp} summarises the design. RQ1 and RQ2 are offline comparisons on public OCR benchmarks, "
        "run on a workstation with the same ONNX models and the same Java post-processing code as the "
        "device (the post-processing is pure Java and runs unchanged on a desktop JVM). RQ3 evaluates "
        "translation offline on FLORES-200. RQ4 is measured on physical phones. RQ5 is a within-subjects "
        "user study. {T:hyp} lists the hypotheses; each result table in Chapter 9 names the hypothesis "
        "it tests.")
    c.figure("exp", "exp_design", "Experimental design: research questions, data, measures and analyses "
             "(schematic).", width=16)
    c.table("hyp", "Pre-specified hypotheses",
            ["ID", "Hypothesis", "Test"],
            [["H1a", "The library-free post-processing (component-mean score, rectangle unclip) is "
                     "equivalent to the reference in H-mean on each dataset, within a margin of ±1 "
                     "percentage point (margin to be confirmed before execution).",
              "TOST on paired bootstrap differences [@schuirmann1987tost, efron1993bootstrap]"],
             ["H1b", "Component-mean scoring increases recall relative to box-mean scoring for text "
                     "rotated more than 20°, without reducing precision for text under 5°.",
              "Paired bootstrap per angle stratum"],
             ["H1c", "Rectangle unclip and polygon unclip give the same H-mean (Proposition 4.1 predicts "
                     "identity for rectangle inputs).", "Paired bootstrap; count of differing boxes"],
             ["H2", "The orientation classifier increases word accuracy on crops that are upside down and "
                    "does not decrease it on upright crops.", "McNemar's test on paired word outcomes "
                                                              "[@mcnemar1947]"],
             ["H3a", "Int8 dynamic quantisation changes chrF and COMET by less than a practically "
                     "negligible margin relative to fp32 (margin to be fixed a priori).", "Paired bootstrap "
                                                                                           "[@koehn2004bootstrap]"],
             ["H3b", "Beam search (k = 4) improves on greedy decoding by a small amount relative to its "
                     "cost.", "Paired bootstrap; cost from RQ4"],
             ["H3c", "Pivoted CJK↔CJK directions score below a direct multilingual reference.",
              "Paired bootstrap vs NLLB-200-distilled-600M"],
             ["H4a", "Detection latency scales approximately with the number of detector input pixels "
                     "(Chapter 4).", "Regression of latency on w′h′"],
             ["H4b", "The measured decoder cost ratio without/with KV cache approaches the analytical "
                     "(n + 1)/2 for position-proportional work.", "Ratio per output-length bin"],
             ["H5a", "Translucent highlight with halo (α = 150) is rated no less legible than opaque "
                     "erasure.", "CLMM, non-inferiority contrast"],
             ["H5b", "Translucent highlight with halo is rated more natural than opaque erasure.",
              "CLMM contrast"],
             ["H5c", "Measured texture retention ρ inside Ω follows 1 − α (Proposition 6.1).",
              "Regression of ρ on 1 − α"]],
            widths=[1.3, 10.2, 4.8], font_size=8.5)

    c.h2("Datasets", key="datasets")
    c.table("datasets", "Datasets and their roles",
            ["Dataset", "Content", "Used for", "Notes"],
            [["ICDAR 2015 Incidental Scene Text [@karatzas2015icdar]", "English scene text captured "
              "incidentally with wearable cameras; word-level quadrilaterals", "RQ1 (en), RQ2 (en)",
              "Standard test split"],
             ["MLT-2019 [@nayef2019mlt]", "Multi-lingual scene text in ten languages including Chinese, "
              "Japanese and Korean; line/word quadrilaterals with script labels", "RQ1, RQ2 (zh, ja, ko)",
              "Script subsets selected by annotation; split to be fixed"],
             ["FLORES-200 devtest [@nllb2022, goyal2022flores]", "Professionally translated, "
              "multi-way parallel sentences", "RQ3, all 12 directions", "Same sentences in every "
              "language, enabling pivot vs direct comparison"],
             ["In-house document photographs", "[TBD] photographed pages: forms, letters, menus, "
              "signage, text over photographs", "RQ4 pages; RQ5 stimuli; RQ1 external validity",
              "Consent, licence and anonymisation required"],
             ["User-study stimulus set", "[TBD] images in three strata: flat documents, light-on-dark "
              "signs, text over photographs", "RQ5", "Balanced across strata and languages"]],
            widths=[3.8, 5.4, 3.3, 3.8], font_size=8.5)
    c.p("Two caveats apply to the public OCR benchmarks. Their test ground truth may be withheld by the "
        "competition organisers, in which case evaluation uses a held-out portion of the public "
        "annotations with the split documented; and the released PP-OCR weights may have been trained on "
        "data that overlap these benchmarks. The second caveat is harmless for RQ1 — both "
        "post-processing variants use the same network, so contamination affects them equally — but "
        "it inflates absolute recognition accuracy in RQ2, which is why an in-house set of photographed "
        "documents, collected for this study, is also required.")

    c.h2("Metrics", key="metrics")
    c.h3("Detection")
    c.p("A predicted quadrilateral matches a ground-truth quadrilateral when their intersection over "
        "union exceeds 0.5, with one-to-one matching; regions marked \"do not care\" in the annotations "
        "are excluded. With TP matched pairs, precision, recall and H-mean are")
    c.eq("P = TP / |pred|,    R = TP / |gt|,    H = 2PR / (P + R)", key="hmean")
    c.h3("Recognition")
    c.p("Word accuracy is the fraction of ground-truth crops whose recognised string equals the "
        "reference exactly after a documented normalisation (Unicode NFKC; for English, case folding and "
        "removal of punctuation, following common scene-text practice). Normalised edit distance uses "
        "the Levenshtein distance [@levenshtein1966] between prediction x̂ and reference x:")
    c.eq("NED = (1/N) Σ_{i} d_{L}(x̂_{i}, x_{i}) / max(|x̂_{i}|, |x_{i}|),        reported as 1 − NED", key="ned")
    c.p("Recognition is evaluated on ground-truth crops so that it is isolated from detection, and "
        "also end to end on detected crops for the in-house set.")
    c.h3("Translation")
    c.p("BLEU [@papineni2002bleu] is computed with sacreBLEU [@post2018sacrebleu] using the tokeniser "
        "appropriate to the target language — `13a` for English, `zh` for Chinese, `ja-mecab` for "
        "Japanese and `ko-mecab` for Korean — and the full signature is reported. chrF "
        "[@popovic2015chrf], a character n-gram F-score, is less sensitive to tokenisation and is "
        "treated as the primary automatic metric for CJK targets. COMET [@rei2020comet], a learned "
        "metric that correlates better with human judgement [@kocmi2021ship], is reported with the "
        "exact model identifier. Differences between systems are tested with paired bootstrap "
        "resampling over sentences [@koehn2004bootstrap].")
    c.h3("Efficiency")
    c.p("Latency is wall-clock time per stage — detection, detection post-processing, classification "
        "and recognition, translation, rendering — and end to end, reported as the median and the 90th "
        "percentile over pages. Memory is the peak proportional set size (PSS) of the process during a "
        "page. Cold-start model-load time is the time to create each ONNX session from its asset. The "
        "application currently logs total recognition time and total pipeline time; a measurement build "
        "adds monotonic-clock timestamps around each stage, with instrumentation compiled out of "
        "release builds.")
    c.h3("Rendering")
    c.p("Participants rate legibility and naturalness on 5-point scales and give pairwise preferences. "
        "The objective companion metric is texture retention inside the highlight region, measured on "
        "non-glyph pixels of Ω (pixels whose distance from any original or new glyph exceeds a margin):")
    c.eq("ρ = σ_{out} / σ_{in}", key="rho")
    c.p("where σ_{in} and σ_{out} are the standard deviations of luminance over the same pixel set "
        "before and after rendering. Proposition 6.1 predicts ρ = 1 − α in the interior of Ω, and "
        "ρ ≥ 1 − α including the feathered edge; deviations measure the effect of feathering, "
        "quantisation to 8 bits and the halo. SSIM [@wang2004ssim] between original and rendered image "
        "outside the new glyphs is reported as a secondary measure.")

    c.h2("RQ1 Protocol: Detection Post-processing", key="m_rq1")
    c.p("The same PP-OCRv4 detector ONNX model is run once per image, and its probability map is "
        "post-processed by (a) the reference PaddleOCR post-processing (OpenCV contours, box-mean score, "
        "polygon unclip with a clipping library) and (b) the library-free Java implementation, with "
        "identical thresholds (τ_{b} = 0.3, τ_{s} = 0.6, r = 1.6) and identical detector input "
        "resolution for each quality level. Because the network output is shared, any difference is "
        "attributable to post-processing alone. Two ablations isolate the two deliberate deviations: "
        "box-mean versus component-mean scoring, and polygon versus rectangle unclip. Results are "
        "stratified by the angle of the ground-truth box (< 5°, 5–20°, > 20°) to test the "
        "rotation-bias hypothesis behind S(C). Post-processing time per image is recorded on the same "
        "workstation for both implementations as a secondary outcome.")

    c.h2("RQ2 Protocol: Recognition", key="m_rq2")
    c.p("Word accuracy and 1 − NED are computed per script on ground-truth crops of ICDAR 2015 and the "
        "MLT-2019 subsets, with and without the orientation classifier. To test H2 specifically, each "
        "crop set is evaluated twice: as annotated, and rotated by 180°; the classifier should recover "
        "most rotated crops and leave upright crops unchanged. Confidence calibration of the CTC line "
        "confidence is examined by plotting accuracy against confidence, which informs whether the "
        "discard threshold of 0.5 is well placed. The effect of the automatic script check is measured "
        "separately on the in-house set by deliberately misconfiguring the source language.")

    c.h2("RQ3 Protocol: Translation Quality", key="m_rq3")
    c.p("All twelve directions are evaluated on FLORES-200 devtest. The main configuration is the "
        "deployed one: int8 models, greedy decoding, the length limit of Equation {E:limit}, and the "
        "chunking rule of Chapter 5, run through the Java tokeniser and decoding loop on a desktop JVM "
        "with ONNX Runtime so that tokenisation and decoding are identical to the device. Ablations: "
        "fp32 versus int8 (H3a), greedy versus beam 4 (H3b, beam search run with the reference "
        "Transformers implementation of the same checkpoints), and, for the six pivoted directions, "
        "NLLB-200-distilled-600M direct translation as an upper-bound reference that does not fit the "
        "device budget (H3c). To separate tokeniser fidelity from model quality, the Java SentencePiece "
        "segmentation is compared with the reference library on all source sentences, and any mismatch "
        "is reported.")

    c.h2("RQ4 Protocol: Efficiency on Device", key="m_rq4")
    c.p("Three devices from different price tiers are used ({T:devices}). Each device is reset to a "
        "documented state: airplane mode, fixed screen brightness, battery above 50% and not charging, "
        "no other user applications running, and a cool-down period between runs so that thermal "
        "throttling does not drift across conditions. For each quality level (640, 960 and 1280 pixels) "
        "[TBD] pages from the in-house set are processed, preceded by warm-up runs that are discarded. "
        "Measured are per-stage latency (median and 90th percentile), peak PSS, cold-start session "
        "creation time per model, and, for translation, the ratio of decoder time without and with a "
        "key–value cache, the latter using an experimental cached export of the same checkpoints and "
        "binned by output length to compare with the analytical (n + 1)/2 (H4b).")
    c.table("devices", "Devices for RQ4 (to be fixed before execution)",
            ["Tier", "Device model", "SoC", "RAM", "Android version", "Build / ORT version"],
            [["Low", "[TBD]", "[TBD]", "[TBD]", "[TBD]", "[TBD]"],
             ["Mid", "[TBD]", "[TBD]", "[TBD]", "[TBD]", "[TBD]"],
             ["High", "[TBD]", "[TBD]", "[TBD]", "[TBD]", "[TBD]"]],
            widths=[1.5, 3.0, 3.0, 1.8, 2.8, 4.2])

    c.h2("RQ5 Protocol: User Study of Rendering", key="m_rq5")
    c.h3("Design and conditions")
    c.p("A within-subjects study compares rendering variants of the same images ({F:study}). The "
        "variant factor crosses highlight opacity α ∈ {255 (opaque erase), 200, 150, 90} with halo "
        "∈ {on, off}; to keep sessions short, the core set shown to every participant is α = 255, "
        "α = 200 with halo, α = 150 with halo (default), α = 150 without halo and α = 90 with halo, plus "
        "an off-device LaMa-inpainted reference [@suvorov2022lama] in which the original text is removed "
        "before the translation is typeset with the same fitting and halo. All variants of an image use "
        "identical detection, translation and fitted layouts, so they differ only in the treatment of "
        "the original.")
    c.table("conds", "User-study conditions (analytical retained fraction from Proposition 6.1)",
            ["Condition", "α (0–255)", "Halo", "1 − α (analytical)"],
            [["C1 Opaque erase", "255", "off", "0.00"], ["C2", "200", "on", "0.22"],
             ["C3 Default", "150", "on", "0.41"], ["C4", "150", "off", "0.41"], ["C5", "90", "on", "0.65"],
             ["C6 LaMa inpainting (off-device)", "—", "on", "—"]],
            widths=[5.6, 3.0, 2.6, 5.1])
    c.h3("Participants, stimuli and procedure")
    c.p("[TBD] participants will be recruited, with the number fixed by a power analysis or a "
        "simulation-based estimate for the CLMM contrasts before recruitment. Inclusion requires "
        "normal or corrected-to-normal vision and reading ability in the target language of the "
        "stimuli; the source language should be one the participant does not read, so that the "
        "ghost of the original does not act as a crib. Stimuli are [TBD] images balanced across the "
        "three content strata. Each session comprises consent and demographics, two practice images, a "
        "rating block in which each image–condition pair is shown once in randomised order on a "
        "calibrated phone held by the participant, a block of pairwise preferences between conditions of "
        "the same image, and a debrief with the System Usability Scale [@brooke1996sus] for the "
        "application as a whole and free-text comments. Ratings are 5-point scales for legibility "
        "(\"the translated text is easy to read\") and naturalness (\"the translation looks like part of "
        "the page\").")
    c.figure("study", "user_study", "User-study conditions and per-participant session flow "
             "(schematic).", width=15.5)
    c.h3("Analysis")
    c.p("Ratings are ordinal, so they are analysed with cumulative link mixed models (CLMM) "
        "[@agresti2010ordinal] with condition as a fixed effect and crossed random intercepts for "
        "participant and image [@baayen2008mixed], adding random slopes as far as the data support "
        "[@barr2013maximal]; linear mixed models fitted with lme4 [@bates2015lme4] on the raw ratings, "
        "and aligned-rank-transform ANOVA [@wobbrock2011art], serve as robustness checks. H5a is tested "
        "as a non-inferiority contrast of C3 against C1 on legibility with a pre-specified margin; H5b "
        "as a superiority contrast on naturalness. Pairwise preferences are analysed with a "
        "Bradley–Terry model [@bradley1952paired]. Content stratum is added as a fixed effect and in "
        "interaction with condition in a secondary model, since the opaque erase is expected to fare "
        "worst over photographs. H5c is tested by regressing measured ρ on 1 − α across conditions and "
        "images.")
    c.h3("Ethics")
    c.p("The study requires approval from the institutional review board of [University] before "
        "recruitment. Participants give informed consent, may withdraw at any time without "
        "consequence, and are compensated at [TBD]. No personal documents are used as stimuli; in-house "
        "photographs are of documents created for the study or with rights cleared, and any personal "
        "data visible in them is removed. Responses are stored pseudonymously, separated from consent "
        "forms, and retained for [TBD] years. Appendix C holds placeholders for the consent form, "
        "instructions and questionnaire.")

    c.h2("Statistical Conventions", key="stats")
    c.p("All confidence intervals are 95% and are obtained by bootstrap unless a model provides them. "
        "Families of related tests — the angle strata of RQ1, the twelve directions of RQ3, the "
        "condition contrasts of RQ5 — are corrected with the Holm procedure [@holm1979]. Equivalence and "
        "non-inferiority margins are fixed before execution and justified in terms of practical "
        "significance, not statistical convenience. Effect sizes are reported alongside every test, and "
        "no result is dropped for being non-significant.")
    c.table("ablations", "Ablations and the question each answers",
            ["ID", "Factor", "Levels", "RQ / hypothesis"],
            [["A1", "Detection score", "box mean / component mean", "RQ1, H1b"],
             ["A2", "Unclip", "polygon offset / closed-form rectangle", "RQ1, H1c"],
             ["A3", "Orientation classifier", "off / on", "RQ2, H2"],
             ["A4", "Detector input size", "640 / 960 / 1280", "RQ1, RQ4 (H4a)"],
             ["A5", "MT weights", "fp32 / int8", "RQ3 (H3a), RQ4"],
             ["A6", "Decoding", "greedy / beam 4", "RQ3 (H3b), RQ4"],
             ["A7", "CJK↔CJK route", "English pivot / NLLB direct (off-device)", "RQ3 (H3c)"],
             ["A8", "Decoder export", "cache-less / KV cache", "RQ4 (H4b)"],
             ["A9", "Rendering", "α ∈ {255, 200, 150, 90} × halo", "RQ5 (H5a–c)"],
             ["A10", "Recognition batching", "arrival order / sorted by aspect ratio", "RQ4"],
             ["A11", "Script verification", "off / on", "RQ2, RQ4"]],
            widths=[1.3, 4.0, 6.5, 4.5])

    c.h2("Threats to Validity", key="threats")
    c.p("Following the usual classification [@wohlin2012experimentation], the main threats and their "
        "mitigations are as follows.")
    c.bullets([
        "**Internal validity.** RQ1 and RQ3 compare implementations that share networks, so model "
        "variation is controlled; the remaining risk is configuration drift, mitigated by running both "
        "variants from one script with one parameter file. On-device timing is confounded by thermal "
        "state, background activity and frequency scaling; the device protocol controls these as far as "
        "possible and reports variability.",
        "**Construct validity.** BLEU is a weak proxy for translation quality, especially for CJK "
        "targets where it depends on segmentation; chrF and COMET are therefore reported and the "
        "tokenisers fixed. H-mean at IoU 0.5 rewards boxes that a translation renderer might still place "
        "poorly; the in-house set allows inspection of rendered pages. Rating scales measure perceived "
        "legibility, not reading performance; a reading-time or comprehension task is a possible "
        "extension.",
        "**External validity.** Public benchmarks are scene-text-heavy, while many intended uses concern "
        "documents; the in-house set addresses this but its composition must be described. Three "
        "devices cannot represent the Android ecosystem [@ignatov2018aibench]. Participants in a lab "
        "study are not travellers in front of a sign.",
        "**Conclusion validity.** Multiple testing is controlled with Holm corrections; sample sizes are "
        "fixed in advance; non-significant results are reported with confidence intervals rather than "
        "as evidence of no effect, except where an equivalence test is specified.",
        "**Model provenance.** The EN→JA checkpoint is taken from a repository whose name uses a "
        "non-standard language code (Chapter 5); its model card must be checked. Benchmark overlap "
        "with the OCR training data would inflate absolute accuracies (Section {S:datasets}).",
    ])
