#!/usr/bin/env python3
"""Fine-tunes the app's Korean-English OPUS-MT models on prepared data.

    python tools/mt_train/train.py --direction ko-en
    python tools/mt_train/train.py --direction en-ko --batch-size 8 --grad-accum 4

Starting points are the checkpoints the app already ships, so the fine-tuned
model keeps their tokenizer and vocabulary unchanged and drops straight into
tools/convert_mt.py (see export.py):

    ko-en  Helsinki-NLP/opus-mt-ko-en          transformer-base, Apache-2.0
    en-ko  Helsinki-NLP/opus-mt-tc-big-en-ko   transformer-big,  CC-BY 4.0,
           via the corrected copy built by fix_en_ko_base.py - the published
           tokenizer maps English through the Korean vocabulary and the
           unmodified checkpoint produces garbage (see that file)

Neither model needs a target-language token (the tc-big vocabulary contains no
>>xx<< entries), which matches what the app's MarianTranslator feeds it.

What the fine-tuning adds over the published checkpoints:

* robustness to OCR errors: a fraction of training sources (``--noise-prob``)
  is corrupted with look-alike characters, fused/split words, capitals and
  hyphenation artefacts (ocr_noise.py); targets stay clean;
* domain: the prepared mix over-represents short UI, label and title strings;
* evaluation that matches deployment: greedy decoding (the app does not use
  beam search) and chrF as the selection metric.

Outputs ``<output-dir>/final`` (model + unchanged tokenizer) and
``training_summary.json``.
"""
from __future__ import annotations

import argparse
import inspect
import json
import math
import random
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from ocr_noise import SourceNoiser  # noqa: E402

BASE_MODELS = {
    "ko-en": "Helsinki-NLP/opus-mt-ko-en",
    "en-ko": "Helsinki-NLP/opus-mt-tc-big-en-ko",   # always used through fix_en_ko_base
}


def resolve_base(direction: str) -> str:
    """The starting checkpoint for a direction, as a repo id or local directory."""
    if direction == "en-ko":
        import fix_en_ko_base
        return str(fix_en_ko_base.ensure())
    return BASE_MODELS[direction]
# The big model has ~4x the parameters; it wants a smaller step size.
DEFAULT_LR = {"ko-en": 5e-5, "en-ko": 2e-5}


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--direction", choices=sorted(BASE_MODELS), required=True)
    ap.add_argument("--data-dir", type=Path, default=HERE / "data" / "en-ko")
    ap.add_argument("--base-model", default=None, help="override the starting checkpoint")
    ap.add_argument("--output-dir", type=Path, default=None, help="default: runs/<direction>")
    ap.add_argument("--epochs", type=float, default=2.0)
    ap.add_argument("--max-steps", type=int, default=-1, help="overrides --epochs when > 0")
    ap.add_argument("--lr", type=float, default=None)
    ap.add_argument("--batch-size", type=int, default=32)
    ap.add_argument("--grad-accum", type=int, default=1)
    ap.add_argument("--max-len", type=int, default=128, help="max tokens per side")
    ap.add_argument("--warmup-ratio", type=float, default=0.03)
    ap.add_argument("--weight-decay", type=float, default=0.01)
    ap.add_argument("--label-smoothing", type=float, default=0.1)
    ap.add_argument("--noise-prob", type=float, default=0.3,
                    help="fraction of training sources given OCR-style noise (0 disables)")
    ap.add_argument("--eval-steps", type=int, default=2000)
    ap.add_argument("--eval-samples", type=int, default=1000,
                    help="dev pairs decoded per evaluation (generation is the slow part)")
    ap.add_argument("--max-train-samples", type=int, default=None)
    ap.add_argument("--patience", type=int, default=4, help="early-stopping evaluations without improvement")
    ap.add_argument("--gradient-checkpointing", action="store_true")
    ap.add_argument("--seed", type=int, default=42)
    return ap.parse_args()


def read_jsonl(path: Path) -> list[dict]:
    with path.open(encoding="utf-8") as fh:
        return [json.loads(line) for line in fh if line.strip()]


class PairCollator:
    """Tokenises raw pairs per batch.

    Rows carry a ``noisy`` flag: 1 for training rows, 0 for dev rows. The
    Trainer uses one collator for both loaders, so the flag - not trainer state -
    is what keeps evaluation sources clean.
    """

    def __init__(self, tokenizer, model, max_len: int, noiser: SourceNoiser | None):
        self.tok = tokenizer
        self.max_len = max_len
        self.noiser = noiser
        self.model = model

    def __call__(self, features: list[dict]):
        srcs = [f["src_text"] for f in features]
        if self.noiser is not None:
            srcs = [self.noiser(s) if f["noisy"] else s for s, f in zip(srcs, features)]
        tgts = [f["tgt_text"] for f in features]
        batch = self.tok(srcs, text_target=tgts, max_length=self.max_len, truncation=True,
                         padding=True, return_tensors="pt")
        labels = batch["labels"]
        labels[labels == self.tok.pad_token_id] = -100
        batch["labels"] = labels
        # With label smoothing the Trainer pops "labels" before calling the model,
        # so the decoder inputs must be built here (as DataCollatorForSeq2Seq does).
        batch["decoder_input_ids"] = self.model.prepare_decoder_input_ids_from_labels(labels=labels)
        return batch


def main() -> None:
    args = parse_args()
    try:
        sys.stdout.reconfigure(line_buffering=True)
    except AttributeError:
        pass

    import numpy as np
    import sacrebleu
    import torch
    from datasets import Dataset
    from transformers import (AutoModelForSeq2SeqLM, AutoTokenizer, EarlyStoppingCallback,
                              Seq2SeqTrainer, Seq2SeqTrainingArguments, set_seed)

    set_seed(args.seed)
    src_lang, tgt_lang = args.direction.split("-")
    base = args.base_model or resolve_base(args.direction)
    out_dir = args.output_dir or HERE / "runs" / args.direction
    out_dir.mkdir(parents=True, exist_ok=True)
    lr = args.lr or DEFAULT_LR[args.direction]

    # ---- data ----
    def to_rows(rows: list[dict], noisy: int) -> dict[str, list]:
        return {"src_text": [r[src_lang] for r in rows], "tgt_text": [r[tgt_lang] for r in rows],
                "noisy": [noisy] * len(rows)}

    train_rows = read_jsonl(args.data_dir / "train.jsonl")
    if args.max_train_samples:
        random.Random(args.seed).shuffle(train_rows)
        train_rows = train_rows[:args.max_train_samples]
    dev_rows = read_jsonl(args.data_dir / "dev.jsonl")
    random.Random(args.seed).shuffle(dev_rows)
    dev_rows = dev_rows[:args.eval_samples]
    train_ds = Dataset.from_dict(to_rows(train_rows, 1))
    dev_ds = Dataset.from_dict(to_rows(dev_rows, 0))
    print(f"{args.direction}: {len(train_ds):,} training pairs, {len(dev_ds):,} dev pairs; base {base}")

    # ---- model ----
    tokenizer = AutoTokenizer.from_pretrained(base)
    model = AutoModelForSeq2SeqLM.from_pretrained(base)
    if args.gradient_checkpointing:
        model.gradient_checkpointing_enable()
        model.config.use_cache = False
    base_vocab = tokenizer.get_vocab()
    base_special = {k: getattr(model.config, k, None)
                    for k in ("pad_token_id", "eos_token_id", "decoder_start_token_id", "vocab_size")}

    noiser = SourceNoiser(src_lang, args.noise_prob, seed=args.seed) if args.noise_prob > 0 else None
    collator = PairCollator(tokenizer, model, args.max_len, noiser)

    target_tok = "char" if tgt_lang == "ko" else "13a"

    def compute_metrics(eval_pred):
        preds, labels = eval_pred
        if isinstance(preds, tuple):
            preds = preds[0]
        preds = np.where(preds < 0, tokenizer.pad_token_id, preds)
        labels = np.where(labels < 0, tokenizer.pad_token_id, labels)
        hyp = [s.strip() for s in tokenizer.batch_decode(preds, skip_special_tokens=True)]
        ref = [s.strip() for s in tokenizer.batch_decode(labels, skip_special_tokens=True)]
        bleu = sacrebleu.corpus_bleu(hyp, [ref], tokenize=target_tok).score
        chrf = sacrebleu.corpus_chrf(hyp, [ref], word_order=2).score
        return {"bleu": round(bleu, 2), "chrf": round(chrf, 2)}

    use_cuda = torch.cuda.is_available()
    bf16 = use_cuda and torch.cuda.is_bf16_supported()
    targs = dict(
        output_dir=str(out_dir),
        per_device_train_batch_size=args.batch_size,
        per_device_eval_batch_size=max(8, args.batch_size),
        gradient_accumulation_steps=args.grad_accum,
        learning_rate=lr,
        weight_decay=args.weight_decay,
        warmup_ratio=args.warmup_ratio,
        label_smoothing_factor=args.label_smoothing,
        num_train_epochs=args.epochs,
        max_steps=args.max_steps,
        lr_scheduler_type="linear",
        eval_strategy="steps",
        eval_steps=args.eval_steps,
        save_strategy="steps",
        save_steps=args.eval_steps,
        save_total_limit=2,
        load_best_model_at_end=True,
        metric_for_best_model="chrf",
        greater_is_better=True,
        predict_with_generate=True,
        generation_num_beams=1,                 # the app decodes greedily
        generation_max_length=args.max_len,
        logging_steps=50,
        bf16=bf16,
        fp16=use_cuda and not bf16,
        dataloader_num_workers=0,               # the collator carries RNG state
        remove_unused_columns=False,
        report_to="none",
        seed=args.seed,
    )
    training_args = Seq2SeqTrainingArguments(**targs)

    trainer_kwargs = dict(model=model, args=training_args, train_dataset=train_ds, eval_dataset=dev_ds,
                          data_collator=collator, compute_metrics=compute_metrics,
                          callbacks=[EarlyStoppingCallback(early_stopping_patience=args.patience)])
    # transformers renamed tokenizer= to processing_class= in 4.46.
    if "processing_class" in inspect.signature(Seq2SeqTrainer.__init__).parameters:
        trainer_kwargs["processing_class"] = tokenizer
    else:
        trainer_kwargs["tokenizer"] = tokenizer
    trainer = Seq2SeqTrainer(**trainer_kwargs)

    # Baseline on the same dev slice, so the summary shows the gain (or loss).
    baseline = trainer.evaluate(metric_key_prefix="baseline")
    print(f"baseline dev: {baseline}")

    started = time.time()
    trainer.train()
    final = trainer.evaluate(metric_key_prefix="final")
    print(f"final dev: {final}")

    # ---- invariants the app depends on ----
    if tokenizer.get_vocab() != base_vocab:
        raise SystemExit("tokenizer vocabulary changed; the exported model would not match vocab.tsv")
    for k, v in base_special.items():
        if getattr(trainer.model.config, k, None) != v:
            raise SystemExit(f"config.{k} changed from {v}; the app's config.json would be wrong")

    final_dir = out_dir / "final"
    trainer.save_model(str(final_dir))
    tokenizer.save_pretrained(str(final_dir))

    manifest_path = args.data_dir / "manifest.json"
    summary = {
        "direction": args.direction,
        "base_model": base,
        "output": str(final_dir),
        "args": {k: (str(v) if isinstance(v, Path) else v) for k, v in vars(args).items()},
        "learning_rate": lr,
        "train_pairs": len(train_ds),
        "dev_pairs": len(dev_ds),
        "baseline_dev": baseline,
        "final_dev": final,
        "train_minutes": round((time.time() - started) / 60, 1),
        "global_steps": trainer.state.global_step,
        "best_checkpoint": trainer.state.best_model_checkpoint,
        "data_manifest_sha256": (json.loads(manifest_path.read_text(encoding="utf-8")).get("sha256")
                                 if manifest_path.is_file() else None),
        "device": "cuda" if use_cuda else "cpu",
        "precision": "bf16" if bf16 else "fp16" if use_cuda else "fp32",
    }
    (out_dir / "training_summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False),
                                                   encoding="utf-8")
    delta = final.get("final_chrf", math.nan) - baseline.get("baseline_chrf", math.nan)
    print(f"\nsaved {final_dir}  (dev chrF {baseline.get('baseline_chrf')} -> {final.get('final_chrf')}, "
          f"delta {delta:+.2f})")


if __name__ == "__main__":
    main()
