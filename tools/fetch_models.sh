#!/usr/bin/env bash
# Download the PaddleOCR weights and dictionaries, then run both converters.
#
# Usage:  tools/fetch_models.sh [--ocr-only | --mt-only]
#
# Everything lands in app/src/main/assets/model/, which is gitignored: the tree
# is roughly 230 MB and does not belong in version control.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DOWNLOAD_DIR="$REPO_ROOT/build/models/paddle"
ASSETS_DIR="$REPO_ROOT/app/src/main/assets/model"

DO_OCR=1
DO_MT=1
case "${1:-}" in
  --ocr-only) DO_MT=0 ;;
  --mt-only)  DO_OCR=0 ;;
  "")         ;;
  *)          echo "unknown option: $1" >&2; exit 2 ;;
esac

PADDLE_BASE="https://paddleocr.bj.bcebos.com"
DICT_BASE="https://raw.githubusercontent.com/PaddlePaddle/PaddleOCR/release/2.7/ppocr/utils"

# name|url — detection and the angle classifier are language independent.
ARCHIVES=(
  "ch_PP-OCRv4_det_infer|$PADDLE_BASE/PP-OCRv4/chinese/ch_PP-OCRv4_det_infer.tar"
  "ch_PP-OCRv4_rec_infer|$PADDLE_BASE/PP-OCRv4/chinese/ch_PP-OCRv4_rec_infer.tar"
  "en_PP-OCRv4_rec_infer|$PADDLE_BASE/PP-OCRv4/english/en_PP-OCRv4_rec_infer.tar"
  "korean_PP-OCRv3_rec_infer|$PADDLE_BASE/PP-OCRv3/multilingual/korean_PP-OCRv3_rec_infer.tar"
  "japan_PP-OCRv3_rec_infer|$PADDLE_BASE/PP-OCRv3/multilingual/japan_PP-OCRv3_rec_infer.tar"
  "ch_ppocr_mobile_v2.0_cls_infer|$PADDLE_BASE/dygraph_v2.0/ch/ch_ppocr_mobile_v2.0_cls_infer.tar"
)

# The recogniser's class count must match its dictionary exactly, so each
# dictionary has to come from the same PaddleOCR release as its weights.
DICTS=(
  "en_dict.txt|$DICT_BASE/en_dict.txt"
  "korean_dict.txt|$DICT_BASE/dict/korean_dict.txt"
  "japan_dict.txt|$DICT_BASE/dict/japan_dict.txt"
  "ppocr_keys_v1.txt|$DICT_BASE/ppocr_keys_v1.txt"
)

need() {
  command -v "$1" >/dev/null 2>&1 || { echo "required tool not found: $1" >&2; exit 1; }
}

# Windows installs the interpreter as "python"; most Linux and macOS setups use
# "python3" and may have a stub "python" that is Python 2 or absent entirely.
PYTHON=""
for candidate in python3 python py; do
  if command -v "$candidate" >/dev/null 2>&1 \
     && "$candidate" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 9) else 1)' 2>/dev/null; then
    PYTHON="$candidate"
    break
  fi
done
if [[ -z "$PYTHON" ]]; then
  echo "Python 3.9 or newer is required but was not found on PATH." >&2
  exit 1
fi

fetch_ocr() {
  need curl
  need tar
  mkdir -p "$DOWNLOAD_DIR/dicts"

  for entry in "${ARCHIVES[@]}"; do
    name="${entry%%|*}"
    url="${entry##*|}"
    if [[ -d "$DOWNLOAD_DIR/$name" ]]; then
      echo "  have $name"
      continue
    fi
    echo "  downloading $name"
    curl -fsSL --retry 3 "$url" -o "$DOWNLOAD_DIR/$name.tar"
    tar -xf "$DOWNLOAD_DIR/$name.tar" -C "$DOWNLOAD_DIR"
    # On Windows a virus scanner or the search indexer can still hold the
    # archive open the instant tar releases it. The extraction already
    # succeeded, so a failed cleanup must not abort the run.
    rm -f "$DOWNLOAD_DIR/$name.tar" 2>/dev/null || true
  done

  for entry in "${DICTS[@]}"; do
    name="${entry%%|*}"
    url="${entry##*|}"
    if [[ -s "$DOWNLOAD_DIR/dicts/$name" ]]; then
      echo "  have $name"
      continue
    fi
    echo "  downloading $name"
    curl -fL --retry 3 -s "$url" -o "$DOWNLOAD_DIR/dicts/$name"
  done

  echo "converting OCR models to ONNX"
  "$PYTHON" "$REPO_ROOT/tools/convert_ocr.py" \
    --download-dir "$DOWNLOAD_DIR" \
    --assets-dir "$ASSETS_DIR/ocr"
}

fetch_mt() {
  # interpreter already resolved above
  echo "exporting OPUS-MT pairs (this downloads ~1 GB of full-precision weights"
  echo "into build/models/mt and writes ~200 MB of int8 ONNX into assets)"
  "$PYTHON" "$REPO_ROOT/tools/convert_mt.py" \
    --assets-dir "$ASSETS_DIR/mt" \
    --work-dir "$REPO_ROOT/build/models/mt"
}

mkdir -p "$ASSETS_DIR"

if [[ $DO_OCR -eq 1 ]]; then
  echo "== OCR models =="
  fetch_ocr
fi

if [[ $DO_MT -eq 1 ]]; then
  echo
  echo "== translation models =="
  fetch_mt
fi

echo
echo "done. Model tree:"
du -sh "$ASSETS_DIR" 2>/dev/null || true
find "$ASSETS_DIR" -name '*.onnx' | sort
