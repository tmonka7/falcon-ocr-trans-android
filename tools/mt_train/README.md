# Korean ↔ English MT retraining

This folder fine-tunes the app's two Korean translation models on public parallel
data, evaluates them the way the app runs them, and exports them into the app's
model tree.

| Direction | Base checkpoint | Size | Licence |
|---|---|---|---|
| ko → en | `Helsinki-NLP/opus-mt-ko-en` | 77.9 M params (transformer-base) | Apache-2.0 |
| en → ko | `Helsinki-NLP/opus-mt-tc-big-en-ko`, **via the corrected copy below** | 211.2 M params (transformer-big) | CC-BY 4.0 |

## ⚠ The published en → ko model is broken as distributed

The Hugging Face release of `opus-mt-tc-big-en-ko` ships only the **Korean**
vocabulary as `vocab.json`. The original Marian model has separate source and
target vocabularies over one shared embedding matrix. So the Hugging Face
tokenizer maps English pieces through the Korean table:

- Only 20.8 % of the 32 000 English pieces exist in that table.
- The pieces that do exist get the wrong ids.

The output is fluent nonsense:

```
"2, 4, 6 etc. are even numbers."  ->  "그들은,우리는,우리는 모자입니다. 신뢰할 수 있습니다."   (as published)
                                  ->  "2, 4, 6 등은 짝수입니다."                         (fixed; matches the model card)
```

**The weights are fine.** The English vocabulary is exactly the piece order of the
repository's own `source.spm`. That was verified against the original Marian
`src.vocab`: all 32 000 pieces are identical, in the same order.
[`fix_en_ko_base.py`](fix_en_ko_base.py) rebuilds the tokenizer files and checks
the result against the model card.

**The app is affected too.** Its en → ko export came from this checkpoint, so
every direction that translates *into* Korean is broken today. Korean is hidden
in the UI, so users don't see it yet. The fix has three parts, all already made:

- `tools/convert_mt.py` now exports through the corrected copy and also writes
  `source_vocab.tsv`.
- `MarianTranslator` encodes with `source_vocab.tsv` when it is present.
- **Action: re-export en-ko** (`python tools/convert_mt.py --only en-ko`, or
  `export.py` below) before enabling Korean.

The other five models in the app use joint vocabularies and were checked. Their
source-side coverage is 90–100 %.

## What fine-tuning adds

The published checkpoints were trained on general OPUS data, much of it the same
as this data mix. So large gains on general test sets aren't expected. The
fine-tuning targets what the app actually sees:

- **OCR noise.** 30 % of training sources get OCR-style corruption
  (`ocr_noise.py`); targets stay clean. The corruption includes:
  - look-alike characters (rn→m, l→1, O→0);
  - Hangul vowel and consonant confusions (ㅐ/ㅔ, ㅓ/ㅕ, ㄱ/ㅋ);
  - fused and split words, hyphenation artefacts, and ALL-CAPS signage.

  One corruption is aimed at an app-specific bug. The app joins wrapped Korean
  lines *without* a space, and `fuse_spaces` reproduces that.
- **Short-text domain.** The mix includes software UI strings (KDE, GNOME,
  translatewiki), command help (tldr), and capped entity and title pairs. These
  resemble signs, labels and buttons.
- **Deployment-matched evaluation.**
  - Decoding is greedy, as in the app.
  - chrF++ picks the best checkpoint.
  - The exported **int8** model can be scored through the app's exact decoding
    path (`NAME=onnx:<asset dir>`). int8 drift is real: on the en → ko probes,
    2 of 6 greedy outputs change after quantisation.

## Setup

```sh
python -m venv .venv && . .venv/bin/activate            # Windows: .venv\Scripts\activate
pip install torch --index-url https://download.pytorch.org/whl/cu124   # pick your CUDA build
pip install -r tools/mt_train/requirements.txt
python -m pytest tools/mt_train/tests -q                # 24 tests, no downloads
```

## 1. Prepare the data

```sh
python tools/mt_train/prepare_data.py                   # core profile, ~300 MB download
python tools/mt_train/prepare_data.py --profile large   # + capped ParaCrawl, OpenSubtitles, CCMatrix (~2.5 GB)
```

Pipeline, all deterministic per `--seed`:

1. Resolve the latest versions through the OPUS API and cache the downloads.
2. Apply NFKC (as the app's `SpmEncoder` does) and strip corpus debris.
3. Filter each pair: length, length ratio, script checks per side (copied Latin
   product names allowed), URLs, markup and citation boilerplate.
4. Remove duplicates.
5. **Decontaminate:** drop every pair whose English or Korean side appears in
   any evaluation set.
6. Hash-split out dev and test.

`data/en-ko/manifest.json` records the resolved versions, URLs, per-corpus
reject reasons and file hashes.

**Core profile result:** see the tables in [Results](#results).

Evaluation sets (never trained on):

| File | Source | Pairs | Licence |
|---|---|---|---|
| `tatoeba_test.jsonl` | Tatoeba-Challenge eng-kor test (official) | 2 479 | CC-BY 2.0 FR |
| `tatoeba_dev.jsonl` | Tatoeba-Challenge eng-kor dev | 1 129 | CC-BY 2.0 FR |
| `flores_devtest.jsonl` / `flores_dev.jsonl` | FLORES-200 eng_Latn / kor_Hang | 1 012 / 997 | CC-BY-SA 4.0 |
| `app_domain.jsonl` | [`eval/app_domain.tsv`](eval/app_domain.tsv): signs, menus, UI, forms, labels, medical, transit | 91 | this repo |
| `test.jsonl` / `dev.jsonl` | held-out slice of the training mix | ~2 000 each | as sources |

`eval/app_domain.tsv` was written by hand **without native-speaker review**.
Have it checked before reporting results on it.

## 2. Train

```sh
python tools/mt_train/train.py --direction ko-en                                  # ~1.5 M pairs, 2 epochs
python tools/mt_train/train.py --direction en-ko --batch-size 16 --grad-accum 2   # big model
```

Defaults:

| Setting | Default |
|---|---|
| Learning rate | 5e-5 (ko-en), 2e-5 (en-ko) |
| Warm-up | 3 % |
| Label smoothing | 0.1 |
| Max length | 128 tokens |
| Noise probability | 0.3 |
| Evaluation and checkpoint | every 2 000 steps on 1 000 dev pairs, keeping the best by chrF |
| Early stopping | 4 evaluations |

Precision is bf16 or fp16 automatically on CUDA.

Before saving, the script checks that the vocabulary and the special-token ids
are unchanged, because the app's `vocab.tsv` and `config.json` depend on them.
`runs/<dir>/training_summary.json` records the baseline and final dev scores.

Rough GPU guidance (estimates, not measurements). Full fine-tuning with AdamW
needs about 16 bytes per parameter before activations:

| Direction | Weights + optimiser | Fits |
|---|---|---|
| ko → en | ~1.3 GB | 8 GB GPU, batch 32 |
| en → ko | ~3.4 GB | 16 GB at batch 16, or 12 GB with `--batch-size 8 --grad-accum 4 --gradient-checkpointing` |

CPU training works (used for the smoke tests) but is only practical for a few
hundred steps.

## 3. Evaluate

```sh
python tools/mt_train/evaluate.py --direction ko-en                      # base vs runs/ko-en/final
python tools/mt_train/evaluate.py --direction en-ko \
    --model tuned=tools/mt_train/runs/en-ko/final \
    --model tuned_int8=onnx:app/src/main/assets/model/mt/en-ko
```

Each set is scored on clean sources and on OCR-noised sources (fixed seed).
BLEU uses `tokenize=char` for Korean targets and `13a` for English targets. The
script writes `report.md` and `report.json`, including side-by-side samples from
`app_domain`.

## 4. Export into the app

```sh
python tools/mt_train/export.py --direction ko-en
python tools/mt_train/export.py --direction en-ko
```

Export reuses `tools/convert_mt.py` (ONNX, dynamic int8, TSV tables) and keeps
the previous model in `<pair>.bak`. It then runs a parity check that decodes
probe sentences exactly as `MarianTranslator` does:

- Source ids come from the exported TSV tables.
- The encoder runs once and the cacheless decoder is stepped greedily.
- Detokenisation matches `decodePieces`.

The check compares token ids with PyTorch. Ship only if the parity check passes
**and** the int8 evaluation beats the base on `app_domain` and the noisy
conditions without regressing on FLORES or Tatoeba.

## Results

Measured on CPU in this environment, greedy decoding, first 500 sentences per set
(all 91 for `app_domain`). These are **baselines before any fine-tuning**: no
full training run has been done yet, because that needs a GPU.

_(filled in below)_

## Licensing

- The fine-tuned weights inherit the base model's licence: Apache-2.0 for
  ko-en, and CC-BY 4.0 for en-ko, which requires attribution.
- They also inherit obligations from the training data:
  - TED2020 and NeuLab-TedTalks are **CC BY-NC-ND** (non-commercial).
  - Several corpora are marked "see OPUS" in [`corpora.py`](corpora.py).
- For a commercial release, retrain with an explicit corpus list that excludes
  non-commercial data, e.g. `--corpus WikiMatrix --corpus KDE4 ...`, and check
  each corpus page.

## Files

| File | Purpose |
|---|---|
| `prepare_data.py` | download, clean, decontaminate, split |
| `corpora.py` | corpus catalogue, caps, profiles, licences |
| `textnorm.py` | normalisation and pair filters |
| `ocr_noise.py` | OCR-style source corruption |
| `fix_en_ko_base.py` | corrected en → ko base checkpoint |
| `train.py` | fine-tuning (Seq2SeqTrainer) |
| `evaluate.py` | base vs tuned vs exported-int8 comparison |
| `export.py` | export into the app plus parity check |
| `eval/app_domain.tsv` | hand-written domain test set (draft) |
| `tests/` | unit tests for filters and noise |
