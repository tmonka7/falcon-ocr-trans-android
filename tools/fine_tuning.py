#!/usr/bin/env python3
"""Fine-tune one OPUS-MT pair on a parallel corpus, mock or real.

Run this on a desktop, like the converters. Requires::

    pip install torch transformers sentencepiece
    pip install "optimum[onnxruntime]" ml_dtypes   # only for --export

Without ``--data`` the script generates a small templated corpus (travel
phrases with a noun and a number slot) in all four languages and trains on the
requested direction. That corpus exists to exercise the pipeline end to end —
train, save, export, load on the phone — not to improve translation. A few
epochs on it will over-fit the phrasing and can degrade general quality, so do
not ship a mock-trained model.

A real corpus is a UTF-8 TSV of ``source<TAB>target`` lines; the mock corpus is
written in the same format next to the checkpoint so the two are
interchangeable.

The tokenizer and vocabulary are never changed. That keeps the exported
``source.spm.tsv`` and ``vocab.tsv`` identical to the stock pair, so the app's
``SpmEncoder`` and ``MtVocab`` need nothing new.

Typical use::

    python tools/finetune_mt.py --pair ko-en                  # mock data, save only
    python tools/finetune_mt.py --pair ko-en --data my.tsv --export

``--export`` overwrites ``assets/model/mt/<pair>/``. To restore the stock model,
run ``python tools/convert_mt.py --only <pair>``.
"""

from __future__ import annotations

import argparse
import json
import math
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import convert_mt  # noqa: E402  (needs the path entry above)

__all__ = ["main"]

LANGS = ("en", "ko", "ja", "zh")


# ---------------------------------------------------------------------------
# Mock corpus
# ---------------------------------------------------------------------------

# Nouns chosen to mix Korean final consonants, so both particle forms appear.
ITEMS = [
    {"en": "menu", "ko": "메뉴", "ja": "メニュー", "zh": "菜单"},
    {"en": "ticket", "ko": "표", "ja": "切符", "zh": "票"},
    {"en": "receipt", "ko": "영수증", "ja": "レシート", "zh": "收据"},
    {"en": "passport", "ko": "여권", "ja": "パスポート", "zh": "护照"},
    {"en": "umbrella", "ko": "우산", "ja": "傘", "zh": "雨伞"},
    {"en": "key", "ko": "열쇠", "ja": "鍵", "zh": "钥匙"},
    {"en": "book", "ko": "책", "ja": "本", "zh": "书"},
    {"en": "map", "ko": "지도", "ja": "地図", "zh": "地图"},
]

# ko_topic / ko_obj / ko_subj carry the particle that fits the noun's ending.
TEMPLATES = [
    {"en": "Where is the {en}?", "ko": "{ko_topic} 어디에 있습니까?",
     "ja": "{ja}はどこですか？", "zh": "{zh}在哪里？"},
    {"en": "Please give me the {en}.", "ko": "{ko_obj} 주세요.",
     "ja": "{ja}をください。", "zh": "请给我{zh}。"},
    {"en": "I lost my {en}.", "ko": "{ko_obj} 잃어버렸어요.",
     "ja": "{ja}をなくしました。", "zh": "我丢了我的{zh}。"},
    {"en": "I need the {en}.", "ko": "{ko_subj} 필요합니다.",
     "ja": "{ja}が必要です。", "zh": "我需要{zh}。"},
    {"en": "Can you show me the {en}?", "ko": "{ko_obj} 보여 주시겠어요?",
     "ja": "{ja}を見せてもらえますか？", "zh": "可以给我看看{zh}吗？"},
    {"en": "The {en} costs {n} dollars.", "ko": "{ko_topic} {n}달러입니다.",
     "ja": "{ja}は{n}ドルです。", "zh": "{zh}要{n}美元。"},
]


def _has_final_consonant(word: str) -> bool:
    last = word[-1]
    return "가" <= last <= "힣" and (ord(last) - 0xAC00) % 28 != 0


def _particle(word: str, with_final: str, without_final: str) -> str:
    return word + (with_final if _has_final_consonant(word) else without_final)


def make_mock_corpus(size: int, src: str, tgt: str, seed: int) -> list[tuple[str, str]]:
    """Sample up to ``size`` distinct (source, target) pairs from the templates."""
    rng = random.Random(seed)
    seen: set[tuple[str, str]] = set()
    pairs: list[tuple[str, str]] = []
    # The slot space is finite (~830 sentences); stop rather than loop forever
    # when more are asked for than exist.
    for _ in range(size * 20):
        if len(pairs) >= size:
            break
        template = rng.choice(TEMPLATES)
        item = rng.choice(ITEMS)
        fields = {
            **item,
            "n": rng.randint(2, 99),
            "ko_topic": _particle(item["ko"], "은", "는"),
            "ko_obj": _particle(item["ko"], "을", "를"),
            "ko_subj": _particle(item["ko"], "이", "가"),
        }
        pair = (template[src].format(**fields), template[tgt].format(**fields))
        if pair not in seen:
            seen.add(pair)
            pairs.append(pair)
    if len(pairs) < size:
        print(f"  mock corpus has only {len(pairs)} distinct pairs; using all of them")
    return pairs


def read_tsv(path: Path) -> list[tuple[str, str]]:
    pairs = []
    with path.open(encoding="utf-8") as fh:
        for lineno, line in enumerate(fh, 1):
            line = line.rstrip("\n")
            if not line.strip():
                continue
            parts = line.split("\t")
            if len(parts) != 2 or not parts[0].strip() or not parts[1].strip():
                sys.exit(f"{path}:{lineno}: expected 'source<TAB>target'")
            pairs.append((parts[0].strip(), parts[1].strip()))
    if not pairs:
        sys.exit(f"{path} contains no sentence pairs")
    return pairs


def write_tsv(pairs: list[tuple[str, str]], path: Path) -> None:
    with path.open("w", encoding="utf-8", newline="\n") as fh:
        for s, t in pairs:
            fh.write(f"{s}\t{t}\n")


# ---------------------------------------------------------------------------
# Training
# ---------------------------------------------------------------------------

def encode(tokenizer, batch: list[tuple[str, str]], max_length: int, device):
    enc = tokenizer(
        [s for s, _ in batch],
        text_target=[t for _, t in batch],
        max_length=max_length,
        truncation=True,
        padding=True,
        return_tensors="pt",
    )
    # Padding in the labels must not contribute to the loss.
    enc["labels"][enc["labels"] == tokenizer.pad_token_id] = -100
    return {k: v.to(device) for k, v in enc.items()}


def batches(pairs: list[tuple[str, str]], size: int):
    for i in range(0, len(pairs), size):
        yield pairs[i:i + size]


def eval_loss(model, tokenizer, pairs, batch_size, max_length, device) -> float:
    import torch

    model.eval()
    total, count = 0.0, 0
    with torch.no_grad():
        for batch in batches(pairs, batch_size):
            loss = model(**encode(tokenizer, batch, max_length, device)).loss
            total += loss.item() * len(batch)
            count += len(batch)
    return total / max(count, 1)


def translate(model, tokenizer, sentences, max_length, device) -> list[str]:
    import torch

    model.eval()
    enc = tokenizer(sentences, max_length=max_length, truncation=True,
                    padding=True, return_tensors="pt").to(device)
    with torch.no_grad():
        # Greedy, because that is what MarianTranslator does on the phone.
        out = model.generate(**enc, num_beams=1, do_sample=False,
                             max_new_tokens=max_length)
    return tokenizer.batch_decode(out, skip_special_tokens=True)


def show_samples(label, model, tokenizer, pairs, max_length, device) -> None:
    print(f"  {label}:")
    for (src, ref), hyp in zip(pairs, translate(model, tokenizer, [s for s, _ in pairs],
                                                max_length, device)):
        print(f"    {src}\n      ref: {ref}\n      hyp: {hyp}")


def train(args, repo: str, train_pairs, eval_pairs) -> Path:
    import torch
    from transformers import (AutoModelForSeq2SeqLM, AutoTokenizer,
                              get_linear_schedule_with_warmup)

    torch.manual_seed(args.seed)
    device = torch.device(args.device or ("cuda" if torch.cuda.is_available() else "cpu"))
    print(f"loading {repo} on {device}")
    tokenizer = AutoTokenizer.from_pretrained(repo)
    model = AutoModelForSeq2SeqLM.from_pretrained(repo).to(device)

    samples = eval_pairs[:args.samples]
    before = eval_loss(model, tokenizer, eval_pairs, args.batch_size, args.max_length, device)
    print(f"  eval loss before: {before:.4f}")
    show_samples("before", model, tokenizer, samples, args.max_length, device)

    optimizer = torch.optim.AdamW(model.parameters(), lr=args.lr,
                                  weight_decay=args.weight_decay)
    steps = args.epochs * math.ceil(len(train_pairs) / args.batch_size)
    scheduler = get_linear_schedule_with_warmup(
        optimizer, num_warmup_steps=int(steps * args.warmup), num_training_steps=steps)

    rng = random.Random(args.seed)
    step = 0
    for epoch in range(1, args.epochs + 1):
        model.train()
        order = train_pairs[:]
        rng.shuffle(order)
        running, seen = 0.0, 0
        for batch in batches(order, args.batch_size):
            loss = model(**encode(tokenizer, batch, args.max_length, device)).loss
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            optimizer.step()
            scheduler.step()
            optimizer.zero_grad()
            step += 1
            running += loss.item() * len(batch)
            seen += len(batch)
            if step % args.log_every == 0:
                print(f"  epoch {epoch} step {step}/{steps}  loss {running / seen:.4f}")
        val = eval_loss(model, tokenizer, eval_pairs, args.batch_size, args.max_length, device)
        print(f"  epoch {epoch} done  train {running / max(seen, 1):.4f}  eval {val:.4f}")

    show_samples("after", model, tokenizer, samples, args.max_length, device)

    out = args.output_dir
    out.mkdir(parents=True, exist_ok=True)
    model.save_pretrained(out)
    tokenizer.save_pretrained(out)
    preserve_decode_limit(repo, out)
    print(f"checkpoint saved to {out}")
    return out


def preserve_decode_limit(repo: str, out: Path) -> None:
    """Put ``max_length`` back into the saved config.json.

    save_pretrained moves generation settings from config.json into
    generation_config.json. convert_mt.write_config reads max_length from the
    model config, so without this it would fall back to transformers' default
    of 20 and the phone would cut every translation off at 20 tokens.
    """
    from transformers import AutoConfig

    original = int(getattr(AutoConfig.from_pretrained(repo), "max_length", 0) or 0)
    if not original:
        return
    path = out / "config.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("max_length") != original:
        data["max_length"] = original
        path.write_text(json.dumps(data, indent=2), encoding="utf-8")


# ---------------------------------------------------------------------------

def main() -> None:
    # Sample translations are CJK. A redirected stdout on Windows defaults to
    # cp1252, which cannot encode them and would crash mid-run.
    try:
        sys.stdout.reconfigure(line_buffering=True, encoding="utf-8")
        sys.stderr.reconfigure(line_buffering=True, encoding="utf-8")
    except AttributeError:
        pass

    pairs_known = sorted(f"{s}-{t}" for s, t in convert_mt.PAIRS)
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--pair", required=True, choices=pairs_known,
                        help="direction to fine-tune")
    parser.add_argument("--base", help="checkpoint to start from; defaults to the "
                                       "Hugging Face repo convert_mt.py exports")
    parser.add_argument("--data", type=Path,
                        help="source<TAB>target TSV; omit to generate a mock corpus")
    parser.add_argument("--mock-size", type=int, default=400,
                        help="sentence pairs to generate when --data is omitted")
    parser.add_argument("--eval-fraction", type=float, default=0.1)
    parser.add_argument("--epochs", type=int, default=3)
    parser.add_argument("--batch-size", type=int, default=16)
    parser.add_argument("--lr", type=float, default=2e-5)
    parser.add_argument("--weight-decay", type=float, default=0.01)
    parser.add_argument("--warmup", type=float, default=0.1,
                        help="fraction of steps spent warming up the learning rate")
    parser.add_argument("--max-length", type=int, default=128,
                        help="token cap for training inputs and sample decoding")
    parser.add_argument("--samples", type=int, default=3,
                        help="held-out sentences to translate before and after")
    parser.add_argument("--log-every", type=int, default=10)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--device", help="cpu, cuda, cuda:1 ...; default picks CUDA if present")
    parser.add_argument("--output-dir", type=Path,
                        help="default: build/models/mt-finetuned/<pair>")
    parser.add_argument("--export", action="store_true",
                        help="convert the result to int8 ONNX and overwrite the app's pair")
    parser.add_argument("--assets-dir", type=Path,
                        default=Path("app/src/main/assets/model/mt"))
    parser.add_argument("--work-dir", type=Path, default=Path("build/models/mt"))
    args = parser.parse_args()

    src, tgt = args.pair.split("-")
    repo = args.base or convert_mt.PAIRS[(src, tgt)]
    if args.output_dir is None:
        args.output_dir = Path("build/models/mt-finetuned") / args.pair
    args.output_dir.mkdir(parents=True, exist_ok=True)

    if args.data:
        pairs = read_tsv(args.data)
        print(f"read {len(pairs)} pairs from {args.data}")
    else:
        pairs = make_mock_corpus(args.mock_size, src, tgt, args.seed)
        mock_path = args.output_dir / "mock_data.tsv"
        write_tsv(pairs, mock_path)
        print(f"generated {len(pairs)} mock pairs -> {mock_path}")

    random.Random(args.seed).shuffle(pairs)
    n_eval = max(1, int(len(pairs) * args.eval_fraction))
    if len(pairs) - n_eval < 1:
        sys.exit("need at least two sentence pairs: one to train on, one to evaluate")
    eval_pairs, train_pairs = pairs[:n_eval], pairs[n_eval:]
    print(f"train {len(train_pairs)}  eval {len(eval_pairs)}")

    checkpoint = train(args, repo, train_pairs, eval_pairs)

    if args.export:
        convert_mt.export_pair(str(checkpoint), src, tgt, args.assets_dir, args.work_dir)
        print(f"exported to {args.assets_dir / args.pair}; restore the stock model with "
              f"'python tools/convert_mt.py --only {args.pair}'")


if __name__ == "__main__":
    main()
