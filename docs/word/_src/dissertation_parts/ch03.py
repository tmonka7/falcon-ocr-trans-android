"""Chapter 3: System Requirements and Architecture."""


def build(c):
    c.chapter(3, "System Requirements and Architecture")
    c.p("This chapter describes the system as a whole before Chapters 4 to 6 examine its algorithms. It "
        "states the requirements the design answers to, the principles that guided it, and the "
        "architecture that results: packages and their responsibilities, the processing pipeline and its "
        "data types, the threading and memory model, the model tree and its validation, and deployment. "
        "The description is derived from the source code under `app/src/main/java/com/falcon/ocrtrans/` "
        "and from the project's technical documentation.")

    c.h2("Requirements", key="req")
    c.p("The requirements below were reconstructed from the implementation and its documentation rather "
        "than taken from a separate specification; each is phrased so that it can be checked against "
        "the code or measured by the protocol of Chapter 8. {T:fr} lists the functional requirements and "
        "{T:nfr} the non-functional ones.")
    c.table("fr", "Functional requirements",
            ["ID", "Requirement", "Realised by"],
            [["FR1", "Accept input from the camera, from one or more gallery images, and from PDF files "
                     "with a selectable page range.", "`CameraActivity`, `ImageImportActivity`, `PdfActivity`"],
             ["FR2", "Detect text regions at arbitrary orientation and return them as ordered "
                     "quadrilaterals in page pixels.", "`PaddleOcrEngine.detect`, `DbPostProcessor`"],
             ["FR3", "Recognise English, Korean, Japanese and Chinese text with a per-script recogniser.",
              "`PaddleOcrEngine.recognizeCrops`, `CtcDecoder`, `CharDict`"],
             ["FR4", "Group lines into reading order and paragraphs so that translation sees sentences.",
              "`LineGrouper`, `Paragraph`"],
             ["FR5", "Optionally verify the configured source language from the recognised script and "
                     "re-recognise with the matching head.", "`ScriptDetector`, `TranslationPipeline`"],
             ["FR6", "Translate between every ordered pair of the four languages (12 directions).",
              "`MarianTranslator`, `PivotTranslator`"],
             ["FR7", "Re-render the translation over the page, preserving position, orientation, relative "
                     "size and colours.", "`LayoutRenderer`, `TextFitter`"],
             ["FR8", "Export PDF jobs as re-rendered PDF, DOCX or plain text.", "`PdfJob`, `DocxWriter`"],
             ["FR9", "Allow the recognised and translated text to be edited, copied, read aloud and "
                     "saved to a local history.", "`ResultActivity`, `HistoryStore`"],
             ["FR10", "Translate typed text without OCR.", "`TranslateActivity`"],
             ["FR11", "Report precisely which model files are missing instead of failing later.",
              "`ModelValidator`, `SplashActivity`, `MainActivity`"]],
            widths=[1.3, 9.5, 5.5])
    c.table("nfr", "Non-functional requirements",
            ["ID", "Requirement", "Design response / verification"],
            [["NFR1 Privacy", "No image or text leaves the device.", "No `INTERNET` permission in the "
              "manifest; verified by inspection."],
             ["NFR2 Offline", "Full function without connectivity.", "All models bundled under `assets/model/`."],
             ["NFR3 Portability", "No native code of the application's own; one code base for all ABIs.",
              "Java only; ONNX Runtime AAR supplies the only native library."],
             ["NFR4 Memory", "Bounded model residency; no per-page accumulation.", "One MT pair resident; "
              "recognition sessions cached per language; PDF pages processed one at a time."],
             ["NFR5 Responsiveness", "The UI thread never runs inference.", "Single background worker "
              "`falcon-engine` below normal priority; results posted via a `Handler`."],
             ["NFR6 Latency", "Seconds per page on mid-range hardware.", "Measured by RQ4 (Chapter 8)."],
             ["NFR7 Robustness", "Silent-failure components are unit-tested.", "50 JVM unit tests (Chapter 7)."],
             ["NFR8 Accessibility", "Screen-relative control sizes; labels available for icon-only controls.",
              "Dimension tokens per screen class, several deliberately below 48 dp (compact UI); tooltips "
              "and content descriptions (Chapter 7)."],
             ["NFR9 Licensing", "Third-party model licences honoured.", "Apache 2.0 (PaddleOCR) and CC-BY "
              "4.0 (OPUS-MT) attribution in the About dialog."]],
            widths=[2.8, 6.0, 7.5])

    c.h2("Design Principles", key="principles")
    c.p("Four principles recur throughout the implementation and explain many of its specific choices.")
    c.bullets([
        "**Exactness before approximation.** Where a computation can be done exactly at acceptable cost "
        "— the convex hull, the minimum-area rectangle, Viterbi segmentation — it is done exactly, and "
        "any deviation from the reference algorithm is argued to be either exact (the row-extreme hull) "
        "or a deliberate, stated change (the component-mean score).",
        "**Fail loudly where failure would otherwise be silent.** Several components can fail by "
        "producing plausible but wrong output: a recogniser with a mismatched dictionary shifts every "
        "character, a wrong decoder start token produces fluent text unrelated to the input, detector "
        "and recogniser normalisations are easily confused. The code checks each of these explicitly "
        "(for example, the dictionary size is reconciled against the class count read from the loaded "
        "graph) and the unit tests concentrate on them.",
        "**Serialise rather than synchronise.** The inference sessions are not thread-safe. Instead of "
        "locking, all inference is confined to one worker thread, which makes the concurrency argument "
        "trivial and bounds peak memory.",
        "**Degrade visibly.** When a model is missing, the application says which file; when a direction "
        "is pivoted, the language picker says so; when a translation does not fit its box even at the "
        "minimum size, the renderer flags it (and a debug mode outlines it in red).",
    ])

    c.h2("Architecture", key="arch")
    c.p("{F:arch} shows the package structure. The code is organised in four layers. The *presentation* "
        "layer (`ui`) contains the activities and widgets. The *orchestration* layer (`engine`) owns the "
        "inference engines and the worker thread, validates the model tree, and runs the pipeline. The "
        "*algorithm* layer contains one package per concern: `ocr`, `mt`, `render` and `pdf`. The "
        "*foundation* layer holds value types shared by all stages (`core`) and persistence (`data`). The "
        "inference runtime and the model assets sit below the code.")
    c.figure("arch", "architecture", "Package architecture of the system (schematic derived from the "
             "source tree). Arrows denote the principal direction of calls.", width=15.5)
    c.table("packages", "Package responsibilities",
            ["Package", "Responsibility", "Key types"],
            [["`core`", "Value types shared by all stages", "`Lang`, `Quad`, `TextLine`, `Paragraph`, `OcrResult`"],
             ["`ocr`", "Detection, cropping, orientation, recognition, grouping",
              "`PaddleOcrEngine`, `DbPostProcessor`, `CtcDecoder`, `CharDict`, `ImageOps`, `LineGrouper`"],
             ["`mt`", "Tokenisation and translation", "`SpmEncoder`, `MtVocab`, `MtConfig`, `MarianTranslator`, "
              "`PivotTranslator`"],
             ["`render`", "Repainting translated text over the page", "`LayoutRenderer`, `TextFitter`"],
             ["`pdf`", "Page rasterisation and PDF/DOCX/TXT output", "`PdfPageSource`, `PdfJob`, `DocxWriter`"],
             ["`engine`", "Engine lifetime, threading, validation, orchestration", "`Engines`, "
              "`TranslationPipeline`, `ModelValidator`, `ModelPaths`, `ScriptDetector`"],
             ["`data`", "Preferences and SQLite history", "`Prefs`, `HistoryStore`, `HistoryItem`"],
             ["`ui`", "Activities, adapters, widgets", "`MainActivity` and other activities, `LanguageBar`, "
              "`OptionRow`, `Flags`"]],
            widths=[2.0, 6.3, 8.0])
    c.p("Two interfaces decouple the pipeline from concrete engines. `OcrEngine` exposes "
        "`recognize(bitmap, lang)` and is implemented by `PaddleOcrEngine`. `Translator` exposes "
        "`supports`, `translate` and `translateAll`; it is implemented by `MarianTranslator`, and "
        "`PivotTranslator` is a decorator that implements the same interface over a delegate. The "
        "pipeline therefore sees one translator that supports all twelve directions, and the routing "
        "decision is invisible to it.")

    c.h2("Processing Pipeline and Notation", key="pipeline")
    c.p("{F:pipeline} shows the stages that `TranslationPipeline.process` executes for one bitmap. The "
        "input is a bitmap *I* of size W × H, a source language ℓ_{s} and a target language ℓ_{t}, "
        "drawn from 𝓛 = {EN, KO, JA, ZH}. Recognition produces a set of lines, each with an oriented "
        "quadrilateral q_{i}, a string x_{i}, a confidence c_{i} and a pair of colours (κ_{i}, π_{i}) for "
        "ink and paper. Lines are grouped into paragraphs 𝒫_{j}; each paragraph receives a translation "
        "y_{j}; and the renderer produces a new image Î in which each y_{j} occupies the geometry of "
        "𝒫_{j}. {T:notation} collects the notation used in the remaining chapters.")
    c.figure("pipeline", "pipeline", "Processing pipeline. All stages run on the device, serialised on "
             "one worker thread (schematic).", width=16)
    c.table("notation", "Principal notation",
            ["Symbol", "Meaning", "Default / range (source)"],
            [["I, W × H", "Input bitmap and its size in pixels", "—"],
             ["𝓛, ℓ_{s}, ℓ_{t}", "Implemented languages; source and target", "{EN, KO, JA, ZH}"],
             ["L_{max}", "Detector long-edge limit (Image Quality setting)", "640 / 960 / 1280; clamped 320–2048"],
             ["P", "Detector probability map, h × w", "values in [0, 1]"],
             ["τ_{b}", "Binarisation threshold", "0.3 (`DbPostProcessor`)"],
             ["τ_{s}", "Component score threshold", "0.6 (`DbPostProcessor`)"],
             ["r", "Unclip ratio", "1.6 (`DbPostProcessor`)"],
             ["q_{i}, x_{i}, c_{i}", "Line quadrilateral, text, confidence", "c_{i} ≥ 0.5 kept (`PaddleOcrEngine`)"],
             ["κ_{i}, π_{i}", "Estimated ink and paper colour of line i", "`ImageOps.sampleColors`"],
             ["𝒫_{j}, y_{j}", "Paragraph j and its translation", "—"],
             ["α", "Highlight opacity", "150/255 ≈ 0.59 (`LayoutRenderer`)"],
             ["γ", "Highlight growth factor", "0.06 (`LayoutRenderer`)"],
             ["h", "Median line height of a block", "—"],
             ["p, s, s*", "Preferred, candidate and fitted font size", "p = 0.82 h (`LayoutRenderer`)"]],
            widths=[3.0, 7.3, 6.0])
    c.p("The pipeline logic is short enough to state in full. The following pseudocode mirrors "
        "`TranslationPipeline.process`:")
    c.code("""ocr = ocrEngine.recognize(bitmap, source)
effectiveSource = source
if ocr not empty and options.autoDetectSource:
    guess = ScriptDetector.detect(ocr.plainText(), source)
    if not guess.isUserFacing(): guess = source          # language gating (Ch. 7)
    if guess != source:
        second = ocrEngine.recognize(bitmap, guess)       # detection runs again too
        if second not empty: ocr = second; effectiveSource = guess
if options.translate and ocr not empty and effectiveSource != target:
    translateInPlace(ocr, effectiveSource, target)        # paragraph-level, whole page batched
if options.render and ocr not empty:
    rendered = LayoutRenderer.render(bitmap, ocr, options.renderOptions)""")
    c.p("{F:dataflow} traces the data types that flow between stages. The OCR domain works in page "
        "pixels: the probability map is scaled back to page coordinates by the ratio of page size to map "
        "size, where the map's own tensor shape is taken as authoritative because the exported graph may "
        "round dimensions differently from the resizing code. The rendering domain consumes paragraphs "
        "and their translations and produces a new bitmap; the source bitmap is never modified.")
    c.figure("dataflow", "dataflow", "Data flow between stages, with the principal Java types "
             "(schematic).", width=16)
    c.table("types", "Core value types",
            ["Type", "Content", "Notes"],
            [["`Quad`", "Four corners (tl, tr, br, bl), clockwise from top-left, in page pixels",
              "Width and height are the means of opposite edge lengths; the baseline angle is the mean "
              "direction of the top and bottom edges, positive clockwise to match `Canvas.rotate`."],
             ["`TextLine`", "Quad, recognised text, confidence, foreground and background colour, "
              "per-line translation", "Per-line translation is used only by the per-line render mode and "
              "the editable text view."],
             ["`Paragraph`", "Ordered lines, source text, translated text", "Source text joins lines with a "
              "space except between two CJK characters; bounds are the union of line bounds; the "
              "median line height sets the font size."],
             ["`OcrResult`", "Ordered lines, paragraphs, page size, elapsed time", "Empty result when "
              "no box survives detection."]],
            widths=[2.2, 6.0, 8.1])
    c.p("After translation, each paragraph's translation is also distributed across its lines in "
        "proportion to the source-line lengths, preferring to break at the last space before the "
        "proportional cut. A single-line paragraph receives its translation exactly; for multi-line "
        "paragraphs the split is approximate, which is acceptable because the default renderer reflows "
        "the whole paragraph and only the per-line mode and the editable view use the split.")

    c.h2("Threading Model", key="threading")
    c.p("`Engines` is a process-wide singleton that owns one `PaddleOcrEngine`, one `PivotTranslator` and "
        "a single-thread executor named `falcon-engine`, whose thread priority is `NORM_PRIORITY − 1`. "
        "Building the engines costs seconds and tens of megabytes of native session state, so they "
        "outlive any one screen. Neither engine is thread-safe; rather than locking, every call that "
        "touches an engine is submitted to the single worker, and results are posted back to the main "
        "thread through a `Handler` bound to the main looper ({F:threading}). The serialisation is the "
        "point rather than a limitation: it makes the concurrency argument trivial and prevents two "
        "pages from holding working buffers at the same time. Parallelism is still exploited *inside* "
        "each inference call, where ONNX Runtime uses an intra-operator thread pool of "
        "max(1, min(4, cores − 1)) threads, leaving at least one core for the UI thread.")
    c.figure("threading", "threading", "Threading model: the UI thread submits work to the single "
             "engine thread, which fans out inside ONNX Runtime and posts results back (schematic).",
             width=15)
    c.p("One subtlety concerns configuration changes. The detection limit backs the user-visible Image "
        "Quality setting; `Engines.ocr()` re-applies the current preference on every access rather than "
        "only at construction, so a change takes effect on the next scan without restarting the "
        "process. The model inventory computed by `ModelValidator` is cached, because scanning the asset "
        "tree touches a few hundred entries, and can be invalidated after a debug model push.")

    c.h2("Memory Model", key="memory")
    c.p("Memory, not computation, is usually the binding constraint of on-device pipelines, because "
        "Android terminates background — and under pressure foreground — processes whose memory it "
        "needs [@android_memory]. The design bounds three contributors ({T:residency}).")
    c.table("residency", "Residency policy by component (from the source code and documentation)",
            ["Component", "Policy", "Rationale"],
            [["Detector, classifier", "Created on first use; kept for the process lifetime",
              "Language independent; needed for every page"],
             ["Recognisers", "Cached per language after first use", "Switching source language costs "
              "one extra load, not one per page"],
             ["Translation", "Exactly one directed pair resident; loading another closes the previous",
              "≈35 MB per pair; several resident pairs invite the low-memory killer"],
             ["Pivoted page", "Two pairs loaded in sequence, once each per page",
              "Whole-page batch per leg (Chapter 5)"],
             ["PDF pages", "Rasterised, processed and released one at a time",
              "Page bitmaps dominate transient memory"],
             ["Rendered output", "New ARGB_8888 copy of the page", "Source bitmap never modified"]],
            widths=[3.3, 6.5, 6.5])
    c.p("For page bitmaps the arithmetic is simple. An A4 page (8.27 × 11.69 in) rasterised at 200 dpi "
        "is 1654 × 2339 pixels; at four bytes per pixel that is about 15.5 MB (analytical). The renderer "
        "holds a second, rendered copy of the page while it works, and pages with a longer side above "
        "3000 pixels are downscaled at rasterisation (`PdfPageSource.MAX_DIMENSION`). The detector input "
        "is much smaller — at the HIGH quality level the long edge is at most 1280 pixels before rounding "
        "— and its float tensor has three channels of four bytes each.")
    c.p("Model bytes are read from the APK into a Java byte array and passed to "
        "`OrtEnvironment.createSession`. The Gradle configuration marks model files as uncompressed "
        "(`noCompress`) so that the asset's length is known and it can be read in one exact-size "
        "allocation; the byte array is transient, but the session's own copy of the weights persists "
        "for the session's lifetime. Memory-mapping the models directly would avoid the transient copy "
        "and is listed as future work in Chapter 10.")

    c.h2("Model Tree and Validation", key="models")
    c.p("All model paths are defined once in `engine/ModelPaths` and mirrored by the conversion scripts "
        "under `tools/` ({F:model_tree}). The OCR subtree holds one language-independent detector, an "
        "optional orientation classifier and four recognisers with their dictionaries. The MT subtree "
        "holds six directed English-centric pairs, each with an int8 encoder and decoder, a SentencePiece "
        "table, a vocabulary and a configuration file. Appendix B lists the inventory in full.")
    c.figure("model_tree", "model_tree", "Model tree under `assets/model/` with approximate sizes from the "
             "project documentation (schematic).", width=15)
    c.p("`ModelValidator.validate` checks the tree at start-up and returns a report of available OCR "
        "languages, available MT pairs and missing files. Two rules keep the report meaningful. Only "
        "*user-facing* languages are required, so a hidden language's missing files do not mark the "
        "installation incomplete; and only pairs involving English are required, because the CJK↔CJK "
        "pairs do not exist upstream and are expected to be pivoted. The splash screen runs the scan "
        "while the brand mark is displayed, and the home screen shows a warning that links to the model "
        "report if anything required is missing — so that the first symptom of an incomplete install is "
        "a precise message rather than a failure several taps deep.")

    c.h2("Deployment", key="deploy")
    c.p("The application targets Android API 24 as minimum and API 35 as compile and target level, is "
        "written in Java 17 and builds with Gradle 8.13. Its principal dependencies are AndroidX, "
        "Material Components, CameraX 1.4.1 and ONNX Runtime for Android 1.20.0. ABI splits produce "
        "per-architecture APKs for arm64-v8a, armeabi-v7a and x86_64 plus a universal APK. According to "
        "the project documentation the universal debug APK is about 78 MB without models and about "
        "255 MB with them, which exceeds the 150 MB limit of the Google Play store for a single APK; "
        "sideloading and internal testing work as is, and Play distribution requires moving the model "
        "tree into an install-time asset pack. The model tree itself is not versioned in the repository; "
        "a script downloads and converts it (Appendix D).")
    c.kv("deploy", "Deployment facts (repository)",
         [("Minimum / target SDK", "24 / 35"), ("Language / build", "Java 17; Gradle 8.13"),
          ("Inference runtime", "`com.microsoft.onnxruntime:onnxruntime-android:1.20.0`"),
          ("ABIs", "arm64-v8a, armeabi-v7a, x86_64, plus universal APK"),
          ("Permissions", "`CAMERA` only; no `INTERNET`"),
          ("Model tree", "≈230 MB (OCR ≈40 MB, MT ≈190 MB), fetched by `tools/fetch_models.sh`"),
          ("APK size", "≈78 MB without models; ≈255 MB with models (universal debug build)"),
          ("Licences of weights", "PaddleOCR: Apache 2.0; OPUS-MT: CC-BY 4.0 (attribution required)")])
