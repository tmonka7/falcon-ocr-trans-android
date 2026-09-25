# falcon-ocr-trans

Offline OCR and translation for Android. Point it at a photo, an image or a PDF;
it finds the text, translates it, and paints the translation back over the page
in place of the original, keeping the layout.

Java, Gradle 8.13, no network permission. English, Korean, Japanese and Chinese.

## Status

The application is complete and builds. **The model tree is not in the repo** —
it is ~230 MB of third-party weights. Run `tools/fetch_models.sh` once before the
app can do anything; until then it starts, reports precisely which files are
missing, and refuses to pretend otherwise.

```sh
tools/fetch_models.sh     # downloads and converts; needs python3
./gradlew assembleDebug
```

## How it works

```
 image / PDF page
        │
        ▼
 ┌─────────────────┐   PP-OCRv4 detection, ONNX Runtime
 │  text detection │   → probability map → DB post-process → rotated boxes
 └────────┬────────┘
          ▼
 ┌─────────────────┐   perspective-corrected crop per box
 │ angle + recog.  │   → 180° classifier → PP-OCR recognition → CTC decode
 └────────┬────────┘
          ▼
 ┌─────────────────┐   lines sorted into reading order, merged into paragraphs
 │  line grouping  │   so the translator sees sentences, not fragments
 └────────┬────────┘
          ▼
 ┌─────────────────┐   OPUS-MT int8, greedy decode
 │   translation   │   CJK↔CJK pivots through English (no direct model exists)
 └────────┬────────┘
          ▼
 ┌─────────────────┐   erase each box with its sampled paper colour,
 │ layout re-paint │   re-typeset at the fitted size in the sampled ink colour
 └─────────────────┘
```

### Package map

| Package | What lives there |
|---|---|
| `core` | `Lang`, `Quad`, `TextLine`, `Paragraph`, `OcrResult` |
| `ocr` | ONNX sessions, DB post-processing, CTC decoding, line grouping |
| `mt` | SentencePiece, vocabulary, Marian greedy decode, English pivot |
| `render` | Erase and re-typeset, with size fitting |
| `pdf` | Page rasterizing, PDF/DOCX/TXT output |
| `engine` | Model paths and validation, pipeline, shared engine thread |
| `data` | Preferences, SQLite history |
| `ui` | Activities and adapters |

## Decisions worth knowing about

**ONNX Runtime, not Paddle Lite.** PaddleOCR's own Android demo is C++ and
OpenCV over Paddle Lite `.nb` files. Converting the same weights to ONNX keeps
everything in Java with no NDK layer; the cost is that Differentiable
Binarization post-processing — contours, minimum-area rectangles, polygon
dilation — is reimplemented in `DbPostProcessor` instead of coming from OpenCV
and Clipper.

**Six MT models, not twelve.** Helsinki-NLP publishes OPUS-MT for every pair
involving English and none for CJK-to-CJK; `Helsinki-NLP/opus-mt-ko-ja` does not
exist. `PivotTranslator` chains `ko→en→ja` for those six directions. It is about
twice as slow and compounds errors, and the UI says so on the affected pairs.
Drop a genuine direct model into `assets/model/mt/ko-ja/` and it wins
automatically.

**No KV cache in the decoder.** `decoder_model.onnx` is the cacheless export, so
decoding is O(n²) in attention. The inputs are OCR lines and short paragraphs,
where that stays cheap. It is the first thing to revisit for long documents.

**Layout preservation has limits.** Position, block geometry, rotation, relative
size, ink and paper colour all survive. Typeface does not — the system font is
substituted. On flat backgrounds the result reads as reset text; over a
photograph the erase step shows as a flat patch, which is the cost of not
running an inpainting model.

**`ja`, not `jp`.** `jp` is a country code. Model directories, preferences and
history all use `ja`; `Lang.fromCode` still accepts `"jp"`.

## Distribution

The universal debug APK is ~78 MB before models and ~255 MB with them, which is
over the 150 MB Google Play limit. Sideloading and internal testing work as is;
for Play, the model tree needs to move into an install-time [Play Asset
Delivery](https://developer.android.com/guide/playcore/asset-delivery) pack. See
`app/src/main/assets/model/README.md`.

## Tests

```sh
./gradlew test
```

48 JVM tests covering the parts that fail silently rather than loudly: the
SentencePiece Viterbi segmentation, CTC collapsing and the dictionary index
arithmetic, detection post-processing, script detection, language-code parsing,
and the OOXML writer's escaping.

## Licensing

The code here is yours. The **models are not** — they carry their own terms, and
OPUS-MT's CC-BY 4.0 requires attribution in the shipped app. The About dialog
carries it; check both before publishing.
