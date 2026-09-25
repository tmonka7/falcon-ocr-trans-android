#!/usr/bin/env python3
"""Exports a fine-tuned model into the app's model tree and checks it.

    python tools/mt_train/export.py --direction ko-en            # runs/ko-en/final
    python tools/mt_train/export.py --direction en-ko --model-dir path/to/final

This reuses tools/convert_mt.py unchanged (ONNX export, dynamic int8
quantisation, source.spm.tsv, vocab.tsv, config.json), writing to
``app/src/main/assets/model/mt/<direction>/``. A copy of the previous files is
kept in ``<direction>.bak`` so a bad export can be rolled back.

Afterwards it runs a parity check: the int8 ONNX graphs are decoded exactly as
the app's MarianTranslator does (encoder once, cacheless decoder stepped
greedily from decoder_start_token_id, stop at EOS/PAD) and compared with the
PyTorch model's greedy output. Int8 quantisation may change a few words; an
agreement rate far below ~80 % indicates a broken export.
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(REPO / "tools"))

PROBES = {
    "ko": ["출구는 왼쪽에 있습니다.", "냉장 보관하세요.", "다음 역은 시청입니다.",
           "이 파일을 삭제하시겠습니까?", "1일 3회, 식후에 1정씩 복용하세요.", "영업시간: 오전 9시~오후 6시"],
    "en": ["The exit is on the left.", "Keep refrigerated.", "The next stop is City Hall.",
           "Are you sure you want to delete this file?", "Take one tablet three times a day after meals.",
           "Business hours: 9:00 AM to 6:00 PM"],
}


_LOADED: dict[str, tuple] = {}   # asset dir -> (config, encoder, decoder, source vocab, id->target token)


def onnx_greedy(asset_dir: Path, tokenizer, text: str, max_steps: int = 128) -> tuple[list[int], str]:
    """Mirror of MarianTranslator.decodeChunk/greedyDecode, in numpy."""
    import numpy as np
    import onnxruntime as ort

    key = str(asset_dir.resolve())
    if key not in _LOADED:
        # Ids come from the exported TSV tables, exactly as MtVocab reads them, so a
        # wrong table (e.g. target vocabulary used for the source) fails this check.
        def table(name: str) -> dict[str, int]:
            rows = (line.rsplit("\t", 1) for line in
                    (asset_dir / name).read_text(encoding="utf-8").splitlines() if line)
            return {tok: int(i) for tok, i in rows}
        target_vocab = table("vocab.tsv")
        source_vocab = (table("source_vocab.tsv") if (asset_dir / "source_vocab.tsv").is_file()
                        else target_vocab)
        _LOADED[key] = (
            json.loads((asset_dir / "config.json").read_text(encoding="utf-8")),
            ort.InferenceSession(str(asset_dir / "encoder.int8.onnx")),
            ort.InferenceSession(str(asset_dir / "decoder.int8.onnx")),
            source_vocab,
            {i: t for t, i in target_vocab.items()},
        )
    cfg, enc, dec, source_vocab, id_to_target = _LOADED[key]
    pieces = tokenizer.spm_source.encode(text, out_type=str)
    unk = source_vocab.get("<unk>", 1)
    ids = [source_vocab.get(p, unk) for p in pieces] + [cfg["eos_token_id"]]
    input_ids = np.array([ids], dtype=np.int64)
    mask = np.ones_like(input_ids)
    enc_names = {i.name for i in enc.get_inputs()}
    feeds = {"input_ids": input_ids}
    if "attention_mask" in enc_names:
        feeds["attention_mask"] = mask
    hidden = enc.run(None, feeds)[0]

    dec_names = [i.name for i in dec.get_inputs()]
    dec_ids_name = "input_ids" if "input_ids" in dec_names else "decoder_input_ids"
    generated = [cfg["decoder_start_token_id"]]
    limit = min(cfg["max_length"], max(16, len(ids) * 3 + 8), max_steps)
    for _ in range(limit):
        feeds = {dec_ids_name: np.array([generated], dtype=np.int64),
                 "encoder_hidden_states": hidden, "encoder_attention_mask": mask}
        logits = dec.run(None, {k: v for k, v in feeds.items() if k in dec_names})[0]
        nxt = int(logits[0, -1].argmax())
        if nxt in (cfg["eos_token_id"], cfg["pad_token_id"]):
            break
        generated.append(nxt)
    # Detokenise like SpmEncoder.decodePieces: drop specials, "▁" marks a space.
    out = [id_to_target.get(i, "") for i in generated[1:]]
    out = [p for p in out if p and not (p.startswith("<") and p.endswith(">"))]
    return generated[1:], "".join(out).replace("▁", " ").strip()


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--direction", choices=("ko-en", "en-ko"), required=True)
    ap.add_argument("--model-dir", type=Path, default=None, help="default: runs/<direction>/final")
    ap.add_argument("--assets-dir", type=Path, default=REPO / "app/src/main/assets/model/mt")
    ap.add_argument("--work-dir", type=Path, default=REPO / "build/models/mt-finetuned")
    ap.add_argument("--no-backup", action="store_true")
    ap.add_argument("--check-only", action="store_true", help="skip export; only run the parity check")
    args = ap.parse_args()

    src, tgt = args.direction.split("-")
    model_dir = (args.model_dir or HERE / "runs" / args.direction / "final").resolve()
    if not (model_dir / "config.json").is_file():
        raise SystemExit(f"{model_dir} is not a saved model (run train.py first)")
    target = args.assets_dir / args.direction

    if not args.check_only:
        import convert_mt  # tools/convert_mt.py
        if target.is_dir() and not args.no_backup:
            backup = target.with_name(target.name + ".bak")
            shutil.rmtree(backup, ignore_errors=True)
            shutil.copytree(target, backup)
            print(f"previous model backed up to {backup}")
        convert_mt.export_pair(str(model_dir), src, tgt, args.assets_dir, args.work_dir)

    import torch
    from transformers import AutoModelForSeq2SeqLM, AutoTokenizer
    tokenizer = AutoTokenizer.from_pretrained(model_dir)
    model = AutoModelForSeq2SeqLM.from_pretrained(model_dir).eval()
    agree = 0
    print("\nparity check (PyTorch fp32 greedy vs app-style int8 ONNX greedy):")
    for text in PROBES[src]:
        with torch.no_grad():
            gen = model.generate(**tokenizer([text], return_tensors="pt"), num_beams=1, max_new_tokens=128)
        specials = {model.config.pad_token_id, model.config.eos_token_id,
                    model.config.decoder_start_token_id}
        ref_ids = [int(i) for i in gen[0].tolist() if int(i) not in specials]
        ref = tokenizer.decode(gen[0], skip_special_tokens=True).strip()
        got_ids, got = onnx_greedy(target, tokenizer, text)
        # Token ids are compared, not strings: HF's decode and the app's
        # decodePieces space punctuation differently, which is not a model difference.
        same = ref_ids == got_ids
        agree += same
        print(f"  {'=' if same else '~'} {text}\n      torch: {ref}\n      app  : {got}")
    rate = agree / len(PROBES[src])
    print(f"\ntoken-level agreement {agree}/{len(PROBES[src])} ({rate:.0%})")
    if rate < 0.5:
        raise SystemExit("low agreement: the export is probably broken; restore the .bak copy")


if __name__ == "__main__":
    main()
