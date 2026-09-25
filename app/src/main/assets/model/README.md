# Bundled models

Everything under this directory except this file is **gitignored**. The tree is
roughly 230 MB, which does not belong in version control. Populate it with:

```sh
tools/fetch_models.sh            # both stages
tools/fetch_models.sh --ocr-only # just PaddleOCR
tools/fetch_models.sh --mt-only  # just OPUS-MT
```

The app validates this tree at startup (`ModelValidator`) and names any file it
cannot find, so a partial download fails with a list rather than a stack trace.

## Expected layout

```
model/
├── ocr/
│   ├── det/det.onnx                  PP-OCRv4 detection, language independent
│   ├── cls/cls.onnx                  180° angle classifier (optional)
│   └── rec/
│       ├── english/{rec.onnx,dict.txt}
│       ├── korean/{rec.onnx,dict.txt}
│       ├── japan/{rec.onnx,dict.txt}
│       └── chinese/{rec.onnx,dict.txt}
└── mt/
    ├── en-ko/  ko-en/
    ├── en-ja/  ja-en/
    └── en-zh/  zh-en/
        ├── encoder.int8.onnx
        ├── decoder.int8.onnx
        ├── source.spm.tsv            piece <TAB> log-probability
        ├── vocab.tsv                 token  <TAB> id
        └── config.json               special token ids, decode limits
```

Paths are defined once in `engine/ModelPaths.java`. If you change them there,
change `tools/convert_ocr.py` and `tools/convert_mt.py` to match.

## Why the ONNX graphs get patched after conversion

`tools/convert_ocr.py` runs `tools/fix_onnx_concat.py` over every model it
exports. This is not optional tidying — without it ONNX Runtime refuses to load
the PP-OCRv4 recognition models and the angle classifier at all:

```
[ShapeInferenceError] All inputs to Concat must have same rank.
Input 2 has rank 0 != 1
```

paddle2onnx emits `Concat` nodes that assemble a shape vector from a mix of
rank-1 components and rank-0 scalars. Paddle's own runtime accepts that; the
ONNX spec does not. The fix inserts an `Unsqueeze` promoting each scalar to a
one-element vector, which is numerically a no-op and exactly what the graph
meant. It only touches `Concat` nodes whose widest input is rank 1, so real
feature-tensor concatenations are left alone.

Interestingly the two PP-OCRv3 models (Korean, Japanese) and the detector are
unaffected — only the v4 exports and the v2.0 classifier carry the defect.

## Why `dict.txt` must match `rec.onnx`

The recognition head predicts class indices, and the dictionary turns them into
characters. The label set is *the dictionary wrapped in two extras*: a CTC blank
at index 0 and, for models trained with `use_space_char`, a space appended at the
end. A mismatched pair does not throw — it shifts every character in every
result. `CharDict.load` therefore checks the file against the model's own output
dimension and refuses to load a pair that disagrees.

## Why there is no `ko-ja`, `ja-zh`, `ko-zh` …

Helsinki-NLP publishes an OPUS-MT model for every pair involving English and
none for the CJK-to-CJK directions — `Helsinki-NLP/opus-mt-ko-ja` does not
exist. Those six directions are served at runtime by `PivotTranslator`, which
chains `ko→en` and `en→ja`.

This costs two full encode-decode passes, so a pivoted pair takes about twice as
long, and errors from the first model feed the second. If you obtain a genuine
direct model for one of these pairs, drop it in as `mt/ko-ja/` in the layout
above and it will be preferred automatically — no code change.

## Size and distribution

| Component | Approx. size |
|---|---|
| OCR detection + classifier | 5 MB |
| OCR recognition × 4 scripts | 35 MB |
| OPUS-MT int8 × 6 directed pairs | 190 MB |
| **Total** | **~230 MB** |

This exceeds the 150 MB Google Play APK limit. For Play distribution the model
tree needs to move into [Play Asset
Delivery](https://developer.android.com/guide/playcore/asset-delivery) as an
`install-time` asset pack; for sideloading and internal testing the universal
APK is fine as is.

Model blobs are declared `noCompress` in `app/build.gradle` so ONNX Runtime can
map them straight out of the APK instead of inflating each one onto the heap.

## Licensing

These are third-party weights with their own terms, which are **not** covered by
this repository's licence. Check them before shipping:

- **PaddleOCR** models — Apache 2.0.
- **OPUS-MT** models — CC-BY 4.0, which requires attribution in the shipped app.
