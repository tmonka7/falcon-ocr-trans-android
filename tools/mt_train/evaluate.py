#!/usr/bin/env python3
"""Compares translation models on the prepared evaluation sets.

    python tools/mt_train/evaluate.py --direction ko-en
    python tools/mt_train/evaluate.py --direction en-ko --model base=Helsinki-NLP/opus-mt-tc-big-en-ko \
        --model tuned=tools/mt_train/runs/en-ko/final

By default it evaluates the published checkpoint ("base") and, if present,
``runs/<direction>/final`` ("tuned") on:

    tatoeba_test    official Tatoeba-Challenge eng-kor test
    flores_devtest  FLORES-200 devtest
    test            held-out slice of the training mix
    app_domain      hand-written signs/menus/UI/forms (eval/app_domain.tsv)

Each set is scored twice: on clean sources, and on sources corrupted with the
same OCR-style noise used in training (fixed seed, every sentence noised), which
approximates what the app's OCR stage produces.

Decoding is greedy, as in the app. Metrics: chrF++ (primary) and BLEU
(tokenize=char for Korean targets, 13a for English targets). Writes
``report.md`` and ``report.json`` into ``--out``.
"""
from __future__ import annotations

import argparse
import json
import random
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from ocr_noise import add_noise  # noqa: E402
from train import BASE_MODELS, read_jsonl, resolve_base  # noqa: E402

DEFAULT_SETS = ("tatoeba_test", "flores_devtest", "test", "app_domain")


def translate(model, tokenizer, sources: list[str], batch_size: int, max_len: int, device) -> list[str]:
    import torch
    out: list[str] = []
    model.eval()
    for i in range(0, len(sources), batch_size):
        chunk = sources[i:i + batch_size]
        enc = tokenizer(chunk, return_tensors="pt", padding=True, truncation=True, max_length=max_len).to(device)
        with torch.no_grad():
            gen = model.generate(**enc, num_beams=1, do_sample=False, max_new_tokens=max_len)
        out.extend(s.strip() for s in tokenizer.batch_decode(gen, skip_special_tokens=True))
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--direction", choices=sorted(BASE_MODELS), required=True)
    ap.add_argument("--model", action="append", metavar="NAME=PATH_OR_REPO",
                    help="model to evaluate (repeatable); default base + runs/<direction>/final. "
                         "Use NAME=onnx:ASSET_DIR to score an exported int8 model as the app runs it")
    ap.add_argument("--onnx-tokenizer", default=None,
                    help="tokenizer for onnx: models (default: the direction's base model)")
    ap.add_argument("--data-dir", type=Path, default=HERE / "data" / "en-ko")
    ap.add_argument("--sets", nargs="+", default=list(DEFAULT_SETS))
    ap.add_argument("--max-samples", type=int, default=None, help="cap sentences per set")
    ap.add_argument("--no-noisy", action="store_true", help="skip the OCR-noise condition")
    ap.add_argument("--batch-size", type=int, default=32)
    ap.add_argument("--max-len", type=int, default=256)
    ap.add_argument("--out", type=Path, default=None, help="default: runs/<direction>/eval")
    ap.add_argument("--seed", type=int, default=7)
    args = ap.parse_args()

    import sacrebleu
    import torch
    from transformers import AutoModelForSeq2SeqLM, AutoTokenizer

    src_lang, tgt_lang = args.direction.split("-")
    out_dir = args.out or HERE / "runs" / args.direction / "eval"
    out_dir.mkdir(parents=True, exist_ok=True)

    models = {}
    for spec in args.model or []:
        name, _, path = spec.partition("=")
        models[name] = path
    if not models:
        models["base"] = resolve_base(args.direction)
        tuned = HERE / "runs" / args.direction / "final"
        if tuned.is_dir():
            models["tuned"] = str(tuned)

    sets = {}
    for name in args.sets:
        path = args.data_dir / f"{name}.jsonl"
        if not path.is_file():
            print(f"skip {name}: {path} not found (run prepare_data.py)")
            continue
        rows = read_jsonl(path)
        if args.max_samples:
            rows = rows[:args.max_samples]
        sets[name] = rows

    conditions = ["clean"] if args.no_noisy else ["clean", "ocr_noise"]
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    tok_name = "char" if tgt_lang == "ko" else "13a"
    results: dict = {"direction": args.direction, "models": models, "decoding": "greedy",
                     "bleu_tokenize": tok_name, "scores": {}, "samples": {}}

    for mname, path in models.items():
        print(f"== {mname}: {path}")
        onnx_dir = None
        if path.startswith("onnx:"):
            # The exported int8 model, decoded exactly as the app does. Fine-tuning
            # never changes the tokenizer, so the base tokenizer supplies the
            # SentencePiece segmentation; ids come from the exported TSV tables.
            onnx_dir = Path(path[len("onnx:"):])
            tokenizer = AutoTokenizer.from_pretrained(args.onnx_tokenizer or resolve_base(args.direction))
            model = None
        else:
            tokenizer = AutoTokenizer.from_pretrained(path)
            model = AutoModelForSeq2SeqLM.from_pretrained(path).to(device)
        for sname, rows in sets.items():
            refs = [r[tgt_lang] for r in rows]
            for cond in conditions:
                if cond == "clean":
                    srcs = [r[src_lang] for r in rows]
                else:
                    rng = random.Random(args.seed)
                    srcs = [add_noise(r[src_lang], src_lang, rng) for r in rows]
                started = time.time()
                if onnx_dir is not None:
                    from export import onnx_greedy
                    hyps = [onnx_greedy(onnx_dir, tokenizer, s, args.max_len)[1] for s in srcs]
                else:
                    hyps = translate(model, tokenizer, srcs, args.batch_size, args.max_len, device)
                bleu = sacrebleu.corpus_bleu(hyps, [refs], tokenize=tok_name).score
                chrf = sacrebleu.corpus_chrf(hyps, [refs], word_order=2).score
                key = f"{sname}/{cond}"
                results["scores"].setdefault(key, {})[mname] = {
                    "chrf": round(chrf, 2), "bleu": round(bleu, 2), "n": len(rows),
                    "seconds": round(time.time() - started, 1)}
                print(f"   {key:28s} chrF {chrf:6.2f}  BLEU {bleu:6.2f}  (n={len(rows)})")
                if sname == "app_domain":
                    results["samples"].setdefault(cond, [])
                    for i, (s, h, r) in enumerate(zip(srcs, hyps, refs)):
                        if i >= 15:
                            break
                        entry = next((e for e in results["samples"][cond] if e["source"] == s), None)
                        if entry is None:
                            entry = {"source": s, "reference": r}
                            results["samples"][cond].append(entry)
                        entry[mname] = h
        del model
        if device.type == "cuda":
            torch.cuda.empty_cache()

    (out_dir / "report.json").write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")

    names = list(models)
    lines = [f"# {args.direction} evaluation", "",
             f"Greedy decoding; chrF++ / BLEU (tokenize={tok_name}).", "",
             "| Set / condition | n | " + " | ".join(f"{n} chrF | {n} BLEU" for n in names) + " |",
             "|---|---|" + "---|---|" * len(names)]
    for key, per_model in results["scores"].items():
        n = next(iter(per_model.values()))["n"]
        cells = []
        for m in names:
            s = per_model.get(m)
            cells += [f"{s['chrf']:.2f}", f"{s['bleu']:.2f}"] if s else ["-", "-"]
        lines.append(f"| {key} | {n} | " + " | ".join(cells) + " |")
    for cond, samples in results["samples"].items():
        lines += ["", f"## app_domain samples ({cond})", "",
                  "| Source | Reference | " + " | ".join(names) + " |",
                  "|---|---|" + "---|" * len(names)]
        for e in samples:
            lines.append("| " + " | ".join(str(e.get(k, "")).replace("|", "\\|")
                                            for k in ("source", "reference", *names)) + " |")
    (out_dir / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"\nwrote {out_dir / 'report.md'}")


if __name__ == "__main__":
    main()
