"""Builds the Software Requirements Specification (SRS) as .docx."""
from __future__ import annotations

from pathlib import Path

from docgen import Doc
from spec_data import (DATE, DOC_IDS, FR, GLOSSARY, KNOWN_ISSUES, NFR, PRODUCT, SCREENS, VERSION,
                       screens_for, tests_for)

OUT = Path(__file__).resolve().parents[1] / "01_Software_Requirements_Specification.docx"


def build() -> Path:
    d = Doc(title="Software Requirements Specification", subtitle=PRODUCT,
            doc_id=DOC_IDS["srs"], version=VERSION, status="Baseline draft", date=DATE)
    d.cover()
    d.revision_history([
        ("0.9", "2026-09-24", "[Author]", "Requirements derived from the implemented system."),
        ("1.0", DATE, "[Author]", "Adds translucent re-rendering (FR-11), Korean UI gating (FR-21), "
                                  "compact screen-relative controls (FR-22) and the collapsible side menu (FR-23)."),
    ])
    d.toc()

    # 1 -------------------------------------------------------------------
    d.h(1, "1. Introduction")
    d.h(2, "1.1 Purpose")
    d.p("This document specifies the functional and non-functional requirements of the "
        f"{PRODUCT}: an Android application that recognises text in photos, images and PDF pages, "
        "translates it, and paints the translation back over the page, entirely on the device. It is the "
        "reference for design (FOT-SDD-001), screen design (FOT-SDS-001) and testing (FOT-TCS-001); "
        "each requirement has a stable identifier used by those documents.")
    d.h(2, "1.2 Scope")
    d.p("In scope: image and PDF input; text detection, recognition and layout analysis; offline "
        "translation among the user-facing languages; layout-preserving re-rendering; result "
        "review, editing, speech and history; manual text translation; settings and model "
        "validation. Out of scope: any network service, user accounts, cloud sync, handwriting, "
        "vertical CJK typesetting, and languages beyond those listed in Section 2.6.")
    d.h(2, "1.3 Definitions and abbreviations")
    d.table(["Term", "Meaning"], GLOSSARY, widths_cm=[4, 12.3], caption="Glossary")
    d.h(2, "1.4 References")
    d.bullets([
        "FOT-SDD-001 System Design Document.",
        "FOT-SDS-001 Screen Design Specification.",
        "FOT-TCS-001 Test Case Specification.",
        "docs/TECHNICAL.md — technical documentation in the repository.",
        "ISO/IEC/IEEE 29148:2018 — Requirements engineering (structure followed loosely).",
        "Android Developers: accessibility guidance on touch-target size (48 dp minimum).",
    ])
    d.h(2, "1.5 Conventions")
    d.p("Requirements use **shall**. Priorities follow MoSCoW: **Must** (release-blocking), "
        "**Should** (important), **Could** (desirable). Sizes are given as *phone / tablet*; the tablet "
        "value applies when the smallest screen width is at least 600 dp.")

    # 2 -------------------------------------------------------------------
    d.h(1, "2. Overall Description")
    d.h(2, "2.1 Product perspective")
    d.p("The product is a self-contained Android application. It embeds third-party models "
        "(PaddleOCR PP-OCR for text, Helsinki-NLP OPUS-MT for translation) converted to ONNX and "
        "executed by ONNX Runtime. It has no server component and requests no network permission.")
    d.h(2, "2.2 Product functions")
    d.bullets([
        "Capture a page with the camera, or import one or several images.",
        "Translate a PDF document into a PDF, DOCX or TXT file.",
        "Detect, straighten and recognise text; order it into paragraphs.",
        "Translate offline; route CJK-to-CJK directions through English.",
        "Re-render the page with the translation in place, keeping layout and colours, with a faint "
        "highlight instead of an opaque background.",
        "Review, edit, speak and save results; browse and manage history.",
        "Translate typed text.",
        "Configure languages, recognition quality and behaviour; inspect installed models.",
    ])
    d.h(2, "2.3 User classes")
    d.table(["User class", "Characteristics", "Main needs"], [
        ("Traveller", "Occasional, often one-handed, variable light and connectivity",
         "Fast capture; simple controls; works offline"),
        ("Office / student user", "Documents and PDFs, repeated use", "PDF output, batch import, history"),
        ("Privacy-sensitive user", "Medical, legal, identity documents", "Guarantee that nothing leaves the device"),
        ("Maintainer / developer", "Builds, adds models or languages", "Clear model tree, validation, one-line language gating"),
    ], widths_cm=[3.8, 6.5, 6.0], caption="User classes")
    d.h(2, "2.4 Operating environment")
    d.kv_table([
        ("OS", "Android 7.0 (API 24) or later; compiled against API 35"),
        ("Devices", "Phones and tablets; back camera required for camera capture only"),
        ("Storage", "About 255 MB installed with models"),
        ("Runtime", "ONNX Runtime (Java API), CameraX, platform PdfRenderer, TextToSpeech, SQLite"),
    ], caption="Operating environment")
    d.h(2, "2.5 Design and implementation constraints")
    d.bullets([
        "Java only; no NDK/C++ code of the project's own.",
        "No INTERNET permission (NFR-01).",
        "Model weights are third-party and licensed separately (Apache-2.0, CC-BY 4.0).",
        "OPUS-MT offers no direct CJK-to-CJK models; those directions must be pivoted.",
        "The Google Play 150 MB base-APK limit requires models in an asset pack for Play distribution.",
    ])
    d.h(2, "2.6 Languages")
    d.p("The engine implements English, Korean, Japanese and Chinese. The user interface offers "
        "**English, Japanese and Chinese**. Korean is withheld from the interface (FR-21) while its "
        "implementation is kept in the code so that it can be enabled by uncommenting one line.")
    d.table(["Direction", "Route", "Available in UI"], [
        ("en <-> ja, en <-> zh", "Direct OPUS-MT model", "Yes"),
        ("ja <-> zh", "Pivot through English", "Yes (labelled 'via English')"),
        ("en <-> ko", "Direct OPUS-MT model", "No (hidden)"),
        ("ko <-> ja, ko <-> zh", "Pivot through English", "No (hidden)"),
    ], widths_cm=[4.5, 5.8, 6.0], caption="Translation directions")
    d.h(2, "2.7 Assumptions and dependencies")
    d.bullets([
        "The model tree has been produced by tools/fetch_models.sh before building.",
        "Text-to-speech voices are provided by the device; their absence disables Speak only.",
        "Input text is printed or typeset, horizontal, and reasonably in focus.",
    ])

    # 3 -------------------------------------------------------------------
    d.h(1, "3. External Interface Requirements")
    d.h(2, "3.1 User interfaces")
    d.p("Ten screens, specified in FOT-SDS-001. General rules:")
    d.bullets([
        "Dark theme throughout (background #070A12, surfaces #101726, brand red #E02020).",
        "Compact, screen-relative controls (FR-22): buttons 30 dp / 36 dp tall; icon buttons 28 dp / 32 dp; "
        "small icon buttons 24 dp / 28 dp; home tiles about 70 dp / 100 dp. Several touch targets are below the "
        "48 dp accessibility guideline by design (KI-07).",
        "Home has a side menu collapsed to icons by default; the right-hand title-bar button expands "
        "it over the content (FR-23).",
        "Long operations show a blocking progress overlay with an optional detail line (e.g. 'Page 3 of 12').",
        "Errors are shown as toasts or dialogs with the underlying message; the app does not crash.",
    ])
    d.table(["ID", "Screen", "Main requirements"],
            [(s["id"], s["name"], ", ".join(s["reqs"])) for s in SCREENS],
            widths_cm=[2.2, 5, 9.1], caption="Screens")
    d.h(2, "3.2 Hardware interfaces")
    d.bullets(["Back camera through CameraX (optional flash).", "Device storage through the Storage Access Framework pickers."])
    d.h(2, "3.3 Software interfaces")
    d.table(["Interface", "Use"], [
        ("ONNX Runtime", "Executes detection, classification, recognition, encoder and decoder graphs."),
        ("CameraX", "Preview and still capture."),
        ("android.graphics.pdf.PdfRenderer / PdfDocument", "Rasterise input PDFs at 200 dpi; write output PDFs."),
        ("TextToSpeech", "Speak translations."),
        ("SQLite", "History database."),
        ("SharedPreferences", "Settings (Section 5.2)."),
        ("Storage Access Framework", "Open images and PDFs; persistable read permission for PDFs."),
    ], widths_cm=[6, 10.3], caption="Software interfaces")
    d.h(2, "3.4 Communications interfaces")
    d.p("None. The application performs no network communication (NFR-01).")

    # 4 -------------------------------------------------------------------
    d.h(1, "4. Functional Requirements")
    d.p("Each requirement lists the screens that expose it and the test cases that verify it.")
    for rid, title, text, prio, _scr, comps in FR:
        d.h(3, f"{rid} {title}")
        d.kv_table([
            ("ID", rid),
            ("Priority", prio),
            ("Requirement", text),
            ("Screens", ", ".join(screens_for(rid)) or "(engine, no dedicated screen)"),
            ("Realised by", ", ".join(comps)),
            ("Verified by", ", ".join(tests_for(rid)) or "-"),
        ], widths_cm=(3.2, 13.1))

    # 5 -------------------------------------------------------------------
    d.h(1, "5. Data Requirements")
    d.h(2, "5.1 History database")
    d.table(["Column", "Type", "Constraint", "Meaning"], [
        ("_id", "INTEGER", "PRIMARY KEY AUTOINCREMENT", "Row id"),
        ("kind", "TEXT", "NOT NULL", "IMAGE, CAMERA, PDF or MANUAL"),
        ("source_lang", "TEXT", "NOT NULL", "Language code, e.g. 'ja'"),
        ("target_lang", "TEXT", "NOT NULL", "Language code"),
        ("source_text", "TEXT", "NOT NULL", "Recognised or typed text"),
        ("translated_text", "TEXT", "NOT NULL", "Translation as saved (after edits)"),
        ("image_path", "TEXT", "nullable", "JPEG under filesDir/pages, if any"),
        ("created_at", "INTEGER", "NOT NULL, indexed DESC", "Epoch milliseconds"),
    ], widths_cm=[3.3, 2.2, 4.5, 6.3], caption="Table 'history'")
    d.h(2, "5.2 Preferences")
    d.table(["Key", "Values", "Default"], [
        ("source_lang", "en, ja, zh (a stored 'ko' falls back to the default)", "en"),
        ("target_lang", "en, ja, zh (a stored 'ko' falls back to the default)", "zh"),
        ("ocr_auto_detect", "true / false", "true"),
        ("image_quality", "LOW, MEDIUM, HIGH", "HIGH"),
        ("auto_translate", "true / false", "true"),
        ("pdf_output_format", "PDF, DOCX, TXT", "PDF"),
    ], widths_cm=[4, 8.8, 3.5], caption="Stored preferences")
    d.p("The side-menu state is intentionally not stored: the menu always starts collapsed (FR-23).")
    d.h(2, "5.3 Files")
    d.bullets([
        "filesDir/pages/*.jpg — saved result pages (JPEG quality 90).",
        "filesDir/exports/translated_<millis>.<pdf|docx|txt> — PDF job outputs.",
        "assets/model/** — bundled models (read-only).",
    ])

    # 6 -------------------------------------------------------------------
    d.h(1, "6. Non-functional Requirements")
    d.table(["ID", "Category", "Requirement", "Verification"],
            [(a, b, c, e) for a, b, c, e in NFR], widths_cm=[1.9, 2.8, 7.4, 4.2],
            caption="Non-functional requirements")

    # 7 -------------------------------------------------------------------
    d.h(1, "7. Traceability Matrix")
    rows = [(rid, title, prio, ", ".join(screens_for(rid)) or "-", ", ".join(tests_for(rid)) or "-")
            for rid, title, _t, prio, _s, _c in FR]
    rows += [(rid, cat, "-", "-", ", ".join(tests_for(rid)) or "review") for rid, cat, _t, _v in NFR]
    d.table(["Req.", "Title", "Priority", "Screens", "Test cases"], rows,
            widths_cm=[1.8, 4.4, 1.7, 3.6, 4.8], caption="Requirements to screens and tests", font_size=8)

    d.h(1, "Appendix A. Known Issues and Limitations")
    d.table(["ID", "Area", "Description", "Handling"], KNOWN_ISSUES,
            widths_cm=[1.6, 2.8, 7.6, 4.3], caption="Known issues")
    return d.save(OUT)


if __name__ == "__main__":
    print(build())
