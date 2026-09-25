# falcon-ocr-trans — Technical Documentation

This document is for engineers who build, maintain or extend the app. It covers
architecture, the algorithm in each pipeline stage, the rendering model, language
gating, the model tree, performance, and extension points. For a quick overview,
see the [README](../README.md). For model files, see
[`app/src/main/assets/model/README.md`](../app/src/main/assets/model/README.md).

---

## 1. Scope and constraints

| Property | Value |
|---|---|
| Platform | Android, `minSdk 24`, `compileSdk 35` |
| Language | Java only, no NDK layer |
| Build | Gradle 8.13 |
| Network | None. The manifest requests no `INTERNET` permission |
| Inference | ONNX Runtime (Java API) |
| OCR | PaddleOCR PP-OCRv4 detection, PP-OCRv4 / PP-OCRv3 recognition, v2.0 angle classifier |
| MT | Helsinki-NLP OPUS-MT (Marian), exported to ONNX, dynamic int8 |
| Implemented languages | English, Korean, Japanese, Chinese |
| Languages shown to users | English, Japanese, Chinese (Korean is hidden; see §7) |

All processing happens on the device. No image or text leaves it.

---

## 2. Architecture

```
          ┌────────────────────────── ui ───────────────────────────┐
          │ Camera · ImageImport · Pdf · Result · Translate · ...   │
          └───────────────┬─────────────────────────────────────────┘
                          │ Engines.get(ctx).submit(...)
                          ▼
   engine ─ Engines (singleton, one worker thread "falcon-engine")
            ├─ ModelValidator  → Report {ocrLanguages, mtPairs, missing}
            └─ TranslationPipeline.process(bitmap, source, target, options)
                 │
                 ├─ ocr ─ PaddleOcrEngine
                 │         detect → DbPostProcessor → cropQuad → cls → rec → CtcDecoder
                 │         → ImageOps.sampleColors → LineGrouper
                 ├─ engine ─ ScriptDetector (optional re-recognition)
                 ├─ mt ─ PivotTranslator → MarianTranslator (SpmEncoder, MtVocab, MtConfig)
                 └─ render ─ LayoutRenderer → TextFitter
```

### 2.1 Package responsibilities

| Package | Responsibility | Key types |
|---|---|---|
| `core` | Value types shared by all stages | `Lang`, `Quad`, `TextLine`, `Paragraph`, `OcrResult` |
| `ocr` | Detection, cropping, orientation, recognition, grouping | `PaddleOcrEngine`, `DbPostProcessor`, `CtcDecoder`, `CharDict`, `ImageOps`, `LineGrouper` |
| `mt` | Tokenisation and translation | `SpmEncoder`, `MtVocab`, `MtConfig`, `MarianTranslator`, `PivotTranslator` |
| `render` | Repainting translated text over the page | `LayoutRenderer`, `TextFitter` |
| `pdf` | Page rasterisation and PDF/DOCX/TXT output | `PdfPageSource`, `PdfJob`, `DocxWriter` |
| `engine` | Engine lifetime, threading, validation, orchestration | `Engines`, `TranslationPipeline`, `ModelValidator`, `ModelPaths`, `ScriptDetector` |
| `data` | Preferences and SQLite history | `Prefs`, `HistoryStore`, `HistoryItem` |
| `ui` | Activities, adapters, widgets | `*Activity`, `LanguageBar`, `OptionRow`, `Flags` |

### 2.2 Threading model

- `Engines` owns one `PaddleOcrEngine` and one `PivotTranslator`, for the whole
  process. Building them costs seconds and tens of MB of native session state.
- Neither engine is thread-safe. All inference runs on one single-thread
  executor (`falcon-engine`) whose priority is `NORM_PRIORITY - 1`, so
  inference never competes with the UI thread.
- Results are posted back to the main thread through a `Handler`.
- Each ONNX session uses `min(4, cores - 1)` intra-op threads and `ALL_OPT`
  graph optimisation.

### 2.3 Memory policy

- **OCR:** recognition sessions are cached per language after first use.
  Switching the source language mid-session therefore costs one extra load,
  not a reload on every page.
- **MT:** only **one directed pair** is resident at a time (≈35 MB per pair).
  Loading a new pair closes the previous one. A pivoted page loads two pairs in
  sequence, once each, not once per paragraph.
- **PDF:** pages are rasterised, processed and released one at a time. At
  200 dpi, one A4 page (1654 × 2339 px) is ≈15.5 MB as ARGB_8888.

### 2.4 User interface sizing and the side menu

- **Compact, screen-relative controls.** Every control size is a dimension token.
  `res/values/dimens.xml` holds the phone values and
  `res/values-sw600dp/dimens.xml` the tablet values, so all controls grow with
  the screen class. The main tokens are:

  | Token | Phone | Tablet |
  |---|---|---|
  | `button_height` / `button_text` | 30 dp / 12 sp | 36 dp / 14 sp |
  | `icon_button` | 28 dp | 32 dp |
  | `icon_button_small` | 24 dp | 28 dp |
  | `shutter_size` | 44 dp | 54 dp |
  | `row_min_height` | 32 dp | 38 dp |
  | `tile_min_height` | 70 dp | 100 dp |

  The `Widget.Falcon.Button.*` styles read these tokens. They also remove
  Material's default 6 dp insets and 48 dp minimum height; without that, the
  30 dp height would not apply.
- **Accessibility trade-off.** Several touch targets are below Android's
  48 dp guideline. This was requested for a compact look. If accessibility
  takes priority, raise the tokens in `dimens.xml`.
- **Home tiles are compact.** Tiles wrap to their content, at least
  `tile_min_height`. They do not stretch to fill the screen, and the column
  scrolls on short screens.
- **Collapsible side menu** (`MainActivity.bindNavToggle` / `applyNavState`):
  - Collapsed, it is an icon rail (`nav_rail_width`, 40 / 52 dp). The content
    reserves that width with `marginStart`, so the rail never covers a tile.
  - The right-hand title-bar button `main_nav_toggle` animates the rail to
    `nav_rail_expanded_width` (104 / 140 dp) over the content, fades in a
    scrim (`nav_scrim`) and fades the labels in. The animation takes 220 ms.
  - The toggle, a tap on the scrim, or Back collapses it. Back is handled by
    an `OnBackPressedCallback` that is enabled only while the menu is expanded.
  - The menu overlays the content rather than pushing it, so opening it
    never reflows or narrows the home content. Because it covers the content
    while open, it always starts collapsed and its state is not saved.
  - Every menu item carries its label as content description. Collapsed items
    also carry it as a tooltip.

---

## 3. Pipeline, stage by stage

`TranslationPipeline.process` runs the whole job for one bitmap:

```
ocr     = ocrEngine.recognize(bitmap, source)
if autoDetectSource:
    guess = ScriptDetector.detect(ocr.plainText(), source)
    if !guess.isUserFacing(): guess = source          # §7
    if guess != source: ocr = recognize(bitmap, guess) (kept only if non-empty)
if translate and effectiveSource != target:
    translateInPlace(ocr, effectiveSource, target)    # paragraph-level
if render:
    rendered = LayoutRenderer.render(bitmap, ocr, renderOptions)
```

### 3.1 Text detection (`PaddleOcrEngine.detect`, `ImageOps`)

1. **Resize.** Scale the page so its long edge is at most `detectionLimit`
   (the *Image Quality* setting: LOW 640, MEDIUM 960, HIGH 1280; the engine
   clamps any value to 320–2048). Round both sides to a multiple of 32, because
   the detector has five stride-2 stages; an unaligned side shifts every box.
2. **Normalise.** NCHW float tensor with ImageNet mean/std, RGB order.
3. **Infer.** The output is a probability map `P ∈ [0,1]^{H×W}`. Its own shape
   is authoritative for scaling back to page pixels.

### 3.2 DB post-processing (`DbPostProcessor`)

This is a pure-Java replacement for the OpenCV + Clipper post-process that
PaddleOCR normally uses.

| Step | Method | Default |
|---|---|---|
| Binarise | `P ≥ binaryThreshold` | 0.3 |
| Components | Iterative 8-connected flood fill (explicit stack, no recursion) | — |
| Reject specks | component area < `minComponentArea` | 12 px |
| Score | mean of `P` over the **component's own pixels** | ≥ `boxThreshold` 0.6 |
| Outline | keep the leftmost and rightmost pixel of each row | — |
| Hull | Andrew's monotone chain | — |
| Rectangle | Rotating calipers: test every hull edge as one side of the rectangle | — |
| Reject slivers | short side < `minBoxSide` | 3 px |
| Unclip | grow each half-extent by `d = A·r / L` | `r = unclipRatio` 1.6 |
| Output | ordered `Quad`, scaled to page pixels, clamped to the page | — |

Differences from upstream, and the reasons for them:

- **Scoring over the component, not its bounding box.** Upstream averages `P`
  over the axis-aligned box. That penalises diagonal text for the empty
  corners of its box. Averaging over the component's own pixels avoids this.
- **Unclipping the rectangle, not the polygon.** The DB unclip distance is
  `d = A·r / L`. For a `w × h` rectangle this is `d = w·h·r / (2(w + h))`,
  applied to both half-extents. It is closed-form, so no polygon-offset
  library is needed. The renderer needs a baseline angle anyway, not an
  outline.
- **Row-extreme outline.** Keeping only two pixels per row shrinks a 100k-pixel
  paragraph component to a few hundred hull candidates. The hull is unchanged,
  because every hull vertex is a row extreme.

### 3.3 Cropping and orientation

- `ImageOps.cropQuad` maps the four corners onto an upright `w × h` bitmap with
  `Matrix.setPolyToPoly(…, 4)`. This is a perspective map, so mild keystone
  distortion is corrected at the same time. If the corners are collinear, it
  falls back to the axis-aligned bounds. Output size is capped at 4096 px per side.
- The angle classifier (optional; 48×192 input) flips a crop 180° only when
  `p(rotated) > 0.9`. A wrong flip cannot be undone later; a missed flip only
  lowers accuracy.

### 3.4 Recognition and CTC (`recognizeCrops`, `CtcDecoder`, `CharDict`)

- Input height is 48. Crops are **sorted by aspect ratio** and batched six at a
  time, so each batch pads to a similar width. The padded width is rounded up
  to a multiple of 8 and clamped to [16, 1200]. Normalisation is `[-1, 1]`,
  unlike the detector. Mixing the two up produces confident nonsense, not an
  error.
- The dictionary size is checked against the loaded graph's class count, read
  from the output shape. A dynamic class count is rejected with an explicit
  error.
- Greedy CTC decoding: argmax per step, collapse repeats, then drop blanks.
  Line confidence is the mean of the kept maxima. Lines with confidence below
  0.5, and empty lines, are discarded.

### 3.5 Colour estimation (`ImageOps.sampleColors`)

- Subsample the crop to about 4096 pixels.
- Split at the luminance midpoint `(min + max) / 2`, using Rec. 601 weights.
- Average each side. The **minority class is ink** and the majority is
  paper, which also handles light text on a dark background. Ties go to dark ink
  on light paper.
- The result is `TextLine.foregroundColor()` / `backgroundColor()`. The
  renderer uses both.

### 3.6 Reading order and paragraphs (`LineGrouper`)

- **Order:** top to bottom. Two lines count as the same row when their centres
  are within `0.6 × min(height)`; within a row, order is left to right.
- **Paragraph continuation.** Every condition must hold:

| Condition | Threshold |
|---|---|
| Height ratio of neighbours | ≤ 1.7 |
| Baseline angle difference | ≤ 8° |
| Vertical gap (top of next − bottom of previous) | ≤ 1.6 × max height |
| Next line's centre not above previous | — |
| Horizontal overlap / narrower width | ≥ 0.25 |

- `Paragraph.buildSourceText` joins lines with a space, except between two CJK
  characters. In CJK text a space there would be a real character, not a line
  wrap.

### 3.7 Source-language auto-detection (`ScriptDetector`)

This is a script test, not a statistical language identifier.

- Hangul share > 8% → Korean. Kana share > 8% → Japanese. Else Han ≥ Latin → Chinese.
  Else any Latin → English. Otherwise the configured source is kept.
- Pure-Kanji Japanese (e.g. a 出口 sign) is classified as Chinese. This is the
  known, accepted failure mode.
- If the guess differs from the configured source, the page is recognised
  again with the matching head. Detection runs again too; this is the cost of
  auto-detection. The second result is kept only if it is non-empty.
- A guess that is not user-facing (currently Korean) is ignored; see §7.

### 3.8 Translation (`mt`)

**Tokenisation (`SpmEncoder`).** This is a pure-Java SentencePiece *unigram*
encoder. `tools/convert_mt.py` flattens the protobuf model into a
`piece<TAB>logprob` TSV. Segmentation is exact Viterbi (a shortest path over
log-probabilities). Unknown characters cost −10. `▁` (U+2581) marks word
boundaries. This code fails quietly, not loudly, which is why it has unit tests.

**Vocabularies (`MtVocab`).** Pieces are mapped to ids through `vocab.tsv`,
which is the *target* vocabulary and also decodes the output. Most OPUS-MT
releases use one joint vocabulary, so that single table serves both sides.

The en-ko model (`opus-mt-tc-big-en-ko`) is different. It was trained with
separate source and target vocabularies over one tied embedding matrix, so
English must be encoded with its own table, `source_vocab.tsv`, which
`MarianTranslator` uses whenever the file is present.

The published Hugging Face tokenizer for that model ships only the Korean
vocabulary. As a result, the unmodified checkpoint (and anything exported from
it) turns English input into wrong ids and emits fluent nonsense. Only 20.8% of
its source pieces even exist in the published vocabulary.
`tools/mt_train/fix_en_ko_base.py` builds a corrected copy. `convert_mt.py`
uses it and writes `source_vocab.tsv`. Any en-ko model exported before this
fix must be re-exported.

**Decoding (`MarianTranslator`).**

- The encoder runs once per chunk. The decoder runs greedily from
  `decoderStartId` until `eos`/`pad` is emitted, or until
  `min(config.maxLength, max(16, 3·n_src + 8))` tokens.
- Input longer than 192 source tokens is split at sentence punctuation
  (`. ! ? 。 ！ ？ …` and newline). A single overlong sentence is sent whole,
  never cut mid-clause.
- **No KV cache.** The export is `use_cache=False`, so producing *n* tokens
  costs `Σ t = O(n²)` decoder positions, instead of O(n) with a cache. This is
  acceptable for OCR-length inputs. It is the first thing to change for
  long-document throughput.
- Graph input names are resolved by exact match, then by substring, because
  Optimum has renamed them between releases.
- Special tokens (`<…>`) are dropped before detokenisation.

**Routing (`PivotTranslator`).** OPUS-MT has no CJK↔CJK models. For those
six directions the translator runs `src → en → tgt`, each leg as a whole-page
batch. A direct model placed in `assets/model/mt/<src>-<tgt>/` is always
preferred and needs no code change. `isPivoted()` drives the UI note
*"via English — slower, lower quality"*.

**Line redistribution.** Each paragraph is translated as a unit. The result is
then split across the paragraph's lines in proportion to source-line length,
preferring whitespace boundaries. Only the per-line render mode and the
editable text view use this split.

---

## 4. Rendering model (`render`)

### 4.1 Overview

`LayoutRenderer.render(source, result, options)` returns a **new** ARGB_8888
bitmap and never modifies the source. It works on *blocks*. A block is one
translated paragraph (default) or one line (`perLine`), and carries:

- `text`: the translation.
- `target`: the upright layout rectangle. For rotated blocks this is the
  unrotated extent, centred on the block's bounds.
- `angle`: the median line angle, so one skewed detection cannot tilt the
  paragraph. Angles under 0.75° are treated as 0.
- `ink`, `paper`: sampled colours (§3.5).
- `sources`: the original line quads.

Blocks without a translation are **skipped entirely**, so the original text is
left untouched instead of being faded with nothing to replace it.

Rendering runs in two passes: **all highlights first, then all text**. A
neighbouring block's highlight therefore never fades glyphs that were already
drawn.

### 4.2 Highlight (replaces the former opaque erase)

Earlier versions filled every detected line with an opaque patch of the sampled
paper colour. The translation then had a solid background of its own, which
read as a sticker and showed up as a flat patch over photos, gradients and
paper texture.

The renderer now lays down a **faint, soft-edged highlight** instead:

- **Area.** The union (`Path.op(UNION)`) of every source quad in the block,
  each grown 6% about its centre, plus the layout rectangle grown by the same
  amount and rotated with the block. Unioning before filling matters: overlapping
  translucent fills would double up and leave darker bands between lines.
- **Fill.** The block's sampled paper colour at `highlightAlpha`, default
  **150 / 255 ≈ 0.59**.
- **Shape.** Rounded corners (`CornerPathEffect`, radius 0.18 × line height)
  and a feathered edge (`BlurMaskFilter NORMAL`, radius 0.06 × line height).
  The mask filter is honoured because the canvas is bitmap-backed, which means
  software rendering.

Compositing is the usual source-over:

```
C_out = α·P + (1 − α)·C_page
```

So the original text's contrast against the paper falls to `(1 − α) ≈ 41%`.
It stays visible as a ghost, and the page texture shows through.

### 4.3 Typesetting and halo

- The canvas is rotated by `angle` about the target's centre, and the text is
  laid out upright in `target`. Rotating the canvas keeps line breaking, which
  rotating glyph runs by hand would lose.
- **Size fitting (`TextFitter`).** This finds the largest size `s` in
  `[0.45·p, 1.15·p]` whose `StaticLayout` height fits the target, where
  `p = 0.82 × line height`. It is a binary search to 0.25 px, which relies on
  layout height being non-decreasing in `s`. If even the minimum size
  overflows, it is used anyway and flagged (`Fit.overflowed = true`). No clip is
  set, so the text runs past the bottom of its box rather than being cut off;
  overflowing text is better than a blank. Line breaking
  uses `BREAK_STRATEGY_HIGH_QUALITY`; without it, CJK text never wraps.
- **Halo (`halo = true`).** The same `StaticLayout` is drawn twice. First
  as a stroke in the paper colour, width `0.16 × fitted size` with round joins,
  then as a fill in the ink colour. Stroke width does not change glyph advances,
  so the fitted line breaks still hold. The halo carries legibility over the
  ghosted original, so the highlight itself can stay faint.
- **Typeface.** `Typeface.DEFAULT`. Font fallback covers Hangul, Kana and Han
  without bundling a font.

### 4.4 Options

| Field | Default | Effect |
|---|---|---|
| `highlightAlpha` | `LayoutRenderer.DEFAULT_HIGHLIGHT_ALPHA` = 150 | 0 = no highlight; 255 = opaque, behaving like the old erase |
| `halo` | `true` | Paper-coloured outline behind glyphs |
| `perLine` | `false` | Typeset each line in its own quad instead of reflowing paragraphs |
| `debugBoxes` | `false` | Outline each target: blue if the text fits, red if it overflowed |

Tuning guidance:

- If the original shows through too strongly on busy backgrounds, raise
  `highlightAlpha` (e.g. 180–200) before disabling the halo.
- To get the old solid-background look, set `highlightAlpha = 255`.

### 4.5 Known limits

- The typeface, weight and letterforms of the original are not reproduced.
- Very high-contrast source text behind a short translation can remain visible
  outside the new glyphs. This is inherent to a translucent highlight. An
  inpainting model is the principled fix; see §9.
- The paragraph highlight covers the rectangle the paragraph occupies, so a
  ragged-right paragraph also highlights the empty tails of short lines.

---

## 5. PDF and document output (`pdf`)

- `PdfPageSource` rasterises each page at **200 dpi** with the platform
  `PdfRenderer`.
- `PdfJob` runs the pipeline page by page and writes one of the following,
  set by `Prefs.pdfOutput()`:
  - **PDF**: repainted pages, drawn into a `PdfDocument` and scaled back from
    200 dpi pixels to points, so each page keeps its physical size.
  - **DOCX**: page texts via `DocxWriter`, a minimal OOXML writer with XML
    escaping (unit-tested).
  - **TXT**: page texts joined with blank lines, UTF-8.
- Only PDF output enables rendering. DOCX and TXT need text alone, so
  rendering is skipped for them; it would cost seconds per page.
- A page's text is its translation, or the recognised original when the
  translation is empty.
- `Listener.isCancelled()` is polled between pages. Output goes to
  `filesDir/exports/translated_<millis>.<ext>`.

---

## 6. Model tree and validation

The layout is defined once in `engine/ModelPaths` and mirrored by
`tools/convert_ocr.py` and `tools/convert_mt.py`. See the model README for the
full tree. Summary:

| Asset | Source | Notes |
|---|---|---|
| `ocr/det/det.onnx` | `ch_PP-OCRv4_det` | Language-independent |
| `ocr/cls/cls.onnx` | PP-OCR v2.0 cls | Optional |
| `ocr/rec/english` | `en_PP-OCRv4_rec` | |
| `ocr/rec/korean` | `korean_PP-OCRv3_rec` | Bundled; not user-facing (§7) |
| `ocr/rec/japan` | `japan_PP-OCRv3_rec` | |
| `ocr/rec/chinese` | `ch_PP-OCRv4_rec` + `ppocr_keys_v1.txt` | |
| `mt/{en↔ko, en↔ja, en↔zh}` | OPUS-MT (`en-ko` is `tc-big`, exported via the corrected tokenizer) | int8 dynamic, per-channel |

`tools/fix_onnx_concat.py` inserts `Unsqueeze` before rank-mismatched `Concat`
inputs emitted by paddle2onnx. Without it, ONNX Runtime refuses to load the v4
recognition models and the classifier.

`ModelValidator.validate` checks the tree at start-up and returns a `Report`:

- Only **user-facing** languages are required. A hidden language's missing files
  do not mark the install incomplete, and its present files do not appear in
  the report shown in Settings.
- Only pairs involving English are *required*. CJK↔CJK pairs do not exist
  upstream and are expected to be pivoted.

---

## 7. Language gating (Korean)

Korean is **implemented end to end** but **withheld from the user interface**:
the recognition head and dictionary, both MT directions, Hangul script
detection, the TTS locale (`Locale.KOREAN`) and the flag all remain.

### 7.1 Mechanism

`core/Lang.java` keeps `KO` in the enum, so that code, tests, stored preferences
and history rows keep compiling and resolving. A separate, commented list
controls what users can see:

```java
private static final Lang[] USER_FACING = {
        EN,
        // KO, // Korean: implemented, hidden from the UI. Uncomment to enable.
        JA,
        ZH,
};
```

API:

| Method | Purpose |
|---|---|
| `Lang.userFacing()` | Copy of the list, in picker order |
| `lang.isUserFacing()` | Membership test |
| `Lang.userFacingOr(code, fallback)` | Parse; fall back for unknown **or hidden** codes |

### 7.2 Call sites that enforce it

| Site | Behaviour |
|---|---|
| `ui/LanguageActivity.rebuild` | The picker lists `userFacing()` only; search cannot find Korean |
| `data/Prefs.sourceLang/targetLang` | A stored `"ko"` resolves to the default (EN / ZH) |
| `engine/TranslationPipeline.process` | A Hangul-based auto-detection guess is ignored; the configured source is kept |
| `engine/ModelValidator.validate` | Only user-facing languages and pairs are checked and reported |
| `ui/SettingsActivity.showModelReport` | "Routed through English" lists user-facing pairs only |
| `ui/SettingsActivity.showHelp` | Help text names Japanese and Chinese only |

`Lang.fromCode`/`fromCodeOr` are unchanged, so `HistoryStore` still reads
old Korean rows correctly. History does not display language names.

### 7.3 Re-enabling

Uncomment `KO` in `Lang.USER_FACING`, then restore "Korean," in the help text in
`SettingsActivity.showHelp`. No other change is needed. Update
`LangTest.koreanIsImplementedButNotUserFacing` to match.

---

## 8. Build, test, verify

```sh
tools/fetch_models.sh      # once; needs python3; ~230 MB
./gradlew test             # JVM unit tests
./gradlew assembleDebug
```

JVM tests cover the code that fails quietly: SentencePiece Viterbi,
CTC collapsing and dictionary indexing, DB post-processing, script detection,
language-code parsing (including Korean gating), and OOXML escaping. The
renderer depends on `android.graphics` and has no JVM tests. Check it on a
device with `Options.debugBoxes = true`, with at least:

1. dark text on white paper;
2. white text on a dark or coloured sign;
3. text over a photograph or gradient;
4. a rotated paragraph (≥ 5°);
5. a translation much longer than the source, which should show a red overflow box.

---

## 9. Extension points and roadmap

| Area | Change | Where |
|---|---|---|
| MT speed | Export `decoder_with_past` and thread the KV cache: O(n²) → O(n) | `tools/convert_mt.py`, `MarianTranslator.greedyDecode` |
| MT quality | Beam search (≈k× cost), or direct CJK↔CJK models (NLLB, M2M) | `MarianTranslator`; `assets/model/mt/<pair>/` |
| Rendering | Inpaint the source glyphs (e.g. a mobile LaMa) before highlighting | `LayoutRenderer.highlight` |
| Rendering | Per-line highlight shapes for ragged paragraphs | `LayoutRenderer.paragraphBlocks` |
| Detection | Vertical CJK text (`TextLine.isVertical` exists, unused by the renderer) | `LineGrouper`, `LayoutRenderer` |
| Language ID | Kana-less Japanese: character-bigram LID | `ScriptDetector` |
| Distribution | Move models into a Play Asset Delivery install-time pack | Gradle, `Assets` |
| Languages | Add a language: enum entry, `ModelPaths` directory, flag, TTS locale, conversion script entry, then add it to `USER_FACING` | `core`, `engine`, `ui`, `tools` |

---

## 10. Licensing

The application code belongs to the repository owner. The model weights do not:

- PaddleOCR is Apache-2.0.
- OPUS-MT is CC-BY 4.0 and **requires attribution in the shipped app**. The
  About dialog carries it.

Check both before any distribution.
