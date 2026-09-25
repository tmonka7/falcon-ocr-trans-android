"""References (IEEE numeric, order of first citation) and Appendices A–D.

Appendices must not cite: the reference list is emitted before them."""
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Cm, Pt

from .refs import REFS


def _references(c):
    c.d.page_break()
    c.d.chapter("")
    c.d.h(1, "References")
    for i, key in enumerate(c.cite_order, 1):
        para = c.d.d.add_paragraph()
        para.alignment = WD_ALIGN_PARAGRAPH.LEFT
        pf = para.paragraph_format
        pf.left_indent = Cm(1.0)
        pf.first_line_indent = Cm(-1.0)
        pf.space_after = Pt(3)
        pf.line_spacing = 1.15
        pf.tab_stops.add_tab_stop(Cm(1.0))
        c.d._fill(para, f"[{i}]\t{REFS[key]}", size=10.5)


def _appendix_a(c):
    c.appendix("A", "Parameter Table")
    c.p("Every threshold and constant quoted in this dissertation, with the file that defines it. Paths "
        "are relative to `app/src/main/java/com/falcon/ocrtrans/` unless they start with `app/` or "
        "`tools/`. Values were read from the source code at the time of writing.")
    rows = [
        ["Detector long-edge limit (LOW / MEDIUM / HIGH)", "640 / 960 / 1280 px", "`data/Prefs.java` (`ImageQuality`)"],
        ["Stored Image Quality default", "HIGH", "`data/Prefs.java`"],
        ["Engine default detection limit; clamp", "960 px; 320–2048 px", "`ocr/PaddleOcrEngine.java`"],
        ["Detector side rounding; minimum side", "multiple of 32; 32 px", "`ocr/ImageOps.java`"],
        ["Detector normalisation", "ImageNet mean (0.485, 0.456, 0.406), std (0.229, 0.224, 0.225)", "`ocr/ImageOps.java`"],
        ["Binarisation threshold τ_{b}", "0.3", "`ocr/DbPostProcessor.java`"],
        ["Component score threshold τ_{s}", "0.6", "`ocr/DbPostProcessor.java`"],
        ["Unclip ratio r", "1.6", "`ocr/DbPostProcessor.java`"],
        ["Minimum component area", "12 px", "`ocr/DbPostProcessor.java`"],
        ["Minimum box side (before unclip)", "3 px", "`ocr/DbPostProcessor.java`"],
        ["Maximum candidates per map", "1000", "`ocr/DbPostProcessor.java`"],
        ["Flood-fill connectivity; initial stack", "8; min(hw, 65 536) entries", "`ocr/DbPostProcessor.java`"],
        ["Crop size cap", "4096 px per side", "`ocr/ImageOps.java`"],
        ["Classifier input; flip threshold", "48 × 192; p > 0.9", "`ocr/PaddleOcrEngine.java`"],
        ["Recogniser input height", "48 px", "`ocr/PaddleOcrEngine.java`"],
        ["Recognition batch size", "6", "`ocr/PaddleOcrEngine.java`"],
        ["Padded width rounding; clamp", "multiple of 8; 16–1200 px", "`ocr/PaddleOcrEngine.java`"],
        ["Recogniser normalisation", "[−1, 1]", "`ocr/ImageOps.java`"],
        ["Minimum line confidence", "0.5", "`ocr/PaddleOcrEngine.java`"],
        ["Colour sampling budget", "≈4096 pixels", "`ocr/ImageOps.java`"],
        ["Luminance weights", "299 / 587 / 114 (÷1000)", "`ocr/ImageOps.java`"],
        ["Row tolerance (reading order)", "0.6 × smaller height", "`ocr/LineGrouper.java`"],
        ["Maximum line gap", "1.6 × larger height", "`ocr/LineGrouper.java`"],
        ["Maximum height ratio", "1.7", "`ocr/LineGrouper.java`"],
        ["Maximum angle difference", "8°", "`ocr/LineGrouper.java`"],
        ["Minimum horizontal overlap", "0.25 of narrower line", "`ocr/LineGrouper.java`"],
        ["Script share threshold", "0.08", "`engine/ScriptDetector.java`"],
        ["Intra-op threads; optimisation", "max(1, min(4, cores − 1)); ALL_OPT", "`ocr/PaddleOcrEngine.java`, `mt/MarianTranslator.java`"],
        ["Worker thread priority", "NORM_PRIORITY − 1", "`engine/Engines.java`"],
        ["Unknown-character penalty", "−10", "`mt/SpmEncoder.java`"],
        ["Chunk budget", "192 source tokens", "`mt/MarianTranslator.java`"],
        ["Length safety factor; floor; offset", "3; 16; +8", "`mt/MarianTranslator.java`"],
        ["MT config fallbacks (pad, eos, unk, max length)", "58100, 0, 1, 256 (clamped 8–512)", "`mt/MtConfig.java`"],
        ["Pivot language", "English", "`mt/PivotTranslator.java`"],
        ["Highlight alpha (default)", "150 / 255", "`render/LayoutRenderer.java`"],
        ["Highlight growth γ", "0.06", "`render/LayoutRenderer.java`"],
        ["Angle epsilon", "0.75°", "`render/LayoutRenderer.java`"],
        ["Corner radius; edge softness", "0.18 h; 0.06 h", "`render/LayoutRenderer.java`"],
        ["Halo width", "0.16 s", "`render/LayoutRenderer.java`"],
        ["Preferred size from line height", "0.82", "`render/LayoutRenderer.java`"],
        ["Size bounds; bisection precision", "0.45p – 1.15p (≥ 4 px); 0.25 px", "`render/TextFitter.java`"],
        ["PDF rasterisation; maximum dimension", "200 dpi; 3000 px", "`pdf/PdfPageSource.java`"],
        ["PDF output scale", "72 / 200", "`pdf/PdfJob.java`"],
        ["Typed-translation limit", "500 characters", "`ui/TranslateActivity.java`"],
        ["History page size", "200", "`ui/HistoryActivity.java`"],
        ["Side-menu animation", "220 ms; labels from 60% progress", "`ui/MainActivity.java`"],
        ["Scrim colour", "#B3000000 (70% black)", "`app/src/main/res/values/colors.xml`"],
        ["Dimension tokens (phone / tablet)", "see Table {T:tokens}", "`app/src/main/res/values*/dimens.xml`"],
        ["ONNX opset for OCR conversion", "14", "`tools/convert_ocr.py`"],
        ["MT quantisation", "dynamic int8, per channel", "`tools/convert_mt.py`"],
    ]
    c.table("params", "Parameters and their sources", ["Parameter", "Value", "Source file"], rows,
            widths=[5.6, 5.2, 5.5], font_size=8.5)


def _appendix_b(c):
    c.appendix("B", "Model Inventory")
    c.p("The model tree is not stored in the repository; `tools/fetch_models.sh` downloads and converts "
        "it. Sizes are the approximate figures given in the project's model documentation.")
    c.table("inv", "Model inventory under `app/src/main/assets/model/`",
            ["Path", "Source release", "Role", "Notes"],
            [["`ocr/det/det.onnx`", "ch_PP-OCRv4_det", "Text detection (DB)", "Language independent"],
             ["`ocr/cls/cls.onnx`", "PP-OCR v2.0 angle classifier", "180° orientation", "Optional; Concat repair"],
             ["`ocr/rec/english/`", "en_PP-OCRv4_rec + en_dict.txt", "English recognition", "Concat repair"],
             ["`ocr/rec/korean/`", "korean_PP-OCRv3_rec + korean_dict.txt", "Korean recognition",
              "Bundled; hidden in UI"],
             ["`ocr/rec/japan/`", "japan_PP-OCRv3_rec + japan_dict.txt", "Japanese recognition", "—"],
             ["`ocr/rec/chinese/`", "ch_PP-OCRv4_rec + ppocr_keys_v1.txt", "Chinese recognition", "Concat repair"],
             ["`mt/en-ko/`", "Helsinki-NLP/opus-mt-tc-big-en-ko", "EN → KO", "tc-big release; hidden in UI"],
             ["`mt/ko-en/`", "Helsinki-NLP/opus-mt-ko-en", "KO → EN", "Hidden in UI"],
             ["`mt/en-ja/`", "Helsinki-NLP/opus-mt-en-jap", "EN → JA", "Check model card (Chapter 5)"],
             ["`mt/ja-en/`", "Helsinki-NLP/opus-mt-ja-en", "JA → EN", "—"],
             ["`mt/en-zh/`", "Helsinki-NLP/opus-mt-en-zh", "EN → ZH", "—"],
             ["`mt/zh-en/`", "Helsinki-NLP/opus-mt-zh-en", "ZH → EN", "—"]],
            widths=[3.3, 5.5, 3.4, 4.1], font_size=8.5)
    c.table("invsize", "Approximate sizes (project documentation)",
            ["Component", "Approximate size"],
            [["OCR detection + classifier", "5 MB"], ["OCR recognition × 4 scripts", "35 MB"],
             ["OPUS-MT int8 × 6 directed pairs", "190 MB (≈35 MB per pair)"], ["Total", "≈230 MB"]],
            widths=[8.0, 8.3])
    c.p("Each MT directory contains `encoder.int8.onnx`, `decoder.int8.onnx`, `source.spm.tsv` "
        "(piece and log-probability), `vocab.tsv` (token and id) and `config.json` (special-token ids "
        "and decoding limits). Licences: PaddleOCR weights Apache 2.0; OPUS-MT weights CC-BY 4.0, which "
        "requires attribution in the shipped application.")


def _appendix_c(c):
    c.appendix("C", "User-Study Materials")
    c.p("This appendix is a placeholder for the materials of the RQ5 study, to be inserted after "
        "approval by the institutional review board.")
    c.table("studymat", "User-study materials (placeholders)",
            ["Item", "Content", "Status"],
            [["C.1 Information sheet", "[Placeholder]", "[TBD]"], ["C.2 Consent form", "[Placeholder]", "[TBD]"],
             ["C.3 Demographic questionnaire", "[Placeholder]", "[TBD]"],
             ["C.4 Instructions to participants", "[Placeholder]", "[TBD]"],
             ["C.5 Rating items (legibility, naturalness)", "5-point items as worded in Chapter 8", "Draft"],
             ["C.6 Pairwise preference protocol", "[Placeholder]", "[TBD]"],
             ["C.7 System Usability Scale", "Standard ten items", "Draft"],
             ["C.8 Stimulus list and licences", "[Placeholder]", "[TBD]"],
             ["C.9 Ethics approval reference", "[Placeholder]", "[TBD]"]],
            widths=[5.5, 7.3, 3.5])


def _appendix_d(c):
    c.appendix("D", "Reproducibility and Build Instructions")
    c.h2("Building the application")
    c.p("Requirements: a JDK 17, the Android SDK with platform 35, and Python 3 for the model scripts. "
        "From the repository root:")
    c.code("""tools/fetch_models.sh          # once; downloads and converts ~230 MB of models
tools/fetch_models.sh --ocr-only   # PaddleOCR only
tools/fetch_models.sh --mt-only    # OPUS-MT only
./gradlew test                 # 50 JVM unit tests; no device or models needed
./gradlew assembleDebug        # per-ABI and universal debug APKs""")
    c.p("The model conversion needs `paddle2onnx` for OCR and `optimum[onnxruntime]`, `transformers` and "
        "`sentencepiece` for MT. The application validates the model tree at start-up and names any "
        "missing file.")
    c.h2("Checking the renderer")
    c.p("Enable `LayoutRenderer.Options.debugBoxes` and process, on a device: dark text on white paper; "
        "white text on a dark or coloured sign; text over a photograph or gradient; a paragraph rotated "
        "by at least 5°; and a translation much longer than its source, which must show a red overflow "
        "outline.")
    c.h2("Re-enabling Korean")
    c.p("Uncomment `KO` in `Lang.USER_FACING`, restore Korean in the help text of "
        "`SettingsActivity.showHelp`, and update `LangTest.koreanIsImplementedButNotUserFacing`.")
    c.h2("Regenerating this document")
    c.p("This dissertation is generated from Python sources in `docs/word/_src/` "
        "(`build_dissertation.py` and the `dissertation_parts` package), which draw every figure with "
        "matplotlib and PIL and write the Word file with python-docx:")
    c.code("python docs/word/_src/build_dissertation.py")
    c.p("The table of contents and the lists of tables and figures are Word fields; Word updates them "
        "when the document is opened (or via Update Field).")
    c.h2("Recording an experimental run")
    c.p("For every run of the Chapter 8 protocol record: the git commit of the application; SHA-256 "
        "checksums of every model file; ONNX Runtime and Optimum versions; device model, SoC, RAM, "
        "Android version and build number; quality level; random seeds of bootstrap procedures; and "
        "the sacreBLEU and COMET signatures.")


def build(c):
    _references(c)
    _appendix_a(c)
    _appendix_b(c)
    _appendix_c(c)
    _appendix_d(c)
