#!/usr/bin/env python3
"""Builds a corrected copy of Helsinki-NLP/opus-mt-tc-big-en-ko.

    python tools/mt_train/fix_en_ko_base.py            # -> tools/mt_train/base_models/opus-mt-tc-big-en-ko-fixed

**The defect.** The original Marian model (opusTCv20210807-sepvoc, transformer-
big) has *separate* source and target vocabularies but one tied embedding
matrix (``tied-embeddings-all: true``): row i embeds source piece i on the
encoder side and target piece i on the decoder side. The Hugging Face release
ships only the **target** (Korean) vocabulary as ``vocab.json`` and declares a
joint vocabulary, so English input is mapped through the Korean vocabulary:
only 20.8 % of the 32 000 source pieces exist in it at all, and those that do
get the wrong ids. Translation output is garbage, e.g.

    "2, 4, 6 etc. are even numbers."  ->  "그들은,우리는,우리는 모자입니다. ..."

The weights themselves are correct. The source vocabulary is exactly the piece
order of the repository's own ``source.spm`` (verified against the original
Marian ``src.vocab`` file, 32 000 / 32 000 identical), so the fix only
rewrites tokenizer files:

    vocab.json         source pieces in source.spm order, plus <pad> = 32000
    target_vocab.json  the original vocab.json (target pieces, <pad> = 32000)
    tokenizer_config   separate_vocabs = true

After the fix the model card's example translates as documented:
"2, 4, 6 등은 짝수입니다."

The same defect affects the app's current en-ko export (tools/convert_mt.py
wrote the target vocabulary as the app's only vocab.tsv). convert_mt.py now
uses this corrected copy and additionally writes source_vocab.tsv.
"""
from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO_ID = "Helsinki-NLP/opus-mt-tc-big-en-ko"
FIXED_DIR = HERE / "base_models" / "opus-mt-tc-big-en-ko-fixed"
FILES = ["config.json", "generation_config.json", "model.safetensors", "source.spm", "target.spm",
         "vocab.json", "tokenizer_config.json", "special_tokens_map.json"]
PROBE = ("2, 4, 6 etc. are even numbers.", "2, 4, 6 등은 짝수입니다.")   # from the model card


def build(out_dir: Path = FIXED_DIR, verify: bool = True) -> Path:
    import sentencepiece as spm
    from huggingface_hub import hf_hub_download

    out_dir.mkdir(parents=True, exist_ok=True)
    for name in FILES:
        src = Path(hf_hub_download(REPO_ID, name))
        dst = out_dir / name
        if not dst.is_file() or dst.stat().st_size != src.stat().st_size:
            shutil.copyfile(src, dst)

    original = json.loads((out_dir / "vocab.json").read_text(encoding="utf-8"))
    if (out_dir / "target_vocab.json").is_file():
        original = json.loads((out_dir / "target_vocab.json").read_text(encoding="utf-8"))
    pad_id = original["<pad>"]

    sp = spm.SentencePieceProcessor(model_file=str(out_dir / "source.spm"))
    source_vocab = {sp.id_to_piece(i): i for i in range(sp.get_piece_size())}
    if len(source_vocab) != pad_id:
        raise SystemExit(f"source.spm has {len(source_vocab)} pieces; expected {pad_id} to line up with <pad>")
    source_vocab["<pad>"] = pad_id

    # ASCII-escaped like the upstream files: MarianTokenizer opens vocab JSON with the
    # platform default encoding, which breaks on non-ASCII pieces under Windows.
    (out_dir / "target_vocab.json").write_text(json.dumps(original), encoding="utf-8")
    (out_dir / "vocab.json").write_text(json.dumps(source_vocab), encoding="utf-8")
    cfg = json.loads((out_dir / "tokenizer_config.json").read_text(encoding="utf-8"))
    cfg["separate_vocabs"] = True       # target_vocab.json is found by its standard file name
    cfg.pop("target_vocab_file", None)
    (out_dir / "tokenizer_config.json").write_text(json.dumps(cfg, indent=2, ensure_ascii=False), encoding="utf-8")
    (out_dir / "FIXED.md").write_text(__doc__, encoding="utf-8")

    if verify:
        check(out_dir)
    return out_dir


def check(model_dir: Path) -> None:
    """Fails loudly unless the fixed tokenizer reproduces the model card's example."""
    import torch
    from transformers import AutoModelForSeq2SeqLM, AutoTokenizer

    tok = AutoTokenizer.from_pretrained(model_dir)
    if not getattr(tok, "separate_vocabs", False):
        raise SystemExit("tokenizer did not load with separate vocabularies")
    model = AutoModelForSeq2SeqLM.from_pretrained(model_dir).eval()
    with torch.no_grad():
        out = model.generate(**tok([PROBE[0]], return_tensors="pt"), num_beams=1, max_new_tokens=40)
    got = tok.decode(out[0], skip_special_tokens=True).strip()
    print(f"check: {PROBE[0]!r} -> {got!r}")
    if got != PROBE[1]:
        raise SystemExit(f"fixed model does not reproduce the model card ({PROBE[1]!r}); do not use it")
    # Target-side tokenisation (training labels) must use the target vocabulary.
    labels = tok(text_target=[PROBE[1]])["input_ids"][0]
    if tok.decode(labels, skip_special_tokens=True).strip() != PROBE[1]:
        raise SystemExit("target round-trip failed; labels would be tokenised with the wrong vocabulary")


def ensure(out_dir: Path = FIXED_DIR) -> Path:
    """Returns the fixed model directory, building it on first use."""
    if (out_dir / "target_vocab.json").is_file() and (out_dir / "model.safetensors").is_file():
        return out_dir
    print(f"building corrected {REPO_ID} in {out_dir} (one-time)")
    return build(out_dir)


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", type=Path, default=FIXED_DIR)
    ap.add_argument("--no-verify", action="store_true")
    a = ap.parse_args()
    print(build(a.out, verify=not a.no_verify))
