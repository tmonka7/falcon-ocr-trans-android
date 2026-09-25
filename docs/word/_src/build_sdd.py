"""Builds the System Design Document (SDD) as .docx."""
from __future__ import annotations

from pathlib import Path

from docgen import Doc
from spec_data import DATE, DOC_IDS, FR, KNOWN_ISSUES, PRODUCT, VERSION

HERE = Path(__file__).resolve().parent
FIG = HERE / "figures" / "design"
OUT = HERE.parent / "02_System_Design_Document.docx"


def build() -> Path:
    d = Doc(title="System Design Document", subtitle=PRODUCT, doc_id=DOC_IDS["sdd"],
            version=VERSION, status="Baseline draft", date=DATE)
    d.cover()
    d.revision_history([
        ("1.0", DATE, "[Author]", "Initial design baseline, including translucent re-rendering, "
                                  "Korean UI gating, screen-relative sizing and the collapsible side menu."),
    ])
    d.toc()

    # 1 -------------------------------------------------------------------
    d.h(1, "1. Introduction")
    d.h(2, "1.1 Purpose and audience")
    d.p("This document describes how the system satisfies the requirements in FOT-SRS-001. It is "
        "written for developers who maintain or extend the application and for reviewers who "
        "verify the design. Screen-level detail is in FOT-SDS-001; test design is in FOT-TCS-001.")
    d.h(2, "1.2 Design goals")
    d.table(["Goal", "Design response"], [
        ("Nothing leaves the device", "No INTERNET permission; all models bundled; app-private storage only."),
        ("No native build", "Pure Java over the ONNX Runtime Java API; DB post-processing reimplemented without OpenCV/Clipper."),
        ("Fit in a phone's memory", "One engine thread; one MT pair resident; PDF pages streamed; images capped at 2400 px."),
        ("Preserve the page's look", "Geometry-, angle- and colour-aware re-rendering with a translucent highlight and halo."),
        ("Honest failure", "Model validation at start; precise messages instead of stack traces."),
        ("Usable one-handed", "Screen-relative large controls; collapsible side menu that never squeezes the tiles."),
    ], widths_cm=[4.5, 11.8], caption="Design goals")

    # 2 -------------------------------------------------------------------
    d.h(1, "2. Architecture")
    d.h(2, "2.1 Layered view")
    d.figure(FIG / "arch_layers.png", "Layered architecture", 16)
    d.p("Dependencies point downward only. The **ui** layer never calls a model directly; it submits "
        "work to **engine**, which owns the engines and the worker thread. **core** holds plain value "
        "types shared by all layers.")
    d.table(["Package", "Responsibility", "Key types"], [
        ("core", "Value types shared by every stage", "Lang, Quad, TextLine, Paragraph, OcrResult"),
        ("ocr", "Detection, cropping, orientation, recognition, grouping", "PaddleOcrEngine, DbPostProcessor, CtcDecoder, CharDict, ImageOps, LineGrouper"),
        ("mt", "Tokenisation and translation", "SpmEncoder, MtVocab, MtConfig, MarianTranslator, PivotTranslator"),
        ("render", "Re-rendering translated text", "LayoutRenderer, TextFitter"),
        ("pdf", "Rasterisation and document output", "PdfPageSource, PdfJob, DocxWriter"),
        ("engine", "Lifetime, threading, validation, orchestration", "Engines, TranslationPipeline, ModelValidator, ModelPaths, ScriptDetector, ResultHolder"),
        ("data", "Settings and history", "Prefs, HistoryStore, HistoryItem"),
        ("ui", "Activities and widgets", "MainActivity and nine other activities, LanguageBar, OptionRow, Flags"),
        ("util", "Asset and image I/O", "Assets, ImageLoader"),
    ], widths_cm=[2.2, 6, 8.1], caption="Package responsibilities")

    d.h(2, "2.2 Process and threading view")
    d.bullets([
        "**Main thread**: all views, animations (side menu), dialogs and toasts.",
        "**falcon-engine**: a single-thread executor owned by Engines, priority NORM_PRIORITY - 1. Every "
        "inference call, model validation, file save and database access runs here, serialised, because "
        "the ONNX sessions are not thread-safe.",
        "**BaseActivity.runInBackground** submits work and posts the outcome back through a main-thread "
        "Handler, only if the activity is still alive (not finishing or destroyed).",
        "ONNX sessions use min(4, cores - 1) intra-op threads with ALL_OPT graph optimisation.",
    ])
    d.figure(FIG / "seq_capture.png", "Sequence for capture, result and save", 16)

    d.h(2, "2.3 Data flow per page")
    d.figure(FIG / "pipeline.png", "Per-page processing pipeline", 16.3)

    # 3 -------------------------------------------------------------------
    d.h(1, "3. Detailed Component Design")
    d.h(2, "3.1 Engines (engine)")
    d.p("Process-wide singleton. Lazily creates PaddleOcrEngine and PivotTranslator(MarianTranslator). "
        "`ocr()` re-applies the Image Quality detection limit on every access, so a settings change takes "
        "effect on the next scan. `models()` caches the ModelValidator report. `releaseEngines()` closes "
        "native sessions while keeping the worker.")
    d.h(2, "3.2 Text detection (PaddleOcrEngine, DbPostProcessor)")
    d.table(["Step", "Design", "Parameters"], [
        ("Resize", "Scale so the long edge is at most the limit; round sides to multiples of 32", "LOW 640 / MEDIUM 960 / HIGH 1280; clamp 320-2048"),
        ("Normalise", "NCHW float, ImageNet mean/std, RGB", "-"),
        ("Binarise", "P >= threshold", "0.3"),
        ("Components", "Iterative 8-connected flood fill (explicit stack)", "min area 12 px"),
        ("Score", "Mean probability over the component's own pixels", ">= 0.6"),
        ("Outline", "Leftmost and rightmost pixel per row (exact for the hull)", "-"),
        ("Hull + rectangle", "Monotone chain; rotating calipers over hull edges", "-"),
        ("Unclip", "Grow half-extents by d = w·h·r / (2(w + h))", "r = 1.6; min side 3 px"),
        ("Output", "Ordered quad (clockwise from top-left), scaled, clamped", "max 1000 candidates"),
    ], widths_cm=[2.8, 8.5, 5], caption="Detection design")
    d.h(2, "3.3 Recognition")
    d.bullets([
        "Crop by 4-point perspective map (Matrix.setPolyToPoly); fallback to axis-aligned bounds.",
        "Optional 180° classifier (48×192); flip only if p(rotated) > 0.9.",
        "Height 48; crops sorted by aspect ratio; batches of 6; width padded to a multiple of 8 within [16, 1200].",
        "Normalisation to [-1, 1] (differs from detection).",
        "Dictionary size checked against the graph's class count; greedy CTC; drop lines with confidence < 0.5.",
        "Ink/paper colour: luminance midpoint split, minority side = ink.",
    ])
    d.h(2, "3.4 Layout analysis (LineGrouper)")
    d.table(["Rule", "Threshold"], [
        ("Same row if centre distance <", "0.6 × smaller height"),
        ("Height ratio of neighbours", "<= 1.7"),
        ("Angle difference", "<= 8°"),
        ("Vertical gap", "<= 1.6 × larger height"),
        ("Next line's centre above previous", "starts a new paragraph (column)"),
        ("Horizontal overlap / narrower width", ">= 0.25"),
    ], widths_cm=[8, 8.3], caption="Paragraph grouping rules")
    d.h(2, "3.5 Source verification (ScriptDetector)")
    d.p("Counts Hangul, Kana, Han and Latin letters in the first pass's text. Hangul > 8 % -> Korean; "
        "Kana > 8 % -> Japanese; Han >= Latin -> Chinese; any Latin -> English; else the configured "
        "source. TranslationPipeline discards a guess that is not user-facing (Section 5), and re-runs "
        "recognition only when the guess differs from the configured source. Because the test reads the "
        "first pass's output, it can only notice scripts the first-pass model can emit (KI-02).")
    d.h(2, "3.6 Translation (mt)")
    d.table(["Aspect", "Design"], [
        ("Tokeniser", "SentencePiece unigram as a piece/log-prob TSV; exact Viterbi; unknown character -10"),
        ("Encoder", "Once per chunk; input_ids + attention_mask; names resolved from the graph"),
        ("Decoder", "Greedy, cacheless (use_cache=False): n tokens cost n(n+1)/2 decoder positions"),
        ("Length limit", "min(config.maxLength, max(16, 3·source + 8))"),
        ("Chunking", "Source > 192 tokens split at . ! ? 。 ！ ？ … or newline; an overlong sentence kept whole"),
        ("Residency", "One directed pair loaded at a time (about 35 MB each)"),
        ("Pivot", "PivotTranslator: direct model if installed, else src -> en -> tgt, each leg as a page batch"),
        ("Line split", "Paragraph translation split across lines by source length, preferring spaces"),
    ], widths_cm=[3.2, 13.1], caption="Translation design")

    d.h(2, "3.7 Re-rendering (LayoutRenderer, TextFitter)")
    d.p("Rendering produces a new bitmap and never modifies the source. It works on **blocks** "
        "(a paragraph, or a line in per-line mode) and runs two passes: all highlights, then all text, "
        "so no highlight can fade text already drawn. Blocks without a translation are skipped, leaving "
        "the original untouched.")
    d.table(["Element", "Design", "Default"], [
        ("Highlight area", "Union of source quads (grown 6 %) and the layout rectangle rotated to the block angle; unioned before filling so overlaps do not darken", "-"),
        ("Highlight fill", "Sampled paper colour, translucent, rounded corners, feathered edge", "alpha 150/255; radius 0.18 h; blur 0.06 h"),
        ("Effect on the page", "Original text and paper texture keep (1 - alpha) of their contrast (about 41 %)", "-"),
        ("Size fitting", "Largest size in [0.45 p, 1.15 p] whose layout fits; bisection to 0.25 px; clip and flag overflow", "p = 0.82 × line height"),
        ("Rotation", "Canvas rotated about the target centre; median line angle; < 0.75° treated as upright", "-"),
        ("Halo", "Same layout stroked in paper colour, then filled in ink colour", "width 0.16 × text size"),
        ("Options", "highlightAlpha, halo, perLine, debugBoxes", "150, true, false, false"),
    ], widths_cm=[3.2, 9.3, 3.8], caption="Rendering design")
    d.note("The earlier design filled each line with an opaque paper colour, which gave translated text a "
           "solid background and left flat patches over photographs. Setting highlightAlpha = 255 reproduces it.",
           "Design change")

    d.h(2, "3.8 PDF processing (pdf)")
    d.bullets([
        "PdfPageSource rasterises at 200 dpi (PdfRenderer needs a seekable descriptor; persistable read permission is taken).",
        "PdfJob processes the range one page at a time; rendering is enabled only for PDF output.",
        "PDF output draws each rendered page into PdfDocument scaled back to points (physical size kept).",
        "DOCX via DocxWriter (minimal OOXML, escaping tested); TXT as UTF-8 with blank lines between pages.",
        "Cancellation polled between pages; output in filesDir/exports; a PDF history entry is written.",
    ])

    d.h(2, "3.9 Persistence (data)")
    d.p("Prefs wraps SharedPreferences (source_lang, target_lang, ocr_auto_detect, image_quality, "
        "auto_translate, pdf_output_format). HistoryStore wraps an SQLite table 'history' indexed by "
        "created_at DESC; schema upgrades drop and recreate because history is a cache. Pages are saved "
        "as JPEG (quality 90) under filesDir/pages.")

    # 4 -------------------------------------------------------------------
    d.h(1, "4. User Interface Design")
    d.h(2, "4.1 Screen architecture")
    d.p("One activity per screen. BaseActivity supplies the toolbar, the busy overlay and "
        "runInBackground. ProcessingActivity holds the shared 'image -> pipeline -> result' flow for "
        "CameraActivity and ImageImportActivity. ResultHolder passes large bitmaps to ResultActivity "
        "without serialising them (peek on recreation, clear on finish).")
    d.h(2, "4.2 Screen-relative sizing")
    d.p("All control sizes come from dimension tokens. values/dimens.xml holds phone values and "
        "values-sw600dp/dimens.xml tablet values, so every control grows with the screen class. "
        "On Home the column is match_parent inside a ScrollView with fillViewport, and the two tile "
        "rows have weight 1, so the tiles share whatever height is left; on short screens their "
        "minimum height wins and the column scrolls.")
    d.table(["Token", "Phone", "Tablet (sw600dp)", "Used by"], [
        ("button_height / button_text", "60 dp / 18 sp", "72 dp / 22 sp", "Primary, tonal, outlined buttons"),
        ("icon_button", "56 dp", "64 dp", "Toolbar and camera buttons, menu toggle"),
        ("icon_button_small", "48 dp", "56 dp", "Copy, clear, swap"),
        ("shutter_size", "88 dp", "108 dp", "Camera shutter"),
        ("row_min_height", "64 dp", "76 dp", "Settings and option rows"),
        ("tile_min_height / tile_icon / tile_title", "140 dp / 44 dp / 20 sp", "200 dp / 64 dp / 28 sp", "Home tiles"),
        ("toolbar_height", "64 dp", "72 dp", "Toolbars"),
        ("nav_rail_width / nav_rail_expanded_width", "80 / 208 dp", "104 / 280 dp", "Side menu"),
        ("nav_item_height / nav_icon / nav_label", "64 dp / 30 dp / 16 sp", "80 dp / 38 dp / 20 sp", "Side-menu items"),
    ], widths_cm=[5.6, 3.3, 3.3, 4.1], caption="Dimension tokens", font_size=8.5)
    d.h(2, "4.3 Collapsible side menu")
    d.figure(FIG / "nav_state.png", "Side-menu state machine", 15)
    d.bullets([
        "Layout: the content ScrollView has marginStart = nav_rail_width, so the collapsed rail never covers it; "
        "the scrim and the rail are later children of the same FrameLayout, the rail with 8 dp elevation.",
        "Toggle: the right-hand title-bar ImageButton main_nav_toggle; its icon and content description "
        "switch between 'menu / Expand menu' and 'menu open / Collapse menu'.",
        "Expanded: the rail animates over the content; the scrim fades in with the width; labels fade in "
        "over the last 40 % of the animation.",
        "Collapse: toggle, tap on the scrim, or Back (an OnBackPressedCallback enabled only while expanded).",
        "Accessibility: every item carries its label as content description; collapsed items also carry a tooltip.",
        "Why overlay: expanding by pushing would leave about 50 dp for each tile on a 360 dp phone, contradicting FR-22.",
    ])

    # 5 -------------------------------------------------------------------
    d.h(1, "5. Language Gating Design (Korean)")
    d.p("Lang keeps KO in the enum so code, tests, stored data and model paths still resolve. A private "
        "array Lang.USER_FACING lists the languages the interface may show, with the Korean line "
        "commented out. Every user-visible path reads that list:")
    d.table(["Site", "Mechanism"], [
        ("LanguageActivity.rebuild", "Iterates Lang.userFacing(); search cannot reach Korean"),
        ("Prefs.sourceLang / targetLang", "Lang.userFacingOr(stored, default): a stored 'ko' falls back"),
        ("TranslationPipeline.process", "A detector guess that is not user-facing is replaced by the configured source"),
        ("ModelValidator.validate", "Checks and reports user-facing languages and pairs only"),
        ("SettingsActivity", "Pivoted-pair report over user-facing languages; help text names Japanese and Chinese only"),
    ], widths_cm=[5.5, 10.8], caption="Gating sites")
    d.p("To enable Korean, uncomment `KO` in Lang.USER_FACING, restore 'Korean' in the help text and update LangTest.")

    # 6 -------------------------------------------------------------------
    d.h(1, "6. Error Handling and Security")
    d.table(["Situation", "Handling"], [
        ("Model file missing", "ModelValidator names it; Splash continues; Home shows a warning linking to Settings; engine exceptions name the asset and the fetch script"),
        ("Camera permission denied", "Toast with rationale; activity finishes"),
        ("Camera unavailable / bind failure", "Toast 'Camera unavailable'; activity finishes"),
        ("Image cannot be decoded", "Toast with message"),
        ("Inference or I/O exception on the worker", "Delivered to Callback.onError on the main thread; toast; overlay hidden"),
        ("Activity destroyed before result", "Result dropped (checked in runInBackground)"),
        ("PDF provider without persistable permission", "Falls back to the session grant"),
    ], widths_cm=[5.2, 11.1], caption="Error handling")
    d.bullets([
        "No INTERNET permission; no analytics; no third-party SDK that transmits data.",
        "Files only in app-private storage; history can be cleared by the user.",
        "PDF URIs opened read-only.",
    ])

    # 7 -------------------------------------------------------------------
    d.h(1, "7. Deployment and Build")
    d.table(["Item", "Value"], [
        ("Build", "Gradle 8.13; minSdk 24; compileSdk 35; Java"),
        ("Models", "tools/fetch_models.sh -> convert_ocr.py (paddle2onnx, opset 14, fix_onnx_concat.py) and convert_mt.py (Optimum export, dynamic int8, per channel)"),
        ("Model tree", "about 230 MB: ocr/det, ocr/cls, ocr/rec/{english,korean,japan,chinese}, mt/{en-ko,ko-en,en-ja,ja-en,en-zh,zh-en}"),
        ("APK", "about 78 MB without models, 255 MB with; Play requires an install-time asset pack"),
        ("Tests", "./gradlew test — 50 JVM unit tests"),
    ], widths_cm=[3, 13.3], caption="Build and deployment")

    # 8 -------------------------------------------------------------------
    d.h(1, "8. Design Decisions")
    d.table(["#", "Decision", "Alternatives", "Rationale"], [
        ("D1", "ONNX Runtime in Java", "Paddle Lite + C++/OpenCV", "No NDK layer; one language; same weights"),
        ("D2", "Reimplement DB post-processing", "OpenCV + Clipper", "Removes native dependencies; rectangle unclip is closed-form"),
        ("D3", "Pivot through English", "Omit CJK pairs; ship a large multilingual model", "Only English-centric OPUS-MT pairs exist; size budget"),
        ("D4", "Cacheless greedy decoder", "KV-cached decoder; beam search", "Simpler wiring; inputs are short; revisit for long documents"),
        ("D5", "Translucent highlight + halo", "Opaque erase; inpainting model", "Keeps page texture; no extra model; legibility from halo"),
        ("D6", "Korean hidden via USER_FACING", "Delete Korean code; build flavour", "Keeps the implementation; one-line re-enable; tests stay valid"),
        ("D7", "Overlay side menu, always starts collapsed", "Push layout; persist state", "Tiles keep their size on phones; Home is never covered at launch"),
        ("D8", "Dimension tokens + sw600dp", "Runtime computation of sizes", "Declarative, previewable, standard Android practice"),
    ], widths_cm=[1, 4.4, 4.6, 6.3], caption="Design decisions", font_size=8.5)

    # 9 -------------------------------------------------------------------
    d.h(1, "9. Requirements Allocation")
    d.table(["Requirement", "Components"], [(r[0] + " " + r[1], ", ".join(r[5])) for r in FR],
            widths_cm=[6, 10.3], caption="Requirement to component allocation", font_size=8.5)

    d.h(1, "10. Known Issues")
    d.table(["ID", "Area", "Description", "Handling"], KNOWN_ISSUES,
            widths_cm=[1.6, 2.8, 7.6, 4.3], caption="Known issues")
    return d.save(OUT)


if __name__ == "__main__":
    print(build())
