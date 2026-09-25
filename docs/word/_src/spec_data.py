"""Single source of truth for requirement, screen and test-case identifiers.

The SRS, the System Design Document, the Screen Design Specification and the
Test Case Specification all import from here, so an ID means the same thing in
every document and the traceability matrices cannot drift apart.

Everything here describes the code as it stands in this repository; when the
code changes, change this file and rebuild (see build_all.py).
"""
from __future__ import annotations

PROJECT = "falcon-ocr-trans"
PRODUCT = "OCR Translator (falcon-ocr-trans for Android)"
DATE = "2026-09-25"
VERSION = "1.0"

DOC_IDS = {
    "srs": "FOT-SRS-001",
    "sdd": "FOT-SDD-001",
    "sds": "FOT-SDS-001",   # screen design specification
    "tcs": "FOT-TCS-001",
}

# --------------------------------------------------------------------------
# Functional requirements: (id, title, statement, priority, screens, components)
# priority: Must / Should / Could (MoSCoW)
# --------------------------------------------------------------------------
FR = [
    ("FR-01", "Camera capture",
     "The system shall capture a still image with the device's back camera, apply the capture's "
     "rotation so the image is upright, and pass it to the processing pipeline. Camera access "
     "shall be requested at runtime; if refused, the screen shall explain why and close.",
     "Must", ["SCR-03"], ["CameraActivity", "ImageOps.rotate"]),
    ("FR-02", "Single image import",
     "The system shall let the user pick one image from the device (camera screen gallery "
     "buttons) and process it exactly as a captured photo.",
     "Must", ["SCR-03", "SCR-04"], ["CameraActivity", "ImageLoader"]),
    ("FR-03", "Batch image import",
     "The system shall let the user select several images, process them in order, save every "
     "result to history, report progress as 'Page i of n', and open the last result.",
     "Should", ["SCR-04"], ["ImageImportActivity", "HistoryStore"]),
    ("FR-04", "PDF input and job options",
     "The system shall let the user choose a PDF, show its size and page count, choose a page "
     "range (All Pages, 1-5, 1-10, 1-20) and an output format (PDF, DOCX, TXT), and clear the "
     "selection.",
     "Must", ["SCR-07"], ["PdfActivity", "PdfPageSource"]),
    ("FR-05", "Text detection",
     "The system shall locate text regions as oriented quadrilaterals using PP-OCRv4 "
     "Differentiable-Binarization detection with library-free post-processing "
     "(binary threshold 0.3, box threshold 0.6, unclip ratio 1.6, minimum area 12 px, minimum "
     "side 3 px).",
     "Must", [], ["PaddleOcrEngine.detect", "DbPostProcessor"]),
    ("FR-06", "Orientation correction",
     "When the optional angle classifier is installed, the system shall rotate a line crop by "
     "180 degrees if the classifier's confidence that it is upside down exceeds 0.9.",
     "Should", [], ["PaddleOcrEngine.classifyAndFlip"]),
    ("FR-07", "Text recognition",
     "The system shall recognise each detected line with the recognition model of the source "
     "language, decode it with greedy CTC, and discard empty lines and lines with confidence "
     "below 0.5.",
     "Must", [], ["PaddleOcrEngine.recognizeCrops", "CtcDecoder", "CharDict"]),
    ("FR-08", "Reading order and paragraphs",
     "The system shall order lines top-to-bottom and left-to-right and group them into "
     "paragraphs by height ratio (<= 1.7), angle difference (<= 8 deg), vertical gap "
     "(<= 1.6 line heights) and horizontal overlap (>= 25 %).",
     "Must", [], ["LineGrouper", "Paragraph"]),
    ("FR-09", "Source script auto-detection",
     "When 'OCR Language' is set to Auto, the system shall classify the recognised text by "
     "script and, if it disagrees with the configured source language and names a user-facing "
     "language, recognise the page again with the matching model.",
     "Should", ["SCR-09"], ["ScriptDetector", "TranslationPipeline"]),
    ("FR-10", "Translation",
     "The system shall translate each paragraph between any two user-facing languages "
     "offline with OPUS-MT. Directions with no direct model shall be routed through English, "
     "and the interface shall label them 'via English - slower, lower quality'.",
     "Must", ["SCR-06", "SCR-10"], ["MarianTranslator", "PivotTranslator", "SpmEncoder"]),
    ("FR-11", "Layout-preserving re-rendering",
     "The system shall paint each translation back over the region of its source paragraph: "
     "a faint, soft-edged highlight in the sampled paper colour (alpha 150/255), then the text "
     "at the largest size that fits, rotated to the paragraph angle, in the sampled ink colour "
     "with a paper-coloured halo. The translated text shall have no opaque background of its own. "
     "Paragraphs with no translation shall be left untouched.",
     "Must", ["SCR-05"], ["LayoutRenderer", "TextFitter"]),
    ("FR-12", "Result presentation",
     "The system shall show the rendered page, a direction badge (e.g. JA -> EN), the recognised "
     "source text, and an editable translation, and let the user switch between the rendered "
     "and original image.",
     "Must", ["SCR-05"], ["ResultActivity", "ResultHolder"]),
    ("FR-13", "Speech output",
     "The system shall read the (possibly edited) translation aloud with the platform "
     "text-to-speech engine in the target language, and disable the Speak button when no voice "
     "is available for that language.",
     "Could", ["SCR-05"], ["ResultActivity.initTts"]),
    ("FR-14", "Save to history",
     "The system shall save a result (page image as JPEG in app storage, source and translated "
     "text, languages, kind, timestamp) to the local history database on request.",
     "Must", ["SCR-05"], ["HistoryStore", "ImageLoader.saveToAppStorage"]),
    ("FR-15", "History management",
     "The system shall list up to 200 most recent history entries, newest first, with kind icon, "
     "first line of text, direction and timestamp; show an entry's texts on tap; delete one on "
     "long-press after confirmation; and clear all after confirmation.",
     "Should", ["SCR-08"], ["HistoryActivity", "HistoryStore"]),
    ("FR-16", "Manual text translation",
     "The system shall translate typed text of up to 500 characters, show a character counter, "
     "copy input or output to the clipboard, warn when the direction is pivoted, and save each "
     "translation to history.",
     "Should", ["SCR-10"], ["TranslateActivity"]),
    ("FR-17", "Language selection",
     "The system shall let the user choose source and target languages on separate tabs from "
     "the user-facing languages, search by English name, native name or code, mark the current "
     "choice, annotate unavailable or pivoted choices, and swap the pair from the language bar.",
     "Must", ["SCR-06", "SCR-02", "SCR-07", "SCR-10"], ["LanguageActivity", "LanguageBar", "Prefs"]),
    ("FR-18", "Settings",
     "The system shall provide: OCR Language (Auto / fixed), Image Quality (LOW 640, MEDIUM 960, "
     "HIGH 1280 px), Auto Translation on/off, default source and target languages, an installed-"
     "model report, About (with model licences), and Help.",
     "Must", ["SCR-09"], ["SettingsActivity", "Prefs", "Engines.ocr"]),
    ("FR-19", "Model validation",
     "At start-up the system shall check the bundled model tree, name every missing file, and "
     "show a warning on the home screen instead of failing later inside inference.",
     "Must", ["SCR-01", "SCR-02", "SCR-09"], ["ModelValidator", "SplashActivity"]),
    ("FR-20", "PDF job execution",
     "The system shall process the chosen pages one at a time with per-page progress, allow "
     "cancellation with Back, write the output to app-private storage, show its path and text, "
     "and record the job in history.",
     "Must", ["SCR-07"], ["PdfJob", "DocxWriter", "PdfActivity"]),
    ("FR-21", "Korean withheld from the interface",
     "Korean shall remain implemented in the engine but shall not appear anywhere in the user "
     "interface: not in pickers or search, not restored from preferences, not chosen by "
     "auto-detection, not listed in the model report or help text. Enabling it shall need only "
     "uncommenting one line in Lang.USER_FACING.",
     "Must", ["SCR-06", "SCR-09"], ["Lang", "Prefs", "TranslationPipeline", "ModelValidator"]),
    ("FR-22", "Compact, screen-relative controls",
     "Controls shall be compact and sized from dimension tokens that scale with the screen class: "
     "primary, tonal and outlined buttons 30 dp tall with 12 sp text (36 dp / 14 sp on tablets); "
     "icon buttons 28 dp (32 dp); small icon buttons 24 dp (28 dp); camera shutter 44 dp (54 dp); "
     "option rows at least 32 dp (38 dp); home tiles at least 70 dp (100 dp), wrapping to their "
     "content rather than filling the screen.",
     "Must", ["SCR-02", "SCR-03", "SCR-04", "SCR-05", "SCR-07", "SCR-10"],
     ["dimens.xml", "values-sw600dp/dimens.xml", "themes.xml"]),
    ("FR-23", "Collapsible side menu",
     "The home side menu shall be collapsed (icons only, 40 dp / 52 dp) by default and "
     "expand to 104 dp / 140 dp with labels when the user presses the right-hand button of "
     "the title bar. Expanded, it shall overlay the content behind a scrim; pressing the "
     "button again, tapping the scrim, or pressing Back shall collapse it. Collapsed icons "
     "shall expose their label as tooltip and content description.",
     "Must", ["SCR-02"], ["MainActivity.bindNavToggle", "activity_main.xml", "item_nav.xml"]),
    ("FR-24", "Recognition without translation",
     "When Auto Translation is off, the system shall recognise text and show it without "
     "translating.",
     "Could", ["SCR-05", "SCR-09"], ["TranslationPipeline.Options.translate"]),
]

# --------------------------------------------------------------------------
# Non-functional requirements: (id, category, statement, measure / verification)
# --------------------------------------------------------------------------
NFR = [
    ("NFR-01", "Privacy / offline",
     "The application shall not request the INTERNET permission, and no image or text shall "
     "leave the device.",
     "Inspect merged manifest; run with network disabled (TC-NFR-01)."),
    ("NFR-02", "Data protection",
     "Saved pages, exports and history shall be stored only in app-private storage "
     "(filesDir/pages, filesDir/exports, the SQLite database).",
     "Code review of ImageLoader, PdfJob, HistoryStore; device file inspection."),
    ("NFR-03", "Responsiveness",
     "All inference shall run off the UI thread on a single worker thread below normal "
     "priority; the UI shall remain responsive (no ANR) while a page is processed, and a "
     "blocking progress overlay shall be shown.",
     "Manual test with StrictMode / ANR monitoring (TC-NFR-03)."),
    ("NFR-04", "Performance target",
     "Target: one photographed page at quality HIGH processed end to end within 10 s on a "
     "mid-tier device (direct translation direction). This is a target to be confirmed by "
     "measurement, not a measured value.",
     "Latency protocol in the Test Case Specification (TC-NFR-04)."),
    ("NFR-05", "Memory",
     "At most one translation model pair shall be resident; PDF pages shall be processed one "
     "at a time; decoded images shall be down-sampled to a long edge below 2400 px.",
     "Code review; heap profile during a 20-page PDF job (TC-NFR-05)."),
    ("NFR-06", "Usability",
     "Primary actions shall be reachable with one tap from Home; controls shall meet the sizes "
     "of FR-22; the dark theme shall be used throughout.",
     "Screen design review; usability walkthrough."),
    ("NFR-07", "Accessibility",
     "Every icon-only control shall have a content description; collapsed side-menu items "
     "shall have tooltips. Deviation: to meet FR-22's compact sizes, several touch targets are "
     "below Android's 48 dp guideline (see KI-07).",
     "Android Accessibility Scanner; TalkBack walkthrough (TC-NFR-07)."),
    ("NFR-08", "Compatibility",
     "The application shall run on Android 7.0 (API 24) and later, on phones and on tablets "
     "(smallest width >= 600 dp uses larger dimension tokens).",
     "Test matrix in the Test Case Specification."),
    ("NFR-09", "Robustness",
     "Missing models, unreadable images and failed inference shall be reported with a precise "
     "message and shall not crash the application.",
     "Negative tests TC-19-x, TC-02-3."),
    ("NFR-10", "Maintainability",
     "Code shall be Java without an NDK layer; model paths shall be defined once "
     "(ModelPaths); components whose failures are silent shall have JVM unit tests.",
     "Code review; ./gradlew test (50 tests)."),
    ("NFR-11", "Licensing",
     "The About dialog shall attribute PaddleOCR (Apache-2.0), OPUS-MT (CC-BY 4.0) and ONNX "
     "Runtime.",
     "Manual check (TC-18-6)."),
    ("NFR-12", "Distribution size",
     "The universal APK is about 78 MB without models and about 255 MB with them; Play "
     "distribution requires moving models to an install-time asset pack.",
     "Build output inspection."),
]

# --------------------------------------------------------------------------
# Screens: id -> dict
# components: (callout no, name, widget, view id, size (phone / tablet), behaviour)
# --------------------------------------------------------------------------
SCREENS = [
    dict(id="SCR-01", name="Splash", activity="SplashActivity", layout="activity_splash.xml",
         image="01_splash.png", reqs=["FR-19"],
         purpose="Brand screen shown at launch while the model tree is validated.",
         entry="Application launch (LAUNCHER activity).",
         exit="Automatically to SCR-02 when validation completes (success or failure).",
         components=[
             (1, "Brand mark", "ImageView", "-", "-", "Static."),
             (2, "App name and tagline", "TextView", "-", "22 sp / 13 sp", "Static."),
             (3, "Progress", "ProgressBar", "splash_progress", "-", "Indeterminate while validating."),
             (4, "Status", "TextView", "splash_status", "12 sp",
              "'Working…', then tagline, or 'Models are not installed' / 'Something went wrong'."),
         ]),
    dict(id="SCR-02", name="Home", activity="MainActivity", layout="activity_main.xml",
         image="02_home_collapsed.png", image2="02_home_expanded.png",
         reqs=["FR-17", "FR-19", "FR-22", "FR-23"],
         purpose="Entry point: action tiles, language pair, manual translation, side menu.",
         entry="From SCR-01; Home item in the side menu.",
         exit="Tiles and menu items to SCR-03/04/07/08/09; language bar to SCR-06; Translation to SCR-10.",
         components=[
             (1, "Side-menu toggle (right-hand)", "ImageButton", "main_nav_toggle", "28 dp / 32 dp",
              "Expands the side menu over the content (icon changes to 'menu open'); pressed again collapses it."),
             (2, "Side menu", "LinearLayout of item_nav", "nav_rail, nav_home … nav_settings",
              "40 dp collapsed / 104 dp expanded (52 / 140 on tablets); items 32 dp (40 dp) tall",
              "Home (selected), Image, PDF, History, Settings. Collapsed: icons with tooltips. Expanded: icons and labels, content dimmed."),
             (3, "Banner", "LinearLayout", "-", "110 dp / 150 dp", "Static title and subtitle."),
             (4, "Action tiles (4)", "item_action_tile", "tile_image, tile_pdf, tile_sequence, tile_history",
              "Wrap content, min 70 dp (100 dp); icon 22 dp (32 dp); title 14 sp (16 sp)",
              "Image OCR -> SCR-03; PDF OCR -> SCR-07; Image Sequence -> SCR-04; History -> SCR-08."),
             (5, "Language bar", "view_language_bar", "language_bar",
              "Swap button 24 dp (28 dp); names 14 sp", "Tap a side -> SCR-06 for that side; swap exchanges source and target."),
             (6, "Translation button", "MaterialButton (Outlined)", "main_manual_translate",
              "height 30 dp (36 dp), 12 sp (14 sp)", "Opens SCR-10."),
             (7, "Model status", "ImageButton", "main_models_status", "28 dp / 32 dp", "Opens SCR-09."),
             (8, "Scrim (expanded only)", "View", "nav_scrim", "Fills content area",
              "Dims content while expanded; tap collapses the menu."),
             (9, "Model warning", "TextView", "main_model_warning", "12 sp",
              "Shown only when models are missing; tap opens SCR-09."),
         ]),
    dict(id="SCR-03", name="Camera OCR", activity="CameraActivity", layout="activity_camera.xml",
         image="03_camera.png", reqs=["FR-01", "FR-02", "FR-22"],
         purpose="Live preview and capture; gallery shortcut.",
         entry="Image OCR tile.",
         exit="Result (SCR-05) after processing; Back to SCR-02.",
         components=[
             (1, "Back", "ImageButton", "camera_back", "28 dp / 32 dp", "Closes the screen."),
             (2, "Flash", "ImageButton", "camera_flash", "28 dp / 32 dp", "Toggles flash mode (dimmed when off)."),
             (3, "Gallery (top)", "ImageButton", "camera_gallery_top", "28 dp / 32 dp", "Opens the system image picker."),
             (4, "Preview and frame", "PreviewView", "camera_preview", "Full screen", "Back camera preview; framing guide."),
             (5, "Gallery", "circle button", "camera_gallery", "28 dp / 32 dp", "Opens the system image picker."),
             (6, "Shutter", "ImageButton", "camera_shutter", "44 dp / 54 dp", "Captures and processes; ignored while busy."),
             (7, "Auto", "circle button", "camera_auto", "28 dp / 32 dp", "Shows 'Auto' (informational)."),
         ]),
    dict(id="SCR-04", name="Image Import", activity="ImageImportActivity", layout="activity_image_import.xml",
         image="04_image_import.png", reqs=["FR-02", "FR-03", "FR-22"],
         purpose="Select one or several images for processing.",
         entry="Image Sequence tile; Image item in the side menu. The picker opens immediately.",
         exit="Result (SCR-05) with the last processed image.",
         components=[
             (1, "Toolbar", "view_toolbar", "toolbar_back", "56 dp bar, 28 dp buttons", "Back closes."),
             (2, "Thumbnail grid", "RecyclerView (3 columns)", "import_grid", "Square cells",
              "Tap toggles selection (red frame and check)."),
             (3, "Select images", "MaterialButton (Tonal)", "import_add", "30 dp / 36 dp", "Opens the multi-image picker."),
             (4, "Selection count", "TextView", "import_count", "12 sp", "'n images selected'."),
             (5, "Next", "MaterialButton (Primary)", "import_next", "30 dp / 36 dp",
              "Processes the selection; with none selected shows 'Select at least one image'."),
         ]),
    dict(id="SCR-05", name="Translation Result", activity="ResultActivity", layout="activity_result.xml",
         image="05_result.png", reqs=["FR-11", "FR-12", "FR-13", "FR-14", "FR-22", "FR-24"],
         purpose="Show the re-rendered page and the texts; edit, speak, save.",
         entry="After processing from SCR-03 or SCR-04.",
         exit="Back to the previous screen.",
         components=[
             (1, "Toolbar", "view_toolbar", "toolbar_back", "56 dp bar", "Back closes and releases page bitmaps."),
             (2, "Page image", "ImageView", "result_image", "Upper area",
              "Rendered page (translucent highlight + halo text) or original."),
             (3, "Direction badge", "TextView", "result_mode_badge", "11 sp", "Effective source -> target, e.g. JA -> EN."),
             (4, "Source text", "TextView", "result_source_text", "Scrollable", "Recognised text."),
             (5, "Translation", "EditText", "result_translated_text", "Scrollable", "Editable before saving and speaking."),
             (6, "Speak", "MaterialButton (Tonal)", "result_speak", "30 dp / 36 dp", "Reads the translation; disabled without a voice."),
             (7, "Show original / translated", "MaterialButton (Tonal)", "result_toggle", "30 dp / 36 dp", "Toggles the image."),
             (8, "Save", "MaterialButton (Primary)", "result_save", "30 dp / 36 dp", "Saves to history; toast 'Saved to history'."),
         ]),
    dict(id="SCR-06", name="Language Settings", activity="LanguageActivity", layout="activity_language.xml",
         image="06_language.png", reqs=["FR-10", "FR-17", "FR-21"],
         purpose="Choose the source or target language.",
         entry="Language bar (SCR-02, SCR-07, SCR-10); default language rows in SCR-09.",
         exit="Back, or selecting a language (saves and closes).",
         components=[
             (1, "Source / Target tabs", "TabLayout", "language_tabs", "-", "Switch the side being edited."),
             (2, "Search", "EditText", "language_search", "Full width", "Filters by English name, native name or code."),
             (3, "Language rows", "RecyclerView of item_language", "language_list", "-",
              "Flag, name (with native name), note. English, Japanese, Chinese only - Korean is not listed."),
             (4, "Availability note", "TextView", "-", "11 sp", "'Model not installed' or 'via English - slower, lower quality'."),
             (5, "Selected mark", "ImageView", "-", "-", "Marks the current choice."),
         ]),
    dict(id="SCR-07", name="PDF OCR", activity="PdfActivity", layout="activity_pdf.xml",
         image="07_pdf.png", reqs=["FR-04", "FR-20", "FR-17", "FR-22"],
         purpose="Translate a PDF document.",
         entry="PDF OCR tile; PDF item in the side menu.",
         exit="Back (cancels a running job).",
         components=[
             (1, "File card", "LinearLayout", "pdf_file_card", "Full width", "Tap opens the document picker (PDF)."),
             (2, "Clear", "ImageButton", "pdf_file_clear", "24 dp / 28 dp", "Clears the selected file."),
             (3, "Page Range", "item_option_row", "pdf_row_range", "min 32 dp", "All Pages, 1-5, 1-10, 1-20."),
             (4, "Output Format", "item_option_row", "pdf_row_format", "min 32 dp", "PDF, DOCX, TXT (persisted)."),
             (5, "Language bar", "view_language_bar", "pdf_language_bar", "-", "As on SCR-02."),
             (6, "Start OCR", "MaterialButton (Primary)", "pdf_start", "30 dp / 36 dp",
              "Starts the job; without a file shows 'Choose a PDF' and opens the picker."),
             (7, "Result", "TextView", "pdf_result", "Text", "Output path and combined text."),
         ]),
    dict(id="SCR-08", name="History", activity="HistoryActivity", layout="activity_history.xml",
         image="08_history.png", reqs=["FR-15"],
         purpose="Review and manage saved translations.",
         entry="History tile; History item in the side menu.",
         exit="Back.",
         components=[
             (1, "Clear history", "ImageButton (toolbar action)", "toolbar_action", "28 dp / 32 dp",
              "Confirms, then deletes all entries."),
             (2, "Entry list", "RecyclerView of item_history", "history_list", "-",
              "Kind icon, first line (max 60 chars), direction, timestamp. Tap: detail dialog. Long-press: delete."),
             (3, "Empty state", "LinearLayout", "history_empty", "-", "'No translations yet' with hint."),
         ]),
    dict(id="SCR-09", name="Settings", activity="SettingsActivity", layout="activity_settings.xml",
         image="09_settings.png", reqs=["FR-09", "FR-18", "FR-19", "FR-21"],
         purpose="Preferences and model report.",
         entry="Settings item in the side menu; model status button on SCR-02; model warning.",
         exit="Back.",
         components=[
             (1, "OCR Language", "item_option_row", "settings_ocr_language", "min 32 dp", "Toggles Auto / configured source."),
             (2, "Image Quality", "item_option_row", "settings_image_quality", "min 32 dp", "LOW 640 / MEDIUM 960 / HIGH 1280 px."),
             (3, "Auto Translation", "item_option_row (switch)", "settings_auto_translate", "min 32 dp", "Translate after recognition."),
             (4, "Default Source Language", "item_option_row", "settings_default_source", "min 32 dp", "Opens SCR-06 (source)."),
             (5, "Default Target Language", "item_option_row", "settings_default_target", "min 32 dp", "Opens SCR-06 (target)."),
             (6, "Installed Models", "item_option_row", "settings_models", "min 32 dp",
              "'OCR languages / MT pairs' (3 / 4 with Korean hidden); tap shows report and pivoted pairs."),
             (7, "About", "item_option_row", "settings_about", "min 32 dp", "Version and model licences."),
             (8, "Help & Feedback", "item_option_row", "settings_help", "min 32 dp", "Usage tips."),
         ]),
    dict(id="SCR-10", name="Translation (manual)", activity="TranslateActivity", layout="activity_translate.xml",
         image="10_translate.png", reqs=["FR-10", "FR-16", "FR-17", "FR-22"],
         purpose="Translate typed text without OCR.",
         entry="Translation button on SCR-02.",
         exit="Back.",
         components=[
             (1, "Language bar", "view_language_bar", "translate_language_bar", "-", "As on SCR-02."),
             (2, "Input", "EditText", "translate_input", "Multi-line", "Up to 500 characters."),
             (3, "Copy input / counter", "ImageButton, TextView", "translate_copy_source, translate_input_counter",
              "24 dp / 28 dp", "Copies input; shows n/500."),
             (4, "Translate", "MaterialButton (Primary)", "translate_action", "30 dp / 36 dp",
              "Translates and saves to history; same language copies the input."),
             (5, "Output language", "TextView", "translate_output_lang", "12 sp", "Target display name."),
             (6, "Copy output", "ImageButton", "translate_copy_output", "24 dp / 28 dp", "Copies the translation."),
             (7, "Pivot note", "TextView", "translate_note", "11 sp", "Shown when routed through English."),
         ]),
]

# --------------------------------------------------------------------------
# Test cases: (id, title, reqs, level, priority, preconditions, steps, expected)
# level: Unit (JVM), Integration, System (device), Acceptance
# --------------------------------------------------------------------------
PRE_MODELS = "Models installed (tools/fetch_models.sh); app freshly installed; languages EN -> ZH."
TC = [
    ("TC-01-1", "Capture and translate a printed page", ["FR-01", "FR-11", "FR-12"], "System", "High",
     PRE_MODELS + " Camera permission granted.",
     ["Tap Image OCR on Home.", "Frame a printed English page and tap the shutter.",
      "Wait for the progress overlay to close."],
     "Result screen opens; badge shows EN -> ZH; rendered page shows Chinese text over each paragraph with no opaque "
     "background patch; source and translation fields are filled."),
    ("TC-01-2", "Camera permission refused", ["FR-01", "NFR-09"], "System", "High",
     "Camera permission not yet granted.",
     ["Tap Image OCR.", "Choose 'Don't allow' in the permission dialog."],
     "Toast explains that camera access is needed; the camera screen closes; no crash."),
    ("TC-01-3", "Portrait capture is upright", ["FR-01"], "System", "Medium", PRE_MODELS,
     ["Hold the phone in portrait and capture a page."],
     "Rendered image in SCR-05 is upright (rotation from capture metadata applied); text is detected."),
    ("TC-01-4", "Flash toggle", ["FR-01"], "System", "Low", PRE_MODELS,
     ["Open the camera.", "Tap Flash twice."], "Button becomes fully opaque when on and dimmed when off."),
    ("TC-02-1", "Import one image from the camera screen", ["FR-02"], "System", "High", PRE_MODELS,
     ["Open the camera.", "Tap the gallery button.", "Pick one image."], "Image is processed and SCR-05 opens."),
    ("TC-02-2", "Cancel the picker", ["FR-02"], "System", "Low", PRE_MODELS,
     ["Open the gallery picker from the camera.", "Press Back without choosing."],
     "Returns to the camera; nothing is processed."),
    ("TC-02-3", "Unreadable image", ["FR-02", "NFR-09"], "System", "Medium", PRE_MODELS,
     ["Pick a corrupt or non-image file via the picker."], "Toast with an error message; no crash."),
    ("TC-03-1", "Batch of three images", ["FR-03", "FR-14"], "System", "High", PRE_MODELS,
     ["Tap Image Sequence.", "Select three images.", "Tap Next."],
     "Overlay shows 'Page 1 of 3' … 'Page 3 of 3'; SCR-05 shows the third image; History contains three new entries."),
    ("TC-03-2", "Next with nothing selected", ["FR-03"], "System", "Medium", PRE_MODELS,
     ["Open Image Import.", "Deselect every thumbnail.", "Tap Next."],
     "Toast 'Select at least one image'; nothing is processed."),
    ("TC-03-3", "Toggle selection", ["FR-03"], "System", "Low", PRE_MODELS,
     ["Select two images.", "Tap one thumbnail again."],
     "Its frame and check disappear; the count reads '1 image selected'."),
    ("TC-04-1", "Choose a PDF", ["FR-04"], "System", "High", PRE_MODELS + " A 12-page PDF on the device.",
     ["Tap PDF OCR.", "Tap the file card and pick the PDF."],
     "File name shown; meta line shows size and '12 pages'; clear button visible."),
    ("TC-04-2", "Page range and format", ["FR-04"], "System", "Medium", "TC-04-1 done.",
     ["Tap Page Range, choose 1-5.", "Tap Output Format, choose DOCX.", "Leave and reopen the PDF screen."],
     "Range row shows 1-5; format shows DOCX; after reopening, the format is still DOCX (persisted), range resets to All Pages."),
    ("TC-04-3", "Clear selection", ["FR-04"], "System", "Low", "TC-04-1 done.",
     ["Tap the clear (x) button."], "Card shows 'Choose a PDF'; meta and clear button hidden; range resets."),
    ("TC-05-1", "DB post-processing unit tests", ["FR-05"], "Unit", "High", "JDK 17; ./gradlew test.",
     ["Run DbPostProcessorTest (9 tests)."],
     "All pass: single block, two blocks, unclip grows the box, noise and tiny components ignored, scaling, empty map, thresholds."),
    ("TC-05-2", "Rotated text is detected", ["FR-05", "FR-11"], "System", "Medium", PRE_MODELS,
     ["Photograph a page rotated about 15 degrees."],
     "Lines are detected; rendered translation is rotated to match the paragraph angle."),
    ("TC-06-1", "Upside-down page", ["FR-06"], "System", "Medium", PRE_MODELS + " Classifier model present.",
     ["Process an image of a page rotated 180 degrees."], "Recognised text reads correctly (crops flipped)."),
    ("TC-07-1", "CTC decoder unit tests", ["FR-07"], "Unit", "High", "./gradlew test.",
     ["Run CtcDecoderTest (8 tests)."],
     "All pass: repeats collapse, blank separates doubled letters, all-blank yields empty text, dictionary size checks."),
    ("TC-07-2", "Low-confidence noise dropped", ["FR-07"], "System", "Low", PRE_MODELS,
     ["Process a photo with background texture and little text."], "No garbage lines from texture appear in source text."),
    ("TC-08-1", "Two-column layout", ["FR-08"], "System", "Medium", PRE_MODELS,
     ["Process a two-column page."],
     "Source text follows each column in order; columns are separate paragraphs; headings are separate paragraphs."),
    ("TC-09-1", "Auto-detect Japanese from a CJK first pass", ["FR-09"], "System", "High",
     PRE_MODELS + " OCR Language = Auto; source = Chinese; target = English.",
     ["Process a Japanese page containing Kana."],
     "If the first (Chinese-model) pass emits Kana above 8 % of scored characters, the page is re-recognised with "
     "the Japanese model and the badge shows JA -> EN; otherwise it stays ZH -> EN. Record which occurs: detection can "
     "only see scripts the first-pass model can emit (known limitation KI-02)."),
    ("TC-09-4", "Auto-detection limitation with an English first pass", ["FR-09"], "System", "Medium",
     PRE_MODELS + " OCR Language = Auto; source = English.",
     ["Process a Japanese page."],
     "Badge stays EN -> ZH: the English model cannot emit CJK characters, so no re-detection is triggered. "
     "Documents known limitation KI-02; the user must choose the source language."),
    ("TC-09-2", "Script detector unit tests", ["FR-09"], "Unit", "High", "./gradlew test.",
     ["Run ScriptDetectorTest (9 tests)."],
     "All pass, including the documented failure mode (pure-Kanji Japanese reported as Chinese)."),
    ("TC-09-3", "Hangul page with Korean hidden", ["FR-09", "FR-21"], "System", "High",
     PRE_MODELS + " OCR Language = Auto; source = English.",
     ["Process a Korean (Hangul) page."],
     "Badge never shows KO; the configured source (EN) is kept; no Korean appears anywhere in the UI."),
    ("TC-10-1", "Direct direction", ["FR-10"], "System", "High", PRE_MODELS + " EN -> JA.",
     ["Translate an English page."], "Japanese translation; no pivot note on the language screen."),
    ("TC-10-2", "Pivoted direction", ["FR-10"], "System", "High", PRE_MODELS + " JA -> ZH.",
     ["Open Language Settings, Target tab.", "Inspect the Chinese row.", "Translate a Japanese page."],
     "Chinese row shows 'via English - slower, lower quality'; translation succeeds."),
    ("TC-10-3", "SentencePiece unit tests", ["FR-10"], "Unit", "High", "./gradlew test.",
     ["Run SpmEncoderTest (8 tests)."], "All pass: Viterbi segmentation, unknown fallback, normalisation, decoding."),
    ("TC-11-1", "Translucent highlight, no opaque background", ["FR-11"], "System", "High", PRE_MODELS,
     ["Photograph text printed over a photograph or textured paper.", "Inspect SCR-05."],
     "Page texture remains visible through the highlighted area; original text appears as a faint ghost; translation "
     "is legible thanks to its halo; no flat rectangular patch."),
    ("TC-11-2", "Light text on dark background", ["FR-11"], "System", "Medium", PRE_MODELS,
     ["Photograph a dark sign with white lettering."], "Translation drawn in light ink with a dark halo and dark highlight."),
    ("TC-11-3", "Long translation fits or is flagged", ["FR-11"], "System", "Medium", PRE_MODELS,
     ["Translate short Chinese labels into English (translation longer than source)."],
     "Text shrinks to fit, not below 45 % of the source size. In a developer build with LayoutRenderer.Options.debugBoxes = true, fitting blocks are outlined blue and overflowing blocks red."),
    ("TC-11-4", "Untranslated paragraph untouched", ["FR-11", "FR-24"], "System", "Medium",
     PRE_MODELS + " Auto Translation off.", ["Process a page."],
     "Rendered page equals the original (no highlights) because no paragraph carries a translation."),
    ("TC-12-1", "Toggle original", ["FR-12"], "System", "Medium", "On SCR-05.",
     ["Tap 'Show original'.", "Tap 'Show translated'."], "Image switches; button label switches accordingly."),
    ("TC-12-2", "Rotation keeps the result", ["FR-12"], "System", "Low", "On SCR-05.",
     ["Rotate the device."], "Same page and texts are shown after recreation."),
    ("TC-13-1", "Speak translation", ["FR-13"], "System", "Low", "On SCR-05; TTS voice for target installed.",
     ["Edit the translation.", "Tap Speak."], "The edited text is spoken."),
    ("TC-13-2", "No voice installed", ["FR-13"], "System", "Low", "Target language voice not installed.",
     ["Open SCR-05."], "Speak button is disabled."),
    ("TC-14-1", "Save to history", ["FR-14"], "System", "High", "On SCR-05.",
     ["Edit the translation.", "Tap Save.", "Open History."],
     "Toast 'Saved to history'; newest entry shows the first source line and the direction; detail shows the edited translation."),
    ("TC-15-1", "Delete one entry", ["FR-15"], "System", "Medium", "History has entries.",
     ["Long-press an entry.", "Tap Delete."], "Entry disappears."),
    ("TC-15-2", "Clear history", ["FR-15"], "System", "Medium", "History has entries.",
     ["Tap the delete icon in the toolbar.", "Tap Delete in the confirmation."],
     "Toast 'History cleared'; empty state shown."),
    ("TC-15-3", "Cancel clear", ["FR-15"], "System", "Low", "History has entries.",
     ["Tap the delete icon.", "Tap Cancel."], "Entries remain."),
    ("TC-16-1", "Manual translation", ["FR-16"], "System", "High", PRE_MODELS + " EN -> JA.",
     ["Tap Translation on Home.", "Type 'Where is the station?'", "Tap Translate."],
     "Japanese output shown; counter shows 21/500; entry added to History (kind MANUAL)."),
    ("TC-16-2", "Copy buttons", ["FR-16"], "System", "Low", "TC-16-1 done.",
     ["Tap copy on the output."], "Toast 'Copied to clipboard'; clipboard holds the translation."),
    ("TC-16-3", "Same source and target", ["FR-16"], "System", "Low", "Source = target = EN.",
     ["Type text and tap Translate."], "Output equals the input; no model is loaded."),
    ("TC-17-1", "Search languages", ["FR-17"], "System", "Medium", "On SCR-06.",
     ["Type 'jap'.", "Clear and type '中'.", "Clear and type 'zh'."],
     "Japanese only; Chinese only; Chinese only."),
    ("TC-17-2", "Swap languages", ["FR-17"], "System", "Medium", "EN -> ZH.",
     ["Tap the swap button on Home."], "Bar shows ZH -> EN; the choice persists after restart."),
    ("TC-18-1", "Image quality applies without restart", ["FR-18"], "System", "Medium", PRE_MODELS,
     ["Set Image Quality to LOW.", "Process a page with small print.", "Set HIGH and process again."],
     "Row shows the chosen level; small print is recognised better at HIGH (detection limit re-applied on each scan)."),
    ("TC-18-2", "Auto Translation off", ["FR-18", "FR-24"], "System", "Medium", PRE_MODELS,
     ["Turn Auto Translation off.", "Process a page."], "Recognised text shown; translation field empty."),
    ("TC-18-3", "Installed models report", ["FR-18", "FR-19", "FR-21"], "System", "High", PRE_MODELS,
     ["Open Settings.", "Tap Installed Models."],
     "Row shows 3 / 4; report lists OCR 'en ja zh' and pivoted pairs ja-zh and zh-ja only; no 'ko'."),
    ("TC-18-4", "Help text", ["FR-18", "FR-21"], "System", "Low", "-",
     ["Open Help & Feedback."], "Tips mention Japanese and Chinese pivoting; Korean is not mentioned."),
    ("TC-18-6", "About and licences", ["FR-18", "NFR-11"], "System", "Medium", "-",
     ["Open About."], "Version, PaddleOCR (Apache 2.0), OPUS-MT (CC-BY 4.0) and ONNX Runtime are shown."),
    ("TC-19-1", "Models missing", ["FR-19", "NFR-09"], "System", "High", "App installed WITHOUT models.",
     ["Launch the app."],
     "Splash status 'Models are not installed'; Home shows the warning with the fetch hint; tapping it opens Settings; no crash."),
    ("TC-19-2", "Partial models", ["FR-19"], "System", "Medium", "One recognition model removed before build.",
     ["Open Installed Models."], "Report names the missing file path."),
    ("TC-20-1", "PDF to PDF", ["FR-20"], "System", "High", "TC-04-1 done; format PDF.",
     ["Tap Start OCR."],
     "Overlay counts 'Page i of 12'; result shows the path under files/exports; output PDF pages keep their physical size; History has a PDF entry."),
    ("TC-20-2", "PDF to DOCX and TXT", ["FR-20"], "System", "Medium", "TC-04-1 done.",
     ["Run with DOCX, then with TXT."], "Files open in a word processor / text editor and contain the page texts."),
    ("TC-20-3", "Cancel a PDF job", ["FR-20"], "System", "Medium", "Job running on a long PDF.",
     ["Press Back during processing."], "Overlay closes; job stops after the current page; no crash."),
    ("TC-20-4", "DOCX writer unit tests", ["FR-20"], "Unit", "High", "./gradlew test.",
     ["Run DocxWriterTest (8 tests)."], "All pass: parts present, escaping, control characters, CJK, empty document."),
    ("TC-20-5", "Start without a file", ["FR-20"], "System", "Low", "No PDF chosen.",
     ["Tap Start OCR."], "Toast 'Choose a PDF'; document picker opens."),
    ("TC-21-1", "Korean absent from pickers", ["FR-21"], "System", "High", "-",
     ["Open Language Settings on both tabs.", "Search 'ko', 'kor', '한'."],
     "Only English, Japanese, Chinese listed; searches return nothing."),
    ("TC-21-2", "Stored Korean preference ignored", ["FR-21"], "Integration", "High",
     "Preference source_lang set to 'ko' (adb or older build).",
     ["Launch the app and open Home."], "Language bar shows English (default), not Korean."),
    ("TC-21-3", "Language gating unit tests", ["FR-21"], "Unit", "High", "./gradlew test.",
     ["Run LangTest (8 tests)."],
     "All pass, including koreanIsImplementedButNotUserFacing and userFacingLanguagesSurviveTheFilter."),
    ("TC-21-4", "Re-enable Korean", ["FR-21"], "Integration", "Low", "Developer build.",
     ["Uncomment KO in Lang.USER_FACING; rebuild.", "Open Language Settings."],
     "Korean (한국어) listed; Korean pages translate. (Update LangTest before merging.)"),
    ("TC-22-1", "Compact home tiles", ["FR-22"], "System", "High", "Phone, portrait.",
     ["Open Home."],
     "The four tiles wrap to their content, each about 70 dp tall with a 22 dp icon and 14 sp title; they do not stretch to fill the screen."),
    ("TC-22-2", "Tablet sizes", ["FR-22", "NFR-08"], "System", "Medium", "Tablet (sw >= 600 dp).",
     ["Open Home, Result and PDF screens."],
     "Tiles about 100 dp, primary buttons 36 dp, button text 14 sp; nothing clipped."),
    ("TC-22-3", "Landscape / short screens scroll", ["FR-22"], "System", "Medium", "Phone, landscape.",
     ["Open Home.", "Scroll."], "Content scrolls if it does not fit; nothing overlaps or clips."),
    ("TC-22-4", "Button sizes match the tokens", ["FR-22", "NFR-07"], "System", "Medium", "-",
     ["Measure buttons with Layout Inspector on every screen.", "Run Accessibility Scanner."],
     "Buttons are 30 dp tall, icon buttons 28 dp, small icon buttons 24 dp (phone). The scanner's "
     "touch-target warnings are expected (KI-07) and recorded, not failed."),
    ("TC-23-1", "Expand with the right-hand button", ["FR-23"], "System", "High", "Home, menu collapsed.",
     ["Tap the right-hand title-bar button."],
     "Menu animates to full width over the content with labels; content dims; button icon changes to 'menu open' and its description to 'Collapse menu'."),
    ("TC-23-2", "Collapse by button, scrim and Back", ["FR-23"], "System", "High", "Menu expanded.",
     ["Tap the button.", "Expand; tap the dimmed area.", "Expand; press Back."],
     "Each action collapses the menu; Back does not leave the app while the menu is expanded; a second Back exits Home as usual."),
    ("TC-23-3", "Collapsed tooltips and TalkBack", ["FR-23", "NFR-07"], "System", "Medium", "Menu collapsed; TalkBack on.",
     ["Long-press a menu icon.", "Focus each icon with TalkBack."], "Tooltip shows the label; TalkBack reads the label."),
    ("TC-23-4", "Menu items navigate", ["FR-23"], "System", "High", "-",
     ["Tap Image, PDF, History, Settings in turn (collapsed and expanded)."], "Opens SCR-04, SCR-07, SCR-08, SCR-09."),
    ("TC-23-5", "Starts collapsed", ["FR-23"], "System", "Low", "Menu expanded.",
     ["Leave the app with Back from the collapsed menu, relaunch."], "Menu is collapsed."),
    ("TC-NFR-01", "No network access", ["NFR-01"], "System", "High", PRE_MODELS,
     ["Enable airplane mode.", "Run TC-01-1, TC-16-1, TC-20-1.",
      "Inspect the merged manifest for INTERNET."], "Everything works offline; no INTERNET permission."),
    ("TC-NFR-03", "UI stays responsive", ["NFR-03"], "System", "Medium", PRE_MODELS,
     ["Start a 20-page PDF job.", "Rotate and background/foreground the app."], "No ANR; overlay progress keeps updating."),
    ("TC-NFR-04", "Latency measurement", ["NFR-04"], "System", "Medium", PRE_MODELS + " Mid-tier device.",
     ["Process 20 photographed pages at HIGH; record 'recognised n line(s) in t ms' from logcat and wall-clock time."],
     "Median end-to-end time recorded; compared with the 10 s target. [Measurement pending]"),
    ("TC-NFR-05", "Memory during PDF", ["NFR-05"], "System", "Medium", PRE_MODELS,
     ["Profile heap while translating a 20-page PDF."], "No OutOfMemoryError; heap returns to baseline between pages. [Measurement pending]"),
    ("TC-NFR-07", "Accessibility walkthrough", ["NFR-07"], "Acceptance", "Medium", "TalkBack on.",
     ["Complete TC-01-1 and TC-16-1 using TalkBack only."], "Every control is announced meaningfully."),
]

# JVM unit tests actually present in app/src/test (class -> methods).
UNIT_TESTS = {
    "LangTest": ["parsesCanonicalCodes", "acceptsJpAsAliasForJa", "stripsRegionSuffixes",
                 "unknownCodeIsNull", "fallbackIsUsedForUnknownCodes",
                 "pairKeyMatchesModelDirectoryNaming", "koreanIsImplementedButNotUserFacing",
                 "userFacingLanguagesSurviveTheFilter"],
    "ScriptDetectorTest": ["hangulIsKorean", "kanaIsJapanese", "hanWithoutKanaIsChinese",
                           "latinIsEnglish", "mixedHanAndKanaIsJapanese",
                           "smallHangulShareStillWins", "digitsAndPunctuationFallBack",
                           "nullAndEmptyFallBack", "pureKanjiJapaneseIsReportedAsChinese"],
    "SpmEncoderTest": ["viterbiPrefersHigherScoringSegmentation", "viterbiSplitsWhenThatScoresBetter",
                       "unknownCharacterFallsBackToSingleChar", "normalizePrefixesMarkerAndReplacesSpaces",
                       "normalizeCollapsesWhitespace", "normalizeReturnsEmptyForBlankInput",
                       "normalizeAppliesNfkc", "decodePiecesRestoresSpaces"],
    "CtcDecoderTest": ["collapsesRepeatsAndDropsBlanks", "blankSeparatesDoubledCharacters",
                       "withoutBlankRepeatsCollapseToOne", "allBlankYieldsEmptyTextAndZeroConfidence",
                       "trailingClassIsSpace", "dictionaryWithoutSpaceClassIsAccepted",
                       "mismatchedDictionaryIsRejected", "trailingEmptyLineIsIgnored"],
    "DbPostProcessorTest": ["findsASingleBlock", "separatesTwoDistinctBlocks",
                            "unclipExpandsBeyondTheRawBlob", "ignoresLowProbabilityNoise",
                            "ignoresTinyComponents", "scalesResultsBackToSourceResolution",
                            "emptyMapYieldsNoBoxes", "thresholdIsHonoured",
                            "boxScoreThresholdRejectsLowConfidenceBlobs"],
    "DocxWriterTest": ["writesEveryRequiredPart", "writesOneParagraphPerEntry",
                       "escapesXmlMetacharacters", "stripsControlCharacters",
                       "newlinesBecomeLineBreaks", "preservesSignificantWhitespace",
                       "handlesCjkText", "emptyDocumentIsStillValid"],
}

# Known issues / limitations found while specifying (referenced by SDD and TCS).
KNOWN_ISSUES = [
    ("KI-01", "Rendering", "A translucent highlight attenuates but does not remove the original text; a high-contrast "
     "original behind a much shorter translation remains faintly visible outside the halo.", "By design; inpainting is future work."),
    ("KI-02", "Auto-detection", "Script detection runs on the first pass's output, so it can only notice scripts the "
     "first-pass model can emit. With English as the source, CJK pages are never re-detected.", "Choose the source language; "
     "future: run detection on a multi-script first pass."),
    ("KI-03", "Language gating", "History rows saved before Korean was hidden still display 'KO -> ..' in their direction label.",
     "Cosmetic; affects only pre-existing data."),
    ("KI-04", "Batch import", "Only the last image of a batch opens in the result screen; the others are in History.", "By design."),
    ("KI-05", "PDF range", "Page ranges are limited to All, 1-5, 1-10, 1-20.", "Enhancement candidate."),
    ("KI-07", "Accessibility", "The compact sizes put several touch targets (24-32 dp icon buttons, 30 dp buttons, "
     "32 dp side-menu items) below Android's 48 dp guideline.", "Deliberate, per the compact-UI request; raise the tokens "
     "in dimens.xml if accessibility takes priority."),
    ("KI-06", "Build verification", "The UI changes (compact controls, collapsible menu) and the rendering change have not yet "
     "been compiled or run on a device in this revision.", "Run ./gradlew test assembleDebug and the System tests."),
]

GLOSSARY = [
    ("OCR", "Optical character recognition: finding and reading text in an image."),
    ("MT / NMT", "(Neural) machine translation."),
    ("DB", "Differentiable Binarization, the segmentation-based text detector used by PP-OCR."),
    ("CTC", "Connectionist temporal classification, the decoding scheme of the recogniser."),
    ("PP-OCR", "PaddleOCR's lightweight detection, classification and recognition models."),
    ("OPUS-MT", "Helsinki-NLP's openly licensed Marian translation models."),
    ("ONNX Runtime", "Cross-platform inference engine that executes the converted models."),
    ("Pivot", "Translating A -> English -> B when no direct A -> B model exists."),
    ("Highlight", "Translucent, feathered paper-colour fill drawn under a translation (replaces the old opaque erase)."),
    ("Halo", "Paper-coloured outline drawn behind each translated glyph for legibility."),
    ("Side menu / rail", "Vertical navigation on the left of Home; collapsed = icons only, expanded = icons and labels."),
    ("User-facing language", "A language listed in Lang.USER_FACING and therefore visible in the UI (EN, JA, ZH)."),
    ("dp / sp", "Density-independent pixels / scale-independent pixels (Android units)."),
    ("sw600dp", "Resource qualifier for screens whose smallest width is at least 600 dp (tablets)."),
]


def req_title(rid: str) -> str:
    for r in FR:
        if r[0] == rid:
            return r[1]
    for r in NFR:
        if r[0] == rid:
            return r[1]
    return ""


def tests_for(rid: str) -> list[str]:
    return [t[0] for t in TC if rid in t[2]]


def screens_for(rid: str) -> list[str]:
    return [s["id"] for s in SCREENS if rid in s["reqs"]]
