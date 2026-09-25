#!/usr/bin/env python3
"""Export OPUS-MT pairs to int8 ONNX plus the Java-readable side tables.

Run this once on a desktop. Requires::

    pip install "optimum[onnxruntime]" transformers sentencepiece

For each directed pair this writes::

    assets/model/mt/<from>-<to>/
        encoder.int8.onnx     quantised encoder
        decoder.int8.onnx     quantised decoder, cacheless variant
        source.spm.tsv        piece <TAB> log-probability
        vocab.tsv             token  <TAB> id
        config.json           special token ids and decode limits

The two TSVs exist so the app does not have to parse SentencePiece protobuf or
JSON vocabularies on a phone; ``SpmEncoder`` and ``MtVocab`` read them directly.

Only pairs involving English are exported, because Helsinki-NLP publishes no
CJK-to-CJK OPUS-MT model. The app's ``PivotTranslator`` chains two of these to
serve ko-ja, ja-zh and the rest.
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

# Directed pair -> Hugging Face repository.
# The repo names are not uniform: en->ko only exists as a "tc-big" release, and
# en->ja is published under the three-letter code "jap". These were verified to
# resolve; substituting a different checkpoint is fine as long as it is a Marian
# model, since everything below is driven by the tokenizer and config it ships.
PAIRS = {
    ("en", "ko"): "Helsinki-NLP/opus-mt-tc-big-en-ko",
    ("ko", "en"): "Helsinki-NLP/opus-mt-ko-en",
    ("en", "ja"): "Helsinki-NLP/opus-mt-en-jap",
    ("ja", "en"): "Helsinki-NLP/opus-mt-ja-en",
    ("en", "zh"): "Helsinki-NLP/opus-mt-en-zh",
    ("zh", "en"): "Helsinki-NLP/opus-mt-zh-en",
}


def export_pair(repo: str, src: str, tgt: str, out_root: Path, work_root: Path,
                keep_work: bool = False) -> None:
    from optimum.onnxruntime import ORTModelForSeq2SeqLM, ORTQuantizer
    from optimum.onnxruntime.configuration import AutoQuantizationConfig
    from transformers import AutoTokenizer, AutoConfig

    pair = f"{src}-{tgt}"
    out_dir = out_root / pair
    out_dir.mkdir(parents=True, exist_ok=True)
    work_dir = work_root / pair
    work_dir.mkdir(parents=True, exist_ok=True)

    print(f"\n=== {pair}  ({repo}) ===")

    # The tokenizer must be saved explicitly: save_pretrained on the ORT model
    # writes only the graphs and config, so source.spm would otherwise never
    # land in the work directory for write_spm_table to read.
    tokenizer = AutoTokenizer.from_pretrained(repo)
    tokenizer.save_pretrained(work_dir)

    # use_cache=False gives the cacheless decoder_model.onnx that MarianTranslator
    # steps. The with-past variant would be faster but needs several dozen cache
    # tensors threaded through every decode step by name.
    print("  exporting to ONNX ...")
    model = ORTModelForSeq2SeqLM.from_pretrained(repo, export=True, use_cache=False)
    model.save_pretrained(work_dir)

    print("  quantising to int8 ...")
    qconfig = AutoQuantizationConfig.avx2(is_static=False, per_channel=True)
    for stem in ("encoder_model", "decoder_model"):
        onnx_path = work_dir / f"{stem}.onnx"
        if not onnx_path.is_file():
            sys.exit(f"expected {onnx_path} from the export; layout changed?")
        quantizer = ORTQuantizer.from_pretrained(work_dir, file_name=f"{stem}.onnx")
        quantizer.quantize(save_dir=work_dir, quantization_config=qconfig)

    # Optimum names quantised files "<stem>_quantized.onnx".
    for stem, target in (("encoder_model", "encoder.int8.onnx"),
                         ("decoder_model", "decoder.int8.onnx")):
        produced = work_dir / f"{stem}_quantized.onnx"
        if not produced.is_file():
            sys.exit(f"quantisation produced no {produced}")
        shutil.copyfile(produced, out_dir / target)
        size_mb = (out_dir / target).stat().st_size / (1024 * 1024)
        print(f"    {target}: {size_mb:.1f} MB")

    config = AutoConfig.from_pretrained(repo)

    write_spm_table(work_dir, out_dir / "source.spm.tsv")
    write_vocab(tokenizer, out_dir / "vocab.tsv")
    write_config(tokenizer, config, src, tgt, out_dir / "config.json")

    # Each pair leaves roughly 750 MB of full-precision and pre-quantisation
    # intermediates behind. Everything needed is now in out_dir, so drop them
    # rather than requiring ~5 GB of scratch to convert the whole set.
    if keep_work:
        print(f"    keeping intermediates in {work_dir}")
    else:
        shutil.rmtree(work_dir, ignore_errors=True)


def write_spm_table(work_dir: Path, target: Path) -> None:
    """Flatten source.spm into ``piece<TAB>score``.

    The scores are the unigram log-probabilities SpmEncoder runs Viterbi over;
    without them the Java side cannot reproduce the reference segmentation.
    """
    import sentencepiece as spm

    spm_file = work_dir / "source.spm"
    if not spm_file.is_file():
        sys.exit(f"missing {spm_file}; the tokenizer did not save its SentencePiece model")

    sp = spm.SentencePieceProcessor(model_file=str(spm_file))
    with target.open("w", encoding="utf-8", newline="\n") as fh:
        for i in range(sp.get_piece_size()):
            piece = sp.id_to_piece(i)
            # A piece containing a tab or newline would break the TSV. None occur
            # in the published models; fail loudly rather than write a bad table.
            if "\t" in piece or "\n" in piece:
                sys.exit(f"piece {i!r} contains a delimiter; TSV format is unsafe here")
            fh.write(f"{piece}\t{sp.get_score(i):.6f}\n")
    print(f"    source.spm.tsv: {sp.get_piece_size()} pieces")


def write_vocab(tokenizer, target: Path) -> None:
    vocab = tokenizer.get_vocab()
    with target.open("w", encoding="utf-8", newline="\n") as fh:
        for token, index in sorted(vocab.items(), key=lambda kv: kv[1]):
            if "\t" in token or "\n" in token:
                sys.exit(f"token {token!r} contains a delimiter; TSV format is unsafe here")
            fh.write(f"{token}\t{index}\n")
    print(f"    vocab.tsv: {len(vocab)} tokens")


def write_config(tokenizer, config, src: str, tgt: str, target: Path) -> None:
    pad = tokenizer.pad_token_id
    payload = {
        "source_lang": src,
        "target_lang": tgt,
        "pad_token_id": pad,
        "eos_token_id": tokenizer.eos_token_id,
        "unk_token_id": tokenizer.unk_token_id,
        # Marian has no dedicated BOS; it starts the decoder on the pad token.
        "decoder_start_token_id": getattr(config, "decoder_start_token_id", pad),
        "max_length": int(getattr(config, "max_length", 256) or 256),
        "vocab_size": int(getattr(config, "vocab_size", len(tokenizer))),
    }
    target.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"    config.json: {payload}")


def main() -> None:
    # Python block-buffers stdout when it is redirected to a file, so progress
    # prints sit unseen for minutes while only stderr warnings reach the log.
    # That makes a long export impossible to follow; force line buffering.
    try:
        sys.stdout.reconfigure(line_buffering=True)
        sys.stderr.reconfigure(line_buffering=True)
    except AttributeError:
        pass

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--assets-dir", type=Path,
                        default=Path("app/src/main/assets/model/mt"))
    parser.add_argument("--work-dir", type=Path, default=Path("build/models/mt"),
                        help="scratch space for full-precision exports")
    parser.add_argument("--only", action="append", metavar="SRC-TGT",
                        help="export just this pair; repeatable")
    parser.add_argument("--keep-work", action="store_true",
                        help="keep per-pair intermediates instead of deleting them")
    args = parser.parse_args()

    wanted = set(args.only or [])
    total = 0
    for (src, tgt), repo in PAIRS.items():
        if wanted and f"{src}-{tgt}" not in wanted:
            continue
        export_pair(repo, src, tgt, args.assets_dir, args.work_dir, args.keep_work)
        total += 1

    if total == 0:
        sys.exit("no pairs matched --only")

    size = sum(f.stat().st_size for f in args.assets_dir.rglob("*") if f.is_file())
    print(f"\n{total} pair(s) written to {args.assets_dir} — {size / (1024 ** 2):.0f} MB total")
    print("CJK-to-CJK directions are served by pivoting through English at runtime.")


if __name__ == "__main__":
    main()
