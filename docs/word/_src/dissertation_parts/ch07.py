"""Chapter 7: Implementation and User Interface."""


def build(c):
    c.chapter(7, "Implementation and User Interface")
    c.p("This chapter turns from algorithms to the artefact. It describes the Android implementation, "
        "the conversion of the third-party models to ONNX including a graph repair without which the "
        "runtime refuses to load several of them, the design of the user interface — screen flow, compact "
        "screen-relative control sizes, a collapsible overlay side menu and language gating — and the "
        "testing strategy.")

    c.h2("Android Implementation", key="android")
    c.p("The application consists of 50 Java source files, about 7,600 lines in total including "
        "comments, organised in the eight packages of {T:packages}. It has no Kotlin, no native code of "
        "its own and no code generation beyond Android's view binding and build configuration. Every "
        "screen derives from `BaseActivity`, which wires the toolbar, provides access to the `Engines` "
        "singleton, and implements a blocking progress overlay with a message and a detail line; a "
        "helper runs a task on the engine thread and delivers either a result or an exception to a "
        "callback on the main thread. `ProcessingActivity` factors out \"run the pipeline on one image, "
        "then show the result\", which the camera and gallery screens share.")
    c.table("screens", "Screens and their responsibilities",
            ["Activity", "Responsibility"],
            [["`SplashActivity`", "Scans the model tree while the brand mark is shown"],
             ["`MainActivity`", "Home: action tiles, language bar, collapsible side menu, model warning"],
             ["`CameraActivity`", "CameraX preview and capture, torch, gallery shortcut; then the pipeline"],
             ["`ImageImportActivity`", "One or more images; each processed in turn, earlier ones saved to "
              "history and the last shown"],
             ["`PdfActivity`", "PDF selection, page range, output format (PDF, DOCX, TXT), cancellation"],
             ["`ResultActivity`", "Rendered page alongside editable recognised and translated text; copy, "
              "text-to-speech, save"],
             ["`HistoryActivity`", "Saved translations from SQLite, loaded in pages of 200"],
             ["`TranslateActivity`", "Typed text (up to 500 characters) translated without OCR"],
             ["`LanguageActivity`", "Source/target picker; flags pivoted and unavailable pairs"],
             ["`SettingsActivity`", "Preferences and the model report"]],
            widths=[4.2, 12.1])
    c.p("Persistent settings are held by `Prefs` in a private shared-preferences file ({T:prefs}). "
        "Language preferences are read through `Lang.userFacingOr`, so a stored code for a language that "
        "is implemented but hidden resolves to the default.")
    c.table("prefs", "Persisted settings and defaults (`data/Prefs`)",
            ["Setting", "Default", "Notes"],
            [["Source language", "EN", "Hidden languages fall back to the default"],
             ["Target language", "ZH", "Hidden languages fall back to the default"],
             ["Auto-detect source script", "on", "Enables script-based verification (Chapter 4)"],
             ["Image quality", "HIGH (1280 px)", "LOW 640, MEDIUM 960"],
             ["Auto-translate", "on", "Translate after recognition"],
             ["PDF output", "PDF", "Alternatives DOCX, TXT"]],
            widths=[4.6, 3.6, 8.1])
    c.p("PDF jobs are handled by `PdfJob`. The document is copied to the application cache so that the "
        "platform's `PdfRenderer` can open a seekable descriptor; pages are rasterised at 200 dpi on a "
        "white background (transparent PDF backgrounds would otherwise reach the detector as black), "
        "processed and released one at a time; cancellation is polled between pages; and the output is "
        "written to the application's private `exports` directory. The DOCX writer is a minimal Office "
        "Open XML producer — the required package parts, one paragraph per page text, XML escaping, "
        "removal of control characters, preserved whitespace and line breaks — and is unit-tested.")

    c.h2("Model Conversion and Graph Repair", key="convert")
    c.p("The model tree is produced by two scripts. `tools/convert_ocr.py` converts the PaddleOCR "
        "inference models with paddle2onnx [@paddle2onnx] at opset 14 with dynamic axes: the PP-OCRv4 "
        "detector, the PP-OCRv4 English and Chinese recognisers, the PP-OCRv3 Korean and Japanese "
        "recognisers, and the v2.0 orientation classifier, together with their dictionaries. "
        "`tools/convert_mt.py` exports the six OPUS-MT pairs with Hugging Face Optimum [@optimum] "
        "(`ORTModelForSeq2SeqLM` with `export=True, use_cache=False`), quantises encoder and decoder "
        "dynamically to int8 with per-channel weights, flattens the source SentencePiece model into a "
        "piece/log-probability table, writes the vocabulary as a token/id table, and extracts the "
        "special-token ids and length limits into a small JSON file.")
    c.h3("The Concat rank repair")
    c.p("The PaddleOCR conversion needs a repair step. paddle2onnx emits `Concat` nodes that assemble a "
        "shape vector from a mixture of rank-1 components and rank-0 scalars. Paddle's own runtime "
        "accepts that; the ONNX specification requires all inputs of `Concat` to have the same rank, and "
        "ONNX Runtime refuses to load the graph with a shape-inference error (\"All inputs to Concat must "
        "have same rank\"). `tools/fix_onnx_concat.py` inserts an `Unsqueeze` before each rank-0 input "
        "to promote it to a one-element vector — numerically a no-op and exactly what the graph meant. "
        "It touches only `Concat` nodes whose widest input has rank 1, i.e. shape-building "
        "concatenations; concatenations of real feature tensors are left alone, because promoting a "
        "scalar there would be wrong. According to the model documentation, the PP-OCRv4 recognisers and "
        "the v2.0 classifier carry the defect, while the PP-OCRv3 recognisers and the detector do not.")
    c.h3("Quantisation settings")
    c.p("The quantisation configuration used is Optimum's `AutoQuantizationConfig.avx2(is_static=False, "
        "per_channel=True)`: dynamic quantisation, in which weights are quantised offline and activation "
        "ranges are computed at run time, so no calibration data is needed. The preset is named after an "
        "x86 instruction set; the operators it produces are standard ONNX integer operators that ONNX "
        "Runtime also executes on ARM, but whether the preset's choices are the best for ARM kernels is "
        "an efficiency question that RQ4 can answer only indirectly and that is noted as a threat to "
        "validity. The quality cost of quantisation is measured directly by the fp32-versus-int8 "
        "comparison of RQ3.")

    c.h2("User Interface Design", key="ui")
    c.p("{F:uiflow} shows the screen flow. The home screen offers four action tiles (camera "
        "recognition, PDF recognition, image import and history), a language bar with a swap button, a "
        "shortcut to typed translation, and the side menu. Every path that processes an image converges "
        "on the result screen, which shows the rendered page with the recognised and translated text; "
        "the translation stays editable, because both OCR and MT make mistakes and correcting the text "
        "is cheaper than repeating the capture.")
    c.figure("uiflow", "ui_flow", "Screen flow of the application (schematic derived from the activities "
             "and their intents).", width=16)

    c.h3("Compact, screen-relative control sizes", key="targets")
    c.p("Every control size is a named dimension token rather than a literal, with phone values in "
        "`res/values/dimens.xml` and tablet values in `res/values-sw600dp/dimens.xml`, so that all "
        "controls scale with the screen class ({T:tokens}, {F:tokens}). The current token set is "
        "deliberately compact: every control was halved relative to an earlier, larger token set, "
        "so that more of the screen is available for the page and its translation. Primary "
        "buttons are 30 dp high on phones, title-bar icon buttons 28 dp, secondary icon buttons 24 dp, "
        "list rows at least 32 dp, side-menu items 32 dp and the camera shutter 44 dp.")
    c.p("This is a conscious trade-off against accessibility guidance, and it should be stated plainly. "
        "Android recommends touch targets of at least 48 × 48 dp [@android_a11y], and WCAG 2.1's "
        "target-size criterion asks for 44 × 44 CSS pixels at level AAA [@wcag21]. On phones every "
        "interactive token is below 48 dp, the 44 dp shutter included; on tablets only the 54 dp "
        "shutter reaches it. At the nominal 160 dp per "
        "inch, 24 dp corresponds to about 3.8 mm and 32 dp to about 5.1 mm (analytical), well below the "
        "9–10 mm that Parhi et al. [@parhi2006target] found sufficient for one-handed thumb input. "
        "Error rates for small targets can therefore be expected to rise, particularly in the "
        "one-handed, standing situations in which the application is often used. The resource file "
        "records the decision and the remedy: raising the tokens restores larger targets everywhere "
        "without code changes. Measuring the effect of the compact tokens on tap accuracy, or offering "
        "a larger accessibility size set, is listed as future work; the RQ5 study concerns rendering and "
        "does not evaluate the controls.")
    c.table("tokens", "Control dimension tokens (resource files; configuration values, not measurements)",
            ["Token", "Phone (values/)", "Tablet (values-sw600dp/)", "Used for"],
            [["`icon_button_small`", "24 dp", "28 dp", "Secondary icon buttons"],
             ["`icon_button`", "28 dp", "32 dp", "Title-bar buttons, including the menu toggle"],
             ["`button_height`", "30 dp", "36 dp", "Primary buttons (text 12 sp / 14 sp)"],
             ["`row_min_height`", "32 dp", "38 dp", "Option and list rows"],
             ["`nav_item_height`", "32 dp", "40 dp", "Side-menu items (icon 15 dp / 19 dp, label 12 sp / 14 sp)"],
             ["`shutter_size`", "44 dp", "54 dp", "Camera shutter"],
             ["`tile_min_height`", "70 dp", "100 dp", "Home action tiles (icon 22 dp / 32 dp)"],
             ["`toolbar_height`", "56 dp", "64 dp", "Title bar"],
             ["`nav_rail_width`", "40 dp", "52 dp", "Collapsed side menu"],
             ["`nav_rail_expanded_width`", "104 dp", "140 dp", "Expanded side menu"]],
            widths=[4.6, 3.1, 3.9, 4.7])
    c.figure("tokens", "touch_tokens", "Principal control tokens for phones and tablets compared with the "
             "48 dp platform guidance; most compact tokens fall below it by design (values from the "
             "resource files).", width=14.5)
    c.p("The home action tiles are laid out two per row at their compact height: each row wraps its "
        "content, and the tiles have a minimum height of 70 dp (100 dp on tablets). They share the row's "
        "width equally but no longer stretch to fill the remaining screen height; the home column sits "
        "in a scroll view, so on short or landscape screens it scrolls.")

    c.h3("Collapsible overlay side menu", key="navmenu")
    c.p("Top-level destinations (home, image import, PDF, history, settings) are reachable from a side "
        "menu on the home screen ({F:nav}). Collapsed, the menu is a narrow rail of icons "
        "(`nav_rail_width`: 40 dp on phones, 52 dp on tablets). The scrolling content always reserves "
        "that width through its start margin, so the collapsed rail never covers a tile. A toggle button "
        "on the right-hand side of the title bar (`main_nav_toggle`) expands the menu: "
        "`MainActivity.applyNavState` animates the rail's width to `nav_rail_expanded_width` (104 dp / "
        "140 dp) over 220 ms with a decelerating interpolator, *over* the content rather than pushing it "
        "aside. A scrim (`nav_scrim`, 70% black) fades in behind the rail in proportion to the "
        "animation's progress, and the item labels become visible once the rail is 60% of the way "
        "open, fading in over the remaining 40% so that they are never squeezed into an ellipsis "
        "mid-animation. When collapsing, labels are hidden before the rail narrows. The menu collapses "
        "on a second press of the toggle, on a tap on the scrim, or on the system Back action, which is "
        "handled by an `OnBackPressedCallback` that is enabled only while the menu is expanded, so Back "
        "otherwise keeps its normal meaning.")
    c.figure("nav", "nav_menu", "Home screen with the side menu collapsed (a) and expanded over the "
             "content behind a scrim (b), drawn to scale for a 360 × 640 dp phone using the phone tokens "
             "(schematic).", width=14.5)
    c.p("Overlaying rather than pushing keeps the content's geometry stable: the tiles neither change "
        "size nor reflow while the menu animates, and closing the menu returns exactly the previous "
        "layout. The width arithmetic shows what pushing would cost. On a 360 dp-wide phone with 16 dp "
        "gutters and a 12 dp gap between the two tiles of a row, the collapsed rail leaves "
        "(360 − 40 − 2·16 − 12)/2 = 138 dp per tile; if the expanded 104 dp rail pushed the content, each "
        "tile would narrow to (360 − 104 − 2·16 − 12)/2 = 106 dp (analytical). With the earlier, larger "
        "token set (80 dp and 208 dp rails) the same arithmetic gave 118 dp and 54 dp, which is what "
        "originally motivated the overlay. The menu always starts collapsed and its state is not "
        "persisted, so that the tiles are never hidden behind the scrim at launch. "
        "Screen-reader accessibility is preserved in both states: every item carries its label as a content "
        "description for screen readers, collapsed items additionally show the label as a tooltip, the "
        "toggle's content description switches between \"expand\" and \"collapse\", and the scrim is "
        "excluded from accessibility focus.")

    c.h3("Language gating", key="gating")
    c.p("The engine implements four languages end to end — recognition heads and dictionaries, both "
        "translation directions for each English pair, Hangul script detection, the text-to-speech "
        "locale and the flag — but the deployed interface exposes three: English, Japanese and Chinese. "
        "Korean is withheld by a single, commented build-time list in `core/Lang.java`:")
    c.code("""private static final Lang[] USER_FACING = {
        EN,
        // KO, // Korean: implemented, hidden from the UI. Uncomment to enable.
        JA,
        ZH,
};""")
    c.p("`KO` stays in the enumeration so that code, tests, stored preferences and history rows keep "
        "compiling and resolving. Every screen, default and auto-detection path reads the list through "
        "three methods — `Lang.userFacing()`, `isUserFacing()` and `userFacingOr(code, fallback)` — "
        "instead of enumerating all values ({T:gatesites}). Re-enabling Korean means uncommenting one "
        "line, restoring the language name in the help text and updating one unit test. The mechanism "
        "separates the question \"is it implemented?\" from \"is it ready to ship?\", which is useful "
        "whenever a language's models, typography or evaluation lag behind the others — for Korean, the "
        "line-joining issue noted in Chapter 4 is one such item.")
    c.table("gatesites", "Call sites that enforce language gating",
            ["Site", "Behaviour"],
            [["`LanguageActivity`", "The picker lists user-facing languages only; search cannot find Korean"],
             ["`Prefs.sourceLang/targetLang`", "A stored \"ko\" resolves to the default (EN / ZH)"],
             ["`TranslationPipeline.process`", "A Hangul-based detection guess is ignored; the configured "
              "source is kept"],
             ["`ModelValidator.validate`", "Only user-facing languages and pairs are required and reported"],
             ["`SettingsActivity` (model report, help)", "Pivoted pairs and help text name user-facing "
              "languages only"]],
            widths=[5.6, 10.7])
    c.p("The language picker also reports what the installed models can do for each choice: a pair "
        "served through English is labelled as slower and of lower quality, and a pair with no route at "
        "all is shown as unavailable rather than failing later.")

    c.h2("Testing Strategy", key="testing")
    c.p("The unit-test suite is small and targeted: 50 JVM tests in six classes, run with `./gradlew "
        "test` and requiring neither a device nor the model tree. Its guiding principle is to test the "
        "code that fails *silently* — whose errors produce plausible output rather than exceptions — "
        "because loud failures are found anyway ({T:tests}).")
    c.table("tests", "Unit tests by class and what they protect (test names from `app/src/test`)",
            ["Test class", "Tests", "What is covered", "Silent failure prevented"],
            [["`SpmEncoderTest`", "8", "Viterbi prefers higher-scoring segmentations and splits when that "
              "scores better; unknown-character fallback; normalisation (marker prefix, whitespace "
              "collapse, blank input, NFKC); detokenisation restores spaces",
              "Wrong segmentation → fluent but wrong translation"],
             ["`CtcDecoderTest`", "8", "Repeat collapsing and blank removal; blank separating doubled "
              "characters; all-blank input; dictionary with and without space class; mismatched "
              "dictionary rejected; trailing empty line ignored", "Index shift → every character wrong"],
             ["`DbPostProcessorTest`", "9", "Single and separate blocks; unclip enlarges the raw blob; "
              "low-probability noise and tiny components ignored; scaling to source resolution; empty "
              "map; thresholds honoured", "Mis-sized or missing boxes"],
             ["`ScriptDetectorTest`", "9", "Hangul, Kana, Han, Latin; mixed Han/Kana; small Hangul share; "
              "digits and punctuation; null/empty; Kanji-only Japanese reported as Chinese",
              "Re-recognition with the wrong head"],
             ["`LangTest`", "8", "Canonical codes; `jp` alias; region suffixes; unknown codes; fallback; "
              "pair keys match model directories; Korean implemented but not user-facing; user-facing "
              "languages survive the filter", "Wrong model directory; hidden language leaking"],
             ["`DocxWriterTest`", "8", "Required package parts; one paragraph per entry; XML escaping; "
              "control characters stripped; line breaks; significant whitespace; CJK text; empty document",
              "Corrupt DOCX output"]],
            widths=[3.2, 1.2, 7.6, 4.3], font_size=8.5)
    c.p("The renderer depends on `android.graphics` and has no JVM tests; the build configures unit "
        "tests to return default values from Android stubs so that pure algorithms that merely mention "
        "Android types can run on the JVM. The renderer is checked on a device with the debug outline "
        "option against a fixed checklist: dark text on white paper; white text on a dark or coloured "
        "sign; text over a photograph or gradient; a paragraph rotated by at least 5°; and a translation "
        "much longer than its source, which must show a red overflow outline. There are no instrumented "
        "end-to-end tests with real models; the experimental protocol of Chapter 8 plays that role for "
        "accuracy, and a regression suite built from its datasets is proposed as future work.")
